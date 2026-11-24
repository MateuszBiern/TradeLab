import { copy } from "../../app/copy";
import type { AssetClass, Coverage } from "./types";

type Props = { coverage: Coverage | null; loading: boolean };

const assetLabels: Record<string, string> = {
  stocks: copy.equity,
  etfs: copy.etf,
  crypto: copy.crypto,
  forex: copy.forex,
  commodities: copy.commodities,
};

function AssetCard({ asset }: { asset: AssetClass }) {
  const ready = asset.status === "market_data_adapter_available_research_pending" || asset.status === "research_sources_connected_market_data_available";
  const partial = asset.status === "research_sources_connected_market_data_pending";
  return (
    <article className="asset-card">
      <span className="asset-icon">{asset.id === "crypto" ? "₿" : asset.id === "stocks" ? "A" : asset.id === "etfs" ? "▦" : asset.id === "forex" ? "↔" : "◈"}</span>
      <h3>{assetLabels[asset.id] ?? asset.name}</h3>
      <p className={`asset-status ${ready || partial ? "ready" : "pending"}`}>{ready ? copy.statusResearchPending : partial ? copy.statusStocksPartial : copy.statusPending}</p>
    </article>
  );
}

export function CoverageSection({ coverage, loading }: Props) {
  const assets = coverage?.asset_classes ?? [
    { id: "stocks", name: "Stocks", status: "source_not_connected" as const },
    { id: "etfs", name: "ETFs", status: "source_not_connected" as const },
    { id: "crypto", name: "Crypto", status: "market_data_adapter_available_research_pending" as const },
    { id: "forex", name: "FX", status: "source_not_connected" as const },
    { id: "commodities", name: "Commodities", status: "source_not_connected" as const },
  ];
  return (
    <section className="global-section">
      <div className="section-title"><div><p className="card-label">GLOBAL UNIVERSE</p><h2>{copy.coverageTitle}</h2><p className="card-copy">{copy.coverageSubtitle}</p></div><span className="coverage-state">{loading ? copy.checking : copy.noSignals}</span></div>
      <div className="asset-grid">{assets.map((asset) => <AssetCard key={asset.id} asset={asset} />)}</div>
    </section>
  );
}
