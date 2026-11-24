import { copy } from "../../app/copy";
import type { Ticker } from "./types";

function formatPrice(value: number | null) {
  if (value === null || !Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: value >= 100 ? 2 : 6 }).format(value);
}

type Props = { ticker: Ticker };

export function PriceSummary({ ticker }: Props) {
  const change = ticker.change_percent_24h;
  return (
    <div className="quote-grid">
      <article className="quote quote-primary"><span>{copy.price}</span><strong>{formatPrice(ticker.last)}</strong><small>{ticker.symbol} · {ticker.exchange_name}</small></article>
      <article className="quote"><span>{copy.change}</span><strong className={change !== null && change < 0 ? "negative" : "positive"}>{change === null ? "-" : `${change.toFixed(2)}%`}</strong></article>
      <article className="quote"><span>{copy.bid}</span><strong>{formatPrice(ticker.bid)}</strong></article>
      <article className="quote"><span>{copy.ask}</span><strong>{formatPrice(ticker.ask)}</strong></article>
    </div>
  );
}