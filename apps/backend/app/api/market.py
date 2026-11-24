import asyncio

from fastapi import APIRouter, Query

from app.connectors.market_data.ccxt_client import (
    DEFAULT_EXCHANGE,
    DEFAULT_SYMBOL,
    EXCHANGES,
    fetch_base_ticker,
    fetch_candles,
    fetch_ticker,
    list_spot_markets,
    normalize_exchange,
)

router = APIRouter(prefix="/api/v1/market", tags=["market"])


@router.get("/config")
async def market_config():
    return {"exchanges": EXCHANGES, "default_exchange": DEFAULT_EXCHANGE, "default_symbol": DEFAULT_SYMBOL, "mode": "read_only_public_data"}


@router.get("/exchanges")
async def market_exchanges():
    return {"exchanges": [{"id": exchange_id, "name": name, "market_type": "spot"} for exchange_id, name in EXCHANGES.items()]}


@router.get("/symbols")
async def market_symbols(exchange: str = Query(default=DEFAULT_EXCHANGE)):
    exchange_id = normalize_exchange(exchange)
    return {"exchange": exchange_id, "markets": await list_spot_markets(exchange_id)}


@router.get("/ticker")
async def market_ticker(
    exchange: str = Query(default=DEFAULT_EXCHANGE),
    symbol: str = Query(default=DEFAULT_SYMBOL, min_length=3, max_length=30),
):
    return await fetch_ticker(exchange, symbol)


@router.get("/candles")
async def market_candles(
    exchange: str = Query(default=DEFAULT_EXCHANGE),
    symbol: str = Query(default=DEFAULT_SYMBOL, min_length=3, max_length=30),
    timeframe: str = Query(default="1h"),
    limit: int = Query(default=48, ge=1, le=200),
):
    exchange_id = normalize_exchange(exchange)
    return {
        "exchange": exchange_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": await fetch_candles(exchange_id, symbol, timeframe, limit),
    }


@router.get("/compare")
async def market_compare(base: str = Query(default="BTC", min_length=2, max_length=12)):
    rows = await asyncio.gather(*(fetch_base_ticker(exchange_id, base) for exchange_id in EXCHANGES))
    return {"base": base.upper(), "markets": rows}