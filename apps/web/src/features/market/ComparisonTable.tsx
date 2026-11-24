import { copy } from "../../app/copy";
import type { CompareMarket } from "./types";

function formatPrice(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: value >= 100 ? 2 : 6 }).format(value);
}

type Props = { base: string; markets: CompareMarket[]; lastUpdated: number | null };

export function ComparisonTable({ base, markets, lastUpdated }: Props) {
  const updatedTime = lastUpdated ? new Date(lastUpdated).toLocaleTimeString("pl-PL") : "";
  return (
    <>
      <div className="table-heading"><h3>{copy.compare}: {base}</h3><span>{lastUpdated ? `${copy.updated} ${updatedTime}` : ""}</span></div>
      <div className="table-wrap"><table><thead><tr><th>{copy.exchangeColumn}</th><th>{copy.pairColumn}</th><th>{copy.priceColumn}</th><th>{copy.changeColumn}</th><th>{copy.statusColumn}</th></tr></thead><tbody>
        {markets.map((market) => <tr key={market.exchange}>
          <td>{market.exchange_name}</td><td>{market.symbol ?? "-"}</td>
          <td>{formatPrice(market.last)} {market.quote ?? ""}</td>
          <td>{market.change_percent_24h == null ? "-" : `${market.change_percent_24h.toFixed(2)}%`}</td>
          <td><span className={market.available ? "available" : "unavailable"}>{market.available ? copy.available : copy.noPair}</span></td>
        </tr>)}
      </tbody></table></div>
    </>
  );
}