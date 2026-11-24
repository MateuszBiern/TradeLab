# TradeLab AI

Local development scaffold for the TradeLab AI application.

## Start

1. Start Docker Desktop and wait until its engine is running.
2. From this folder run: `docker compose up --build`
3. Open the web app at http://localhost:5173
4. Open the API docs at http://localhost:8000/docs

The main screen is a global opportunity-research dashboard. It is designed to scan a supported universe across asset classes and present event-driven ideas with sources and risk context. A local worker now collects public documents from GDELT, ClinicalTrials.gov, and openFDA. The opportunity list remains empty because AI analysis and investment recommendations are not active.

The worker runs every 30 minutes by default. It collects global news, macro indicators, company filings, regulatory and clinical data, and optional social posts/videos. Some platforms require API credentials and app approval; paid sources are opt-in. See [data source setup](docs/data-sources.md). The collected sources are not exhaustive feeds of every market or world event.

CCXT adapters expose public crypto spot market data for Binance, Bybit, Kraken, and Coinbase Advanced. They do not execute trades. XTB is listed for manual follow-through; XTB states that its API was discontinued on March 14, 2025.

Stop with `Ctrl+C`, or run `docker compose down` in another terminal. Persistent database data is kept in a Docker volume.
## Data model

The dashboard also has a starter catalogue of global stocks and ETFs. Configure TWELVE_DATA_API_KEY in .env to search supported symbols and manually request daily prices. Bars are stored locally. This connector does not place orders; quote availability and delay depend on the provider plan.

The backend applies SQL files from `database/migrations` at startup and records applied files in `schema_migrations`. The migrations create source/document and ingestion-run, entity/instrument, event/evidence, agent-run/analysis, opportunity, user-decision, price-observation, and investor-preference tables. The API exposes connector health and recent documents; the dashboard refreshes them every minute.
