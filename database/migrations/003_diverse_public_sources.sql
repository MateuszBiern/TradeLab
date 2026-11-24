ALTER TABLE research_sources DROP CONSTRAINT IF EXISTS research_sources_source_type_check;
ALTER TABLE research_sources ADD CONSTRAINT research_sources_source_type_check
    CHECK (source_type IN ('news', 'company_filing', 'regulator', 'clinical_trial', 'market_data', 'user_material', 'social', 'other'));

INSERT INTO research_sources (source_key, name, source_type, base_url, enabled)
VALUES
    ('google_news', 'Google News RSS', 'news', 'https://news.google.com/rss/search', TRUE),
    ('sec_filings', 'SEC EDGAR filings', 'company_filing', 'https://www.sec.gov/cgi-bin/browse-edgar', TRUE),
    ('world_bank', 'World Bank indicators', 'other', 'https://api.worldbank.org/v2', TRUE),
    ('x_posts', 'X posts search', 'social', 'https://api.x.com/2/tweets/search/recent', TRUE),
    ('youtube_videos', 'YouTube videos search', 'social', 'https://www.googleapis.com/youtube/v3/search', TRUE),
    ('instagram_posts', 'Instagram hashtag posts', 'social', 'https://graph.facebook.com', TRUE)
ON CONFLICT (source_key) WHERE source_key IS NOT NULL DO NOTHING;
