# Data source configuration

TradeLabAI collects public source material locally. It does not automatically calculate a buy signal or place trades.

## Ready without credentials

- Google News RSS: broad searches covering company earnings, mergers, inflation, central banks, oil, sanctions, and drug approvals. Change `GOOGLE_NEWS_QUERY` and `GOOGLE_NEWS_LOCALE` in `.env` to adjust topics and region.
- World Bank API: annual inflation, GDP growth, and unemployment observations for the countries in `WORLD_BANK_COUNTRIES`.
- ClinicalTrials.gov and openFDA: clinical trial and US drug-approval records.

## Needs local setup

1. Copy `.env.example` to `.env` in the project root.
2. Fill only the credentials for sources you want to enable. Keep `.env` private; it is ignored by Git.
3. Run `docker compose up -d --build` after editing `.env`.

- SEC EDGAR: set `SEC_USER_AGENT` to an identifying application name and a real contact email, for example `TradeLabAI/0.1 contact=name@example.com`.
- YouTube: set `YOUTUBE_API_KEY` from a Google Cloud project with YouTube Data API v3 enabled. The worker makes at most one search request per hour and asks for up to 25 video titles/descriptions. YouTube API records are refreshed on retrieval and purged after 29 days if they are no longer returned.
- X: set `X_BEARER_TOKEN`, then explicitly set `X_INGESTION_ENABLED=true`. It searches recent posts, with a default maximum of 10 per hourly poll. X currently lists a usage price per post read; at the current published rate, 10 returned posts each hour would be about $1.20/day. Review the current [X API pricing](https://developer.x.com/) before enabling it.
- Instagram: set `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_USER_ID` for an Instagram Business or Creator account with the required app review access. Hashtag search is limited by Meta to 30 unique hashtags per rolling 7-day period. Configure `INSTAGRAM_HASHTAGS` conservatively.

Sources missing credentials appear as “configuration required” in the application and are skipped by the worker. Credentials are sent only to the local backend/worker containers and are not returned by the API. Social-source documents are purged after 29 days.

Global stock and ETF catalog/prices require TWELVE_DATA_API_KEY. The app starts with a small reference catalog across the US, Poland (WSE), UK, Germany, France, Japan, Hong Kong, India, Brazil, Canada, Switzerland, and Australia. Use the dashboard search to add other instruments. Daily, weekly, or monthly history is requested only when you press the price button; it is stored locally in price_bars. The provider documents equities and ETFs across 250+ exchanges, but symbol availability, delayed/realtime entitlement, and usage limits depend on the plan. See the [official symbol search](https://twelvedata.com/docs/discovery/symbol-search) and [time series](https://twelvedata.com/docs/market-data/time-series) documentation.

The stock-price connector is called only by a manual search or price-history request from the dashboard. It does not place orders. Its price history may be delayed and does not necessarily match the executable quote in your broker.

## Data coverage limits

These APIs provide samples and indexed records, not a complete view of every post or event worldwide. X recent search covers recent posts, YouTube search is quota-limited, and Instagram hashtag search only covers eligible public media. Social activity can be manipulated and should be treated as one evidence signal among filings, company announcements, market data, and other independent sources.
