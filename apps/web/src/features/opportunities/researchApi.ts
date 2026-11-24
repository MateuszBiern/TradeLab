import type { Coverage, Opportunity, SourceDocument } from "./types";

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const researchApi = {
  getCoverage: () => getJson<Coverage>("/api/v1/coverage"),
  getOpportunities: () => getJson<{ scanner_status: string; items: Opportunity[] }>("/api/v1/opportunities"),
  getDocuments: () => getJson<{ items: SourceDocument[] }>("/api/v1/documents?limit=40"),
};
