export type ApiStatus = "checking" | "online" | "offline";

export type Exchange = {
  id: string;
  name: string;
  market_type: string;
};

export type Market = {
  symbol: string;
  base: string;
  quote: string;
};

export type Ticker = {
  exchange: string;
  exchange_name: string;
  symbol: string;
  timestamp: number | null;
  last: number | null;
  bid: number | null;
  ask: number | null;
  change_percent_24h: number | null;
};

export type CompareMarket = {
  exchange: string;
  exchange_name: string;
  base: string;
  symbol?: string;
  quote?: string;
  available: boolean;
  last?: number | null;
  change_percent_24h?: number | null;
  reason?: string;
};

export type Candle = [number, number, number, number, number, number];