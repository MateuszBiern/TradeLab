import { copy } from "../../app/copy";
import type { ResearchSource } from "./types";

type Props = { sources: ResearchSource[] };

function shortError(source: ResearchSource): string {
  const error = source.last_error ?? "";
  const code = error.match(/\b(\d{3})\b/)?.[1];
  if (code === "429") return "Źródło ograniczyło liczbę zapytań (HTTP 429).";
  if (code) return `Źródło zwróciło błąd HTTP ${code}.`;
  return error.length > 100 ? `${error.slice(0, 97)}…` : error;
}

export function ResearchSources({ sources }: Props) {
  return (
    <section className="global-section">
      <div className="section-title"><div><p className="card-label">EVIDENCE PIPELINE</p><h2>{copy.sourcesTitle}</h2></div></div>
      <div className="research-source-grid">
        {sources.map((source) => <article className="research-source" key={source.id}>
          <span className={`source-indicator ${source.status === "connected" ? "connected" : source.status === "error" ? "error" : source.status === "needs_credentials" ? "needs-config" : ""}`} />
          <div><h3>{source.name}</h3><p title={source.status === "error" ? source.last_error ?? undefined : undefined}>{source.status === "connected" ? `${copy.lastSync}: ${source.last_success_at ? new Date(source.last_success_at).toLocaleString() : ""}` : source.status === "error" ? `${copy.sourceError}: ${shortError(source)}` : source.status === "needs_credentials" ? source.setup_message : copy.waitingSync}</p></div>
        </article>)}
      </div>
    </section>
  );
}
