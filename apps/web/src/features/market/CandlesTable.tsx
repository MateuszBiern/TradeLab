import { copy } from "../../app/copy";
import type { Candle } from "./types";

function formatPrice(value: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: value >= 100 ? 2 : 6 }).format(value);
}

function formatTime(value: number) {
  return new Date(value).toLocaleString("pl-PL", { dateStyle: "short", timeStyle: "short" });
}

type Props = { candles: Candle[]; timeframe: string };

export function CandlesTable({ candles, timeframe }: Props) {
  return (
    <>
      <div className="table-heading"><h3>{copy.candles}</h3><span>{timeframe}</span></div>
      <div className="table-wrap"><table><thead><tr><th>{copy.time}</th><th>{copy.open}</th><th>{copy.high}</th><th>{copy.low}</th><th>{copy.close}</th><th>{copy.volume}</th></tr></thead><tbody>
        {candles.map((candle) => <tr key={candle[0]}>
          <td>{formatTime(candle[0])}</td><td>{formatPrice(candle[1])}</td><td>{formatPrice(candle[2])}</td>
          <td>{formatPrice(candle[3])}</td><td>{formatPrice(candle[4])}</td><td>{formatPrice(candle[5])}</td>
        </tr>)}
      </tbody></table></div>
    </>
  );
}