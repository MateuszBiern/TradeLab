ALTER TABLE research_sources ADD COLUMN IF NOT EXISTS source_key TEXT;
ALTER TABLE research_sources ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE research_sources ADD COLUMN IF NOT EXISTS last_polled_at TIMESTAMPTZ;
CREATE UNIQUE INDEX IF NOT EXISTS uq_research_sources_source_key ON research_sources(source_key) WHERE source_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS source_ingestion_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES research_sources(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_ingestion_runs_source_started ON source_ingestion_runs(source_id, started_at DESC);

INSERT INTO research_sources (source_key, name, source_type, base_url, enabled)
VALUES
    ('gdelt_news', 'GDELT global news', 'news', 'https://api.gdeltproject.org/api/v2/doc/doc', TRUE),
    ('clinical_trials', 'ClinicalTrials.gov', 'clinical_trial', 'https://clinicaltrials.gov/api/v2/studies', TRUE),
    ('openfda_drugs', 'openFDA Drugs@FDA', 'regulator', 'https://api.fda.gov/drug/drugsfda.json', TRUE)
ON CONFLICT (source_key) WHERE source_key IS NOT NULL DO NOTHING;
