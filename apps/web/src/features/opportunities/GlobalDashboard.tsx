import { useEffect, useState } from "react";
import { copy } from "../../app/copy";
import { researchApi } from "./researchApi";
import type { Coverage, Opportunity } from "./types";
import type { SourceDocument } from "./types";
import { CoverageSection } from "./CoverageSection";
import { OpportunityFeed } from "./OpportunityFeed";
import { ResearchSources } from "./ResearchSources";
import { VenueSection } from "./VenueSection";
import { RecentDocuments } from "./RecentDocuments";
import { InstrumentCatalog } from "../instruments/InstrumentCatalog";

export function GlobalDashboard() {
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [scannerStatus, setScannerStatus] = useState("not_configured");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const refresh = () => Promise.all([researchApi.getCoverage(), researchApi.getOpportunities(), researchApi.getDocuments()])
      .then(([nextCoverage, nextOpportunities, nextDocuments]) => {
        if (!active) return;
        setCoverage(nextCoverage);
        setOpportunities(nextOpportunities.items);
        setScannerStatus(nextOpportunities.scanner_status);
        setDocuments(nextDocuments.items);
      })
      .catch(() => {
        if (!active) return;
        setCoverage(null);
        setOpportunities([]);
        setScannerStatus("unavailable");
      })
      .finally(() => setLoading(false));
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  return (
    <div className="global-dashboard">
      <CoverageSection coverage={coverage} loading={loading} />
      <OpportunityFeed opportunities={opportunities} scannerStatus={scannerStatus} loading={loading} />
      <ResearchSources sources={coverage?.research_sources ?? []} />
      <RecentDocuments documents={documents} />
      <InstrumentCatalog />
      <VenueSection coverage={coverage} />
      <p className="global-disclaimer">{copy.disclaimer} <span>{copy.footerExecution}</span></p>
    </div>
  );
}
