CREATE TABLE IF NOT EXISTS price_bars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES research_sources(id) ON DELETE RESTRICT,
    interval TEXT NOT NULL CHECK (interval IN ('1day', '1week', '1month')),
    bar_date DATE NOT NULL,
    open NUMERIC(30,12) NOT NULL,
    high NUMERIC(30,12) NOT NULL,
    low NUMERIC(30,12) NOT NULL,
    close NUMERIC(30,12) NOT NULL,
    volume NUMERIC(30,4),
    quote_code TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (instrument_id, source_id, interval, bar_date)
);

CREATE INDEX IF NOT EXISTS idx_price_bars_instrument_date
    ON price_bars(instrument_id, interval, bar_date DESC);

INSERT INTO research_sources (source_key, name, source_type, base_url, enabled)
VALUES ('twelve_data_prices', 'Twelve Data - ceny akcji i ETF-ów', 'market_data',
    'https://api.twelvedata.com', TRUE)
ON CONFLICT (source_key) WHERE source_key IS NOT NULL DO NOTHING;

WITH seed(symbol, name, country_code, mic, exchange_name, currency, asset_class) AS (
    VALUES
        ('AAPL','Apple Inc','US','XNAS','NASDAQ','USD','stock'),
        ('MSFT','Microsoft Corporation','US','XNAS','NASDAQ','USD','stock'),
        ('NVDA','NVIDIA Corporation','US','XNAS','NASDAQ','USD','stock'),
        ('AMZN','Amazon.com Inc','US','XNAS','NASDAQ','USD','stock'),
        ('GOOGL','Alphabet Inc','US','XNAS','NASDAQ','USD','stock'),
        ('META','Meta Platforms Inc','US','XNAS','NASDAQ','USD','stock'),
        ('TSLA','Tesla Inc','US','XNAS','NASDAQ','USD','stock'),
        ('AVGO','Broadcom Inc','US','XNAS','NASDAQ','USD','stock'),
        ('JPM','JPMorgan Chase & Co','US','XNYS','NYSE','USD','stock'),
        ('XOM','Exxon Mobil Corporation','US','XNYS','NYSE','USD','stock'),
        ('LLY','Eli Lilly and Company','US','XNYS','NYSE','USD','stock'),
        ('BRK.B','Berkshire Hathaway Inc Class B','US','XNYS','NYSE','USD','stock'),
        ('SPY','SPDR S&P 500 ETF Trust','US','ARCX','NYSE Arca','USD','etf'),
        ('PKO','PKO Bank Polski SA','PL','XWAR','WSE','PLN','stock'),
        ('PKN','ORLEN SA','PL','XWAR','WSE','PLN','stock'),
        ('PZU','PZU SA','PL','XWAR','WSE','PLN','stock'),
        ('KGH','KGHM Polska Miedź SA','PL','XWAR','WSE','PLN','stock'),
        ('CDR','CD Projekt SA','PL','XWAR','WSE','PLN','stock'),
        ('ALE','Allegro.eu SA','PL','XWAR','WSE','PLN','stock'),
        ('AZN','AstraZeneca PLC','GB','XLON','LSE','GBP','stock'),
        ('HSBA','HSBC Holdings PLC','GB','XLON','LSE','GBP','stock'),
        ('SAP','SAP SE','DE','XETR','XETRA','EUR','stock'),
        ('SIE','Siemens AG','DE','XETR','XETRA','EUR','stock'),
        ('MC','LVMH Moet Hennessy Louis Vuitton SE','FR','XPAR','Euronext Paris','EUR','stock'),
        ('7203','Toyota Motor Corporation','JP','XTKS','Tokyo Stock Exchange','JPY','stock'),
        ('0700','Tencent Holdings Ltd','HK','XHKG','Hong Kong Stock Exchange','HKD','stock'),
        ('RELIANCE','Reliance Industries Ltd','IN','XNSE','National Stock Exchange of India','INR','stock'),
        ('PETR4','Petroleo Brasileiro SA','BR','BVMF','B3','BRL','stock'),
        ('RY','Royal Bank of Canada','CA','XTSE','Toronto Stock Exchange','CAD','stock'),
        ('NESN','Nestle SA','CH','XSWX','SIX Swiss Exchange','CHF','stock'),
        ('BHP','BHP Group Ltd','AU','XASX','Australian Securities Exchange','AUD','stock')
), entity_upsert AS (
    INSERT INTO entities (entity_type, canonical_key, name, country_code, attributes)
    SELECT CASE WHEN asset_class = 'etf' THEN 'fund' ELSE 'company' END,
        'listed:' || mic || ':' || symbol, name, country_code,
        jsonb_build_object('seeded', true, 'exchange', exchange_name, 'currency', currency)
    FROM seed
    ON CONFLICT (canonical_key) DO UPDATE SET
        name = EXCLUDED.name,
        country_code = EXCLUDED.country_code,
        attributes = entities.attributes || EXCLUDED.attributes
    RETURNING id, canonical_key
)
INSERT INTO instruments (entity_id, asset_class, venue_code, symbol, quote_code, attributes)
SELECT e.id, s.asset_class, s.mic, s.symbol, s.currency,
    jsonb_build_object('provider', 'twelve_data', 'provider_symbol', s.symbol,
        'provider_exchange', s.exchange_name, 'provider_mic_code', s.mic, 'seeded', true)
FROM seed s
JOIN entity_upsert e ON e.canonical_key = 'listed:' || s.mic || ':' || s.symbol
ON CONFLICT (venue_code, symbol, asset_class) DO UPDATE SET
    entity_id = EXCLUDED.entity_id,
    quote_code = EXCLUDED.quote_code,
    attributes = instruments.attributes || EXCLUDED.attributes,
    updated_at = NOW();
