import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.connectors.market_data.twelve_data import fetch_time_series, search_symbols

router = APIRouter(prefix="/api/v1/instruments", tags=["instruments"])
COUNTRY_CODES = {
    "Australia": "AU", "Brazil": "BR", "Canada": "CA", "China": "CN",
    "France": "FR", "Germany": "DE", "Hong Kong": "HK", "India": "IN",
    "Japan": "JP", "Poland": "PL", "Switzerland": "CH", "United Kingdom": "GB",
    "United States": "US",
}


class InstrumentImport(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=240)
    exchange: str = Field(min_length=1, max_length=80)
    mic_code: str = Field(min_length=4, max_length=12)
    country: str = Field(default="", max_length=100)
    currency: str = Field(default="", max_length=8)
    instrument_type: str = Field(default="Common Stock", max_length=60)
    isin: str | None = Field(default=None, max_length=16)


async def _db() -> asyncpg.Connection:
    return await asyncpg.connect(os.environ["DATABASE_URL"])


async def _source_id(connection: asyncpg.Connection) -> UUID:
    row = await connection.fetchrow(
        "SELECT id FROM research_sources WHERE source_key = 'twelve_data_prices'"
    )
    if not row:
        raise HTTPException(status_code=503, detail="Brak migracji źródła cen Twelve Data.")
    return row["id"]


async def _record_source_result(connection: asyncpg.Connection, error: str | None = None) -> None:
    await connection.execute(
        """UPDATE research_sources
           SET last_polled_at = NOW(), last_success_at = CASE WHEN $1::text IS NULL THEN NOW() ELSE last_success_at END,
               last_error = $1, updated_at = NOW()
           WHERE source_key = 'twelve_data_prices'""",
        error,
    )


def _attributes(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return value if isinstance(value, dict) else {}


@router.get("")
async def list_instruments(
    q: str | None = Query(default=None, max_length=100),
    asset_class: str = Query(default="stock", pattern="^(stock|etf|all)$"),
    limit: int = Query(default=200, ge=1, le=500),
):
    connection = await _db()
    try:
        rows = await connection.fetch(
            """SELECT i.id, i.asset_class, i.venue_code, i.symbol, i.quote_code, i.isin,
                      i.attributes, e.name, e.country_code, latest.close AS last_price,
                      latest.bar_date::text AS last_price_date
               FROM instruments i JOIN entities e ON e.id = i.entity_id
               LEFT JOIN LATERAL (
                   SELECT close, bar_date FROM price_bars
                   WHERE instrument_id = i.id AND interval = '1day'
                   ORDER BY bar_date DESC LIMIT 1
               ) latest ON TRUE
               WHERE i.active = TRUE
                 AND ($1 = 'all' OR i.asset_class = $1)
                 AND ($2::text IS NULL OR i.symbol ILIKE '%' || $2 || '%' OR e.name ILIKE '%' || $2 || '%')
               ORDER BY e.country_code NULLS LAST, e.name
               LIMIT $3""",
            asset_class, q.strip() if q and q.strip() else None, limit,
        )
        return {"items": [
            {
                **dict(row),
                "id": str(row["id"]),
                "attributes": _attributes(row["attributes"]),
                "last_price": float(row["last_price"]) if row["last_price"] is not None else None,
            }
            for row in rows
        ]}
    finally:
        await connection.close()


@router.get("/search")
async def search_instruments(q: str = Query(min_length=1, max_length=80), limit: int = Query(default=20, ge=1, le=50)):
    try:
        items = await search_symbols(q, limit)
    except HTTPException as exc:
        connection = await _db()
        try:
            await _record_source_result(connection, str(exc.detail))
        finally:
            await connection.close()
        raise
    connection = await _db()
    try:
        await _record_source_result(connection)
    finally:
        await connection.close()
    return {"items": items, "provider": "Twelve Data"}


@router.post("")
async def add_instrument(instrument: InstrumentImport):
    asset_class = "etf" if "etf" in instrument.instrument_type.lower() else "stock"
    mic = instrument.mic_code.upper()
    canonical_key = f"listed:{mic}:{instrument.symbol.upper()}"
    country_code = COUNTRY_CODES.get(instrument.country)
    attributes = {
        "provider": "twelve_data",
        "provider_symbol": instrument.symbol,
        "provider_exchange": instrument.exchange,
        "provider_mic_code": mic,
        "provider_instrument_type": instrument.instrument_type,
        "country": instrument.country,
    }
    connection = await _db()
    try:
        async with connection.transaction():
            entity = await connection.fetchrow(
                """INSERT INTO entities (entity_type, canonical_key, name, country_code, attributes)
                   VALUES ($1, $2, $3, $4, $5::jsonb)
                   ON CONFLICT (canonical_key) DO UPDATE SET
                       name = EXCLUDED.name,
                       country_code = COALESCE(EXCLUDED.country_code, entities.country_code),
                       attributes = entities.attributes || EXCLUDED.attributes,
                       updated_at = NOW()
                   RETURNING id""",
                "fund" if asset_class == "etf" else "company",
                canonical_key, instrument.name, country_code,
                json.dumps(attributes, ensure_ascii=False),
            )
            row = await connection.fetchrow(
                """INSERT INTO instruments
                       (entity_id, asset_class, venue_code, symbol, quote_code, isin, attributes)
                   VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                   ON CONFLICT (venue_code, symbol, asset_class) DO UPDATE SET
                       entity_id = EXCLUDED.entity_id,
                       quote_code = COALESCE(EXCLUDED.quote_code, instruments.quote_code),
                       isin = COALESCE(EXCLUDED.isin, instruments.isin),
                       attributes = instruments.attributes || EXCLUDED.attributes,
                       active = TRUE, updated_at = NOW()
                   RETURNING id""",
                entity["id"], asset_class, mic, instrument.symbol.upper(),
                instrument.currency.upper() or None, instrument.isin,
                json.dumps(attributes, ensure_ascii=False),
            )
        return {"id": str(row["id"]), "saved": True}
    finally:
        await connection.close()


async def _instrument(connection: asyncpg.Connection, instrument_id: UUID) -> asyncpg.Record:
    row = await connection.fetchrow(
        """SELECT i.id, i.asset_class, i.venue_code, i.symbol, i.quote_code, i.attributes,
                  e.name, e.country_code
           FROM instruments i JOIN entities e ON e.id = i.entity_id
           WHERE i.id = $1 AND i.active = TRUE""",
        instrument_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Instrumentu nie ma w katalogu.")
    if row["asset_class"] not in ("stock", "etf"):
        raise HTTPException(status_code=422, detail="Ceny tego typu instrumentu nie są jeszcze obsługiwane.")
    return row


@router.get("/{instrument_id}/prices")
async def get_prices(
    instrument_id: UUID,
    interval: str = Query(default="1day", pattern="^(1day|1week|1month)$"),
    limit: int = Query(default=100, ge=1, le=500),
):
    connection = await _db()
    try:
        await _instrument(connection, instrument_id)
        rows = await connection.fetch(
            """SELECT bar_date, open, high, low, close, volume, quote_code
               FROM price_bars WHERE instrument_id = $1 AND interval = $2
               ORDER BY bar_date DESC LIMIT $3""",
            instrument_id, interval, limit,
        )
        return {"items": [dict(row) for row in rows], "interval": interval}
    finally:
        await connection.close()


@router.post("/{instrument_id}/prices/refresh")
async def refresh_prices(
    instrument_id: UUID,
    interval: str = Query(default="1day", pattern="^(1day|1week|1month)$"),
    limit: int = Query(default=100, ge=1, le=500),
):
    connection = await _db()
    try:
        instrument = await _instrument(connection, instrument_id)
        attributes = _attributes(instrument["attributes"])
        symbol = str(attributes.get("provider_symbol") or instrument["symbol"])
        mic_code = attributes.get("provider_mic_code") or instrument["venue_code"]
        exchange = attributes.get("provider_exchange")
        try:
            series = await fetch_time_series(symbol, exchange, mic_code, interval, limit)
            source_id = await _source_id(connection)
            bars = []
            for value in series["values"]:
                try:
                    bars.append((
                        instrument_id, source_id, interval, date.fromisoformat(value["datetime"][:10]),
                        Decimal(str(value["open"])), Decimal(str(value["high"])),
                        Decimal(str(value["low"])), Decimal(str(value["close"])),
                        Decimal(str(value["volume"])) if value.get("volume") not in (None, "") else None,
                        str(series.get("meta", {}).get("currency") or instrument["quote_code"] or ""),
                        json.dumps({"provider": "Twelve Data", "meta": series.get("meta", {})}),
                    ))
                except (KeyError, ValueError, InvalidOperation) as exc:
                    raise HTTPException(status_code=502, detail="Nie udało się przetworzyć świecy cenowej.") from exc
            if bars:
                async with connection.transaction():
                    await connection.executemany(
                        """INSERT INTO price_bars
                               (instrument_id, source_id, interval, bar_date, open, high, low, close, volume, quote_code, metadata)
                           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb)
                           ON CONFLICT (instrument_id, source_id, interval, bar_date) DO UPDATE SET
                               open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
                               close = EXCLUDED.close, volume = EXCLUDED.volume, quote_code = EXCLUDED.quote_code,
                               metadata = EXCLUDED.metadata""",
                        bars,
                    )
                    await _record_source_result(connection)
            rows = await connection.fetch(
                """SELECT bar_date, open, high, low, close, volume, quote_code
                   FROM price_bars WHERE instrument_id = $1 AND interval = $2
                   ORDER BY bar_date DESC LIMIT $3""",
                instrument_id, interval, limit,
            )
            return {
                "instrument": {"id": str(instrument_id), "symbol": instrument["symbol"], "name": instrument["name"]},
                "provider": "Twelve Data",
                "interval": interval,
                "updated_count": len(bars),
                "items": [dict(row) for row in rows],
            }
        except HTTPException as exc:
            await _record_source_result(connection, str(exc.detail))
            raise
    finally:
        await connection.close()
