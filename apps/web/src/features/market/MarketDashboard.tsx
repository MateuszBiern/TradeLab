import { copy } from "../../app/copy";
import { CandlesTable } from "./CandlesTable";
import { ComparisonTable } from "./ComparisonTable";
import { MarketControls } from "./MarketControls";
import { PriceSummary } from "./PriceSummary";
import { useMarketData } from "./useMarketData";

export function MarketDashboard() {
  const market = useMarketData();
  const base = market.symbol.split("/")[0];

  return (
    <section className="market-card">
      <div className="section-heading">
        <div><p className="card-label">MULTI-EXCHANGE · SPOT</p><h2>{copy.marketTitle}</h2><p className="card-copy">{copy.marketNote}</p></div>
        <MarketControls
          exchanges={market.exchanges}
          markets={market.markets}
          exchange={market.exchange}
          symbol={market.symbol}
          timeframe={market.timeframe}
          loading={market.loading}
          onExchangeChange={market.chooseExchange}
          onSymbolChange={market.chooseSymbol}
          onTimeframeChange={market.setTimeframe}
          onRefresh={() => void market.refresh()}
        />
      </div>
      {market.error && <p className="error-message" role="alert">{market.error}</p>}
      {market.ticker ? <>
        <PriceSummary ticker={market.ticker} />
        <ComparisonTable base={base} markets={market.comparison} lastUpdated={market.lastUpdated} />
        <CandlesTable candles={market.candles} timeframe={market.timeframe} />
      </> : <p className="loading">{market.loading ? copy.loading : market.error}</p>}
    </section>
  );
}