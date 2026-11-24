import { copy } from "../../app/copy";
import type { Exchange, Market } from "./types";

type Props = {
  exchanges: Exchange[];
  markets: Market[];
  exchange: string;
  symbol: string;
  timeframe: string;
  loading: boolean;
  onExchangeChange: (value: string) => void;
  onSymbolChange: (value: string) => void;
  onTimeframeChange: (value: string) => void;
  onRefresh: () => void;
};

export function MarketControls(props: Props) {
  return (
    <div className="controls">
      <label>{copy.exchange}<select value={props.exchange} onChange={(event) => props.onExchangeChange(event.target.value)}>
        {props.exchanges.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
      </select></label>
      <label>{copy.symbol}<select value={props.symbol} onChange={(event) => props.onSymbolChange(event.target.value)}>
        {props.markets.map((market) => <option key={market.symbol} value={market.symbol}>{market.symbol}</option>)}
      </select></label>
      <label>{copy.timeframe}<select value={props.timeframe} onChange={(event) => props.onTimeframeChange(event.target.value)}>
        <option value="15m">15m</option><option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option>
      </select></label>
      <button className="refresh" onClick={props.onRefresh} disabled={props.loading}>{props.loading ? "..." : copy.refresh}</button>
    </div>
  );
}