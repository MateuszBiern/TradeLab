CREATE TABLE IF NOT EXISTS research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('news', 'company_filing', 'regulator', 'clinical_trial', 'market_data', 'user_material', 'other')),
    base_url TEXT,
    access_mode TEXT NOT NULL DEFAULT 'public',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_success_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL CHECK (entity_type IN ('company', 'fund', 'crypto_asset', 'drug', 'clinical_trial', 'regulator', 'person', 'currency', 'commodity', 'other')),
    canonical_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    country_code CHAR(2),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instruments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    asset_class TEXT NOT NULL CHECK (asset_class IN ('stock', 'etf', 'crypto', 'forex', 'commodity', 'other')),
    venue_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    base_code TEXT,
    quote_code TEXT,
    isin TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (venue_code, symbol, asset_class)
);

CREATE INDEX IF NOT EXISTS idx_instruments_entity ON instruments(entity_id);
CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);
CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments(symbol);

CREATE TABLE IF NOT EXISTS source_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES research_sources(id) ON DELETE RESTRICT,
    external_id TEXT,
    canonical_url TEXT,
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    content_hash CHAR(64) NOT NULL,
    body_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (source_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_source_documents_published ON source_documents(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_source_documents_url ON source_documents(canonical_url);

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    event_status TEXT NOT NULL DEFAULT 'detected' CHECK (event_status IN ('detected', 'confirmed', 'disputed', 'resolved', 'dismissed')),
    occurred_at TIMESTAMPTZ,
    expected_at TIMESTAMPTZ,
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_type_date ON events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_status ON events(event_status);

CREATE TABLE IF NOT EXISTS event_documents (
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    evidence_role TEXT NOT NULL DEFAULT 'supporting',
    relevance_score NUMERIC(5,4) CHECK (relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)),
    PRIMARY KEY (event_id, document_id)
);

CREATE TABLE IF NOT EXISTS event_entities (
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation TEXT NOT NULL DEFAULT 'related',
    relevance_score NUMERIC(5,4) CHECK (relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)),
    PRIMARY KEY (event_id, entity_id, relation)
);

CREATE TABLE IF NOT EXISTS price_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    source_id UUID REFERENCES research_sources(id) ON DELETE SET NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    price NUMERIC(30,12) NOT NULL CHECK (price >= 0),
    bid NUMERIC(30,12),
    ask NUMERIC(30,12),
    volume_24h NUMERIC(30,12),
    quote_code TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_price_observations_instrument_time ON price_observations(instrument_id, observed_at DESC);

CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    model_name TEXT,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_status_created ON agent_runs(status, created_at DESC);

CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    instrument_id UUID REFERENCES instruments(id) ON DELETE SET NULL,
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    summary TEXT NOT NULL,
    positive_case TEXT,
    negative_case TEXT,
    risk_summary TEXT,
    horizon TEXT,
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    data_cutoff_at TIMESTAMPTZ,
    findings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analyses_event_created ON analyses(event_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_instrument_created ON analyses(instrument_id, created_at DESC);

CREATE TABLE IF NOT EXISTS opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES events(id) ON DELETE SET NULL,
    instrument_id UUID NOT NULL REFERENCES instruments(id) ON DELETE RESTRICT,
    analysis_id UUID REFERENCES analyses(id) ON DELETE SET NULL,
    direction TEXT NOT NULL CHECK (direction IN ('positive', 'negative', 'watch')),
    thesis TEXT NOT NULL,
    risk_level TEXT CHECK (risk_level IS NULL OR risk_level IN ('low', 'medium', 'high', 'very_high')),
    horizon TEXT,
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    reference_price NUMERIC(30,12),
    reference_currency TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'needs_review', 'approved', 'rejected', 'expired', 'closed')),
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_opportunities_status_date ON opportunities(status, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_opportunities_instrument_date ON opportunities(instrument_id, detected_at DESC);

CREATE TABLE IF NOT EXISTS opportunity_documents (
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES source_documents(id) ON DELETE RESTRICT,
    usage TEXT NOT NULL DEFAULT 'evidence',
    PRIMARY KEY (opportunity_id, document_id)
);

CREATE TABLE IF NOT EXISTS user_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    opportunity_id UUID NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'watch', 'defer')),
    note TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_decisions_opportunity_date ON user_decisions(opportunity_id, decided_at DESC);

CREATE TABLE IF NOT EXISTS investor_preferences (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    risk_tolerance TEXT CHECK (risk_tolerance IS NULL OR risk_tolerance IN ('low', 'medium', 'high', 'custom')),
    investment_horizon TEXT,
    enabled_asset_classes JSONB NOT NULL DEFAULT '["stock", "etf", "crypto", "forex", "commodity"]'::jsonb,
    max_position_risk_percent NUMERIC(5,2) CHECK (max_position_risk_percent IS NULL OR (max_position_risk_percent > 0 AND max_position_risk_percent <= 100)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);