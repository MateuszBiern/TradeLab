import { copy } from "../../app/copy";
import type { Opportunity } from "./types";

type Props = { opportunities: Opportunity[]; scannerStatus: string; loading: boolean };

export function OpportunityFeed({ opportunities, scannerStatus, loading }: Props) {
  return (
    <section className="global-section opportunity-section">
      <div className="section-title"><div><p className="card-label">RANKED RESEARCH</p><h2>{copy.opportunitiesTitle}</h2><p className="card-copy">{copy.opportunitiesSubtitle}</p></div><span className={`scan-state ${scannerStatus === "active" ? "active" : "pending"}`}>{scannerStatus === "active" ? "SCANNER ACTIVE" : copy.noSignals}</span></div>
      {loading ? <p className="empty-state">{copy.checking}</p> : opportunities.length === 0 ? <div className="empty-state">
        <span className="empty-icon">◎</span><h3>{copy.emptyTitle}</h3><p>{copy.emptyDescription}</p>
      </div> : <div className="opportunity-list">
        {opportunities.map((opportunity) => <article className="opportunity-card" key={opportunity.id}>
          <div className="opportunity-heading"><span className="opportunity-class">{opportunity.asset_class}</span><span className="confidence">{opportunity.confidence}%</span></div>
          <h3>{opportunity.asset_name}{opportunity.ticker ? ` · ${opportunity.ticker}` : ""}</h3>
          <p className="catalyst">{opportunity.catalyst}</p><p>{opportunity.thesis}</p>
          <p className="risk-summary">{opportunity.risk_summary}</p>
          <div className="source-links">{opportunity.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.title}</a>)}</div>
        </article>)}
      </div>}
    </section>
  );
}