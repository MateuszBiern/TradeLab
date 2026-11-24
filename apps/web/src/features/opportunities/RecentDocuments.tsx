import type { SourceDocument } from "./types";

type Details = {
  status?: string;
  phase?: string[] | null;
  conditions?: string[];
  sponsor?: string;
  latest_submission_type?: string;
  latest_submission_status?: string;
  indicator?: string;
  value?: number | string | null;
  unit?: string;
  year?: string;
};

const sourceLabels: Record<string, string> = {
  clinical_trials: "Badanie kliniczne",
  openfda_drugs: "FDA - zg\u0142oszenie leku",
  gdelt_news: "Wiadomo\u015b\u0107 ze \u015bwiata",
  google_news: "Wiadomo\u015b\u0107 z Google News",
  world_bank: "Wska\u017aniki makro (World Bank)",
  sec_filings: "Raport sp\u00f3\u0142ki (SEC)",
  youtube_videos: "YouTube",
  x_posts: "Wpis z X",
  instagram_posts: "Instagram",
};

const studyStatuses: Record<string, string> = {
  RECRUITING: "Trwa rekrutacja",
  NOT_YET_RECRUITING: "Rekrutacja jeszcze si\u0119 nie rozpocz\u0119\u0142a",
  ACTIVE_NOT_RECRUITING: "Badanie trwa, bez rekrutacji",
  COMPLETED: "Badanie zako\u0144czone",
  TERMINATED: "Badanie przerwane",
  ENROLLING_BY_INVITATION: "Nab\u00f3r na zaproszenie",
  SUSPENDED: "Badanie zawieszone",
  WITHDRAWN: "Badanie wycofane",
};

function parseDetails(body: string | null | undefined): Details | null {
  if (!body?.trim().startsWith("{")) return null;
  try {
    const parsed: unknown = JSON.parse(body);
    return parsed && typeof parsed === "object" ? parsed as Details : null;
  } catch {
    return null;
  }
}

function parseMetadata(metadata: SourceDocument["metadata"]): Record<string, unknown> {
  if (typeof metadata === "string") {
    try { return JSON.parse(metadata) as Record<string, unknown>; } catch { return {}; }
  }
  return metadata && typeof metadata === "object" ? metadata : {};
}

function DocumentDetails({ document }: { document: SourceDocument }) {
  const details = parseDetails(document.body_text);
  if (!details) {
    return document.body_text && document.body_text !== document.title
      ? <p className="document-summary">{document.body_text}</p>
      : null;
  }

  if (document.source_key === "clinical_trials") {
    const phases = details.phase?.filter((phase) => phase !== "NA").map((phase) => phase.replace("PHASE", "Faza ")) ?? [];
    const conditions = details.conditions ?? [];
    return <div className="document-facts">
      <span><b>Status</b>{studyStatuses[details.status ?? ""] ?? details.status ?? "Niepodany"}</span>
      {phases.length > 0 && <span><b>Faza</b>{phases.join(", ")}</span>}
      {conditions.length > 0 && <span className="document-conditions"><b>Badane schorzenia</b>{conditions.slice(0, 3).join(", ")}{conditions.length > 3 ? ` + ${conditions.length - 3}` : ""}</span>}
    </div>;
  }

  if (document.source_key === "openfda_drugs") {
    return <div className="document-facts">
      {details.sponsor && <span><b>Firma</b>{details.sponsor}</span>}
      {details.latest_submission_type && <span><b>{"Typ zg\u0142oszenia"}</b>{details.latest_submission_type}</span>}
      {details.latest_submission_status && <span><b>Status FDA</b>{details.latest_submission_status}</span>}
    </div>;
  }

  if (document.source_key === "world_bank") {
    const metadata = parseMetadata(document.metadata);
    const indicatorNames: Record<string, string> = {
      "Inflation, consumer prices (annual %)": "Inflacja (roczna)",
      "GDP growth (annual %)": "Wzrost PKB (roczny)",
      "Unemployment, total (% of total labor force) (modeled ILO estimate)": "Bezrobocie",
    };
    const indicator = typeof details.indicator === "string" ? details.indicator : "";
    const year = details.year ?? (typeof metadata.year === "string" ? metadata.year : undefined);
    const numericValue = typeof details.value === "number"
      ? new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 2 }).format(details.value)
      : details.value ?? "Brak danych";
    return <div className="document-facts">
      {indicator && <span><b>Wska\u017anik</b>{indicatorNames[indicator] ?? indicator}</span>}
      <span><b>Warto\u015b\u0107</b>{numericValue}{details.unit ? ` ${details.unit}` : " %"}</span>
      {year && <span><b>Rok</b>{year}</span>}
    </div>;
  }

  return null;
}

export function RecentDocuments({ documents }: { documents: SourceDocument[] }) {
  return <section className="global-section">
    <div className="section-title"><div><p className="card-label">ZEBRANE DANE</p><h2>{"Ostatnie informacje ze \u017ar\u00f3de\u0142"}</h2><p className="card-copy">{"Ka\u017cdy wpis pokazuje dost\u0119pne szczeg\u00f3\u0142y i odno\u015bnik do oryginalnego \u017ar\u00f3d\u0142a."}</p></div></div>
    {documents.length === 0 ? <p className="empty-state">{"Nie ma jeszcze zapisanych informacji. Sprawd\u017a status pod\u0142\u0105czonych \u017ar\u00f3de\u0142."}</p> : <div className="document-list">
      {documents.map((doc) => <article className="document-row" key={doc.id}>
        <div className="document-content"><span className="document-source">{sourceLabels[doc.source_key] ?? doc.source_key.replaceAll("_", " ")}</span><h3>{doc.canonical_url ? <a href={doc.canonical_url} target="_blank" rel="noreferrer">{doc.title}</a> : doc.title}</h3><DocumentDetails document={doc} /></div>
        <time>{doc.source_key === "world_bank"
          ? (parseMetadata(doc.metadata).year as string | undefined) ?? "Dane roczne"
          : doc.published_at ? new Date(doc.published_at).toLocaleDateString() : new Date(doc.retrieved_at).toLocaleDateString()}</time>
      </article>)}
    </div>}
  </section>;
}
