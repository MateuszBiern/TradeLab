export type ApiStatus = "checking" | "online" | "offline";
export type CoverageStatus = "source_not_connected" | "market_data_adapter_available_research_pending" | "research_sources_connected_market_data_pending" | "research_sources_connected_market_data_available";

export type AssetClass = { id: string; name: string; status: CoverageStatus };
export type ResearchSource = { id: string; name: string; status: string; enabled?: boolean; last_success_at?: string | null; last_error?: string | null; setup_message?: string };
export type SourceDocument = { id: string; source_key: string; title: string; canonical_url?: string | null; published_at?: string | null; retrieved_at: string; body_text?: string | null; metadata?: string | Record<string, unknown> | null };
export type MarketDataVenue = { id: string; name: string; asset_class: string; status: string; execution: string };
export type ExecutionVenue = { id: string; name: string; status: string; api_available: boolean };

export type Coverage = {
  scan_mode: string;
  asset_classes: AssetClass[];
  research_sources: ResearchSource[];
  market_data_venues: MarketDataVenue[];
  execution_venues: ExecutionVenue[];
  scanner_status: string;
};

export type Opportunity = {
  id: string;
  asset_class: string;
  asset_name: string;
  ticker?: string;
  catalyst: string;
  thesis: string;
  risk_summary: string;
  confidence: number;
  sources: Array<{ title: string; url: string; published_at?: string }>;
};
