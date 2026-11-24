import { useCallback, useEffect, useState } from "react";
import { copy } from "../../app/copy";
import { marketApi } from "./marketApi";
import type { ApiStatus, Candle, CompareMarket, Exchange, Market, Ticker } from "./types";

const defaultExchanges: Exchange[] = [
  { id: "binance", name: "Binance", market_type: "spot" },
  { id: "bybit", name: "Bybit", market_type: "spot" },
  { id: "kraken", name: "Kraken", market_type: "spot" },
  { id: "coinbase", name: "Coinbase Advanced", market_type: "spot" },
];

function preferredMarket(markets: Market[], base: string): string {
  const quotePriority = ["USDT", "USD", "USDC", "EUR"];
  const matching = markets.filter((market) => market.base === base);
  matching.sort((a, b) => {
    const aIndex = quotePriority.indexOf(a.quote);
    const bIndex = quotePriority.indexOf(b.quote);
    return (aIndex < 0 ? 99 : aIndex) - (bIndex < 0 ? 99 : bIndex) || a.symbol.localeCompare(b.symbol);
  });
  return matching[0]?.symbol ?? markets[0]?.symbol ?? "";
}

export function useMarketData() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");
  const [exchanges, setExchanges] = useState<Exchange[]>(defaultExchanges);
  const [exchange, setExchange] = useState("binance");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [symbol, setSymbol] = useState("");
  const [preferredBase, setPreferredBase] = useState("BTC");
  const [timeframe, setTimeframe] = useState("1h");
  const [ticker, setTicker] = useState<Ticker | null>(null);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [comparison, setComparison] = useState<CompareMarket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  useEffect(() => {
    marketApi.getExchanges().then((data) => setExchanges(data.exchanges)).catch(() => setExchanges(defaultExchanges));
    marketApi.getHealth().then(() => setApiStatus("online")).catch(() => setApiStatus("offline"));
  }, []);

  useEffect(() => {
    let active = true;
    setMarkets([]);
    setSymbol("");
    setTicker(null);
    setCandles([]);
    setComparison([]);
    marketApi.getMarkets(exchange)
      .then((data) => {
        if (!active) return;
        setMarkets(data.markets);
        setSymbol(preferredMarket(data.markets, preferredBase));
        setError("");
      })
      .catch(() => {
        if (active) setError(copy.marketDataError);
      });
    return () => { active = false; };
  }, [exchange]);

  const refresh = useCallback(async () => {
    if (!symbol) return;
    setLoading(true);
    setError("");
    try {
      const base = symbol.split("/")[0];
      const [nextTicker, candleData, compareData] = await Promise.all([
        marketApi.getTicker(exchange, symbol),
        marketApi.getCandles(exchange, symbol, timeframe),
        marketApi.compare(base),
      ]);
      setTicker(nextTicker);
      setCandles(candleData.candles.slice().reverse());
      setComparison(compareData.markets);
      setLastUpdated(Date.now());
      setApiStatus("online");
    } catch {
      setError(copy.unavailable);
    } finally {
      setLoading(false);
    }
  }, [exchange, symbol, timeframe]);

  useEffect(() => { void refresh(); }, [refresh]);

  const chooseExchange = (nextExchange: string) => {
    if (nextExchange === exchange) return;
    setPreferredBase(symbol.split("/")[0] || preferredBase);
    setExchange(nextExchange);
  };

  const chooseSymbol = (nextSymbol: string) => {
    setSymbol(nextSymbol);
    setPreferredBase(nextSymbol.split("/")[0]);
  };

  return {
    apiStatus,
    exchanges,
    exchange,
    markets,
    symbol,
    timeframe,
    ticker,
    candles,
    comparison,
    loading,
    error,
    lastUpdated,
    chooseExchange,
    chooseSymbol,
    setTimeframe,
    refresh,
  };
}