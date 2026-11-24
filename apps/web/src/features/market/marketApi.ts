import type { Candle, CompareMarket, Exchange, Market, Ticker } from "./types";

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const marketApi = {
  getExchanges: () => getJson<{ exchanges: Exchange[] }>("/api/v1/market/exchanges"),
  getHealth: () => getJson<{ status: string }>("/api/v1/health"),
  getMarkets: (exchange: string) =>
    getJson<{ markets: Market[] }>(`/api/v1/market/symbols?${new URLSearchParams({ exchange })}`),
  getTicker: (exchange: string, symbol: string) =>
    getJson<Ticker>(`/api/v1/market/ticker?${new URLSearchParams({ exchange, symbol })}`),
  getCandles: (exchange: string, symbol: string, timeframe: string) =>
    getJson<{ candles: Candle[] }>(`/api/v1/market/candles?${new URLSearchParams({ exchange, symbol, timeframe, limit: "36" })}`),
  compare: (base: string) =>
    getJson<{ markets: CompareMarket[] }>(`/api/v1/market/compare?${new URLSearchParams({ base })}`),
};