import os

import asyncpg
from fastapi import APIRouter

from app.connectors.market_data.ccxt_client import EXCHANGES
from app.connectors.research.readiness import SOURCE_SETUP, missing_configuration

router = APIRouter(prefix="/api/v1", tags=["global-research"])

ASSET_CLASSES = [
    {"id": "stocks", "name": "Globalne akcje", "status": "research_sources_connected_market_data_pending"},
    {"id": "etfs", "name": "ETF-y", "status": "research_sources_connected_market_data_pending"},
    {"id": "crypto", "name": "Kryptowaluty", "status": "market_data_adapter_available_research_pending"},
    {"id": "forex", "name": "Waluty", "status": "source_not_connected"},
    {"id": "commodities", "name": "Surowce", "status": "source_not_connected"},
]

SOURCE_NAMES = {
    "gdelt_news": "Globalne wiadomo\u015bci (GDELT)",
    "clinical_trials": "Badania kliniczne (ClinicalTrials.gov)",
    "openfda_drugs": "Zg\u0142oszenia lek\u00f3w (openFDA)",
    "google_news": "Wiadomo\u015bci z wielu temat\u00f3w (Google News)",
    "sec_filings": "Raporty sp\u00f3\u0142ek (SEC EDGAR)",
    "world_bank": "Wska\u017aniki makro (World Bank)",
    "x_posts": "Wpisy publiczne (X)",
    "youtube_videos": "Wyniki wyszukiwania film\u00f3w (YouTube)",
    "instagram_posts": "Publiczne posty z hashtag\u00f3w (Instagram)",
    "twelve_data_prices": "Ceny akcji i ETF-\u00f3w (Twelve Data)",
}


async def _db():
    return await asyncpg.connect(os.environ["DATABASE_URL"])


@router.get("/coverage")
async def coverage():
    connection = await _db()
    try:
        rows = await connection.fetch("""SELECT source_key, enabled, last_success_at, last_polled_at, last_error
            FROM research_sources WHERE source_key IS NOT NULL ORDER BY source_key""")
    finally:
        await connection.close()
    sources = [{"id": row["source_key"], "name": SOURCE_NAMES.get(row["source_key"], row["source_key"]),
        "status": "needs_credentials" if missing_configuration(row["source_key"]) else ("error" if row["last_error"] else ("connected" if row["last_success_at"] else "waiting")),
        "enabled": row["enabled"], "last_success_at": row["last_success_at"].isoformat() if row["last_success_at"] else None,
        "last_error": row["last_error"],
        "setup_message": SOURCE_SETUP.get(row["source_key"], ((), ""))[1]} for row in rows]
    stock_data_ready = any(
        source["id"] == "twelve_data_prices" and source["status"] == "connected"
        for source in sources
    )
    asset_classes = [
        {**asset, "status": "research_sources_connected_market_data_available"}
        if stock_data_ready and asset["id"] in {"stocks", "etfs"} else asset
        for asset in ASSET_CLASSES
    ]
    return {
        "scan_mode": "global_supported_universe",
        "asset_classes": asset_classes,
        "research_sources": sources,
        "market_data_venues": [
            {"id": exchange_id, "name": name, "asset_class": "crypto", "status": "public_market_data_adapter_available", "execution": "not_configured"}
            for exchange_id, name in EXCHANGES.items()
        ],
        "execution_venues": [
            {"id": "xtb", "name": "XTB", "status": "manual_only", "api_available": False},
        ],
        "scanner_status": "collecting" if any(source["status"] == "connected" for source in sources) else "waiting_for_first_sync",
    }


@router.get("/opportunities")
async def opportunities():
    return {"scanner_status": "research_only_no_ai", "items": []}


@router.get("/documents")
async def recent_documents(limit: int = 50):
    limit = min(max(limit, 1), 200)
    connection = await _db()
    try:
        rows = await connection.fetch("""WITH source_rows AS (
                SELECT d.id, s.source_key, d.external_id, d.canonical_url, d.title,
                    d.published_at, d.retrieved_at, d.body_text, d.metadata,
                    CASE WHEN s.source_key = 'world_bank'
                        THEN make_date(NULLIF(d.metadata->>'year', '')::integer, 1, 1)::timestamptz
                        ELSE COALESCE(d.published_at, d.retrieved_at)
                    END AS display_at,
                    row_number() OVER (
                        PARTITION BY s.source_key,
                            CASE WHEN s.source_key = 'world_bank'
                                THEN concat_ws(':', d.metadata->>'indicator_code', d.metadata->>'country_code')
                                ELSE d.id::text END
                        ORDER BY NULLIF(d.metadata->>'year', '') DESC NULLS LAST,
                            COALESCE(d.published_at, d.retrieved_at) DESC
                    ) AS record_rank
                FROM source_documents d
                JOIN research_sources s ON s.id = d.source_id
            ), current_rows AS (
                SELECT * FROM source_rows
                WHERE source_key <> 'world_bank' OR record_rank = 1
            ), source_total AS (
                SELECT COUNT(DISTINCT source_key) AS count FROM current_rows
            ), ranked AS (
                SELECT current_rows.*,
                    row_number() OVER (PARTITION BY source_key ORDER BY display_at DESC, retrieved_at DESC) AS source_rank,
                    (SELECT count FROM source_total) AS source_count
                FROM current_rows
            )
            SELECT id, source_key, external_id, canonical_url, title, published_at, retrieved_at, body_text, metadata
            FROM ranked
            WHERE source_rank <= CEIL($1::numeric / NULLIF(source_count, 0))
            ORDER BY display_at DESC, retrieved_at DESC
            LIMIT $1""", limit)
        return {"items": [dict(row) for row in rows]}
    finally:
        await connection.close()
