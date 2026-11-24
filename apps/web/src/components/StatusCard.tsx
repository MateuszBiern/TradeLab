import { copy } from "../app/copy";
import type { ApiStatus } from "../features/market/types";

type Props = { status: ApiStatus };

export function StatusCard({ status }: Props) {
  return (
    <section className="status-card" aria-live="polite">
      <div>
        <p className="card-label">{copy.connection}</p>
        <h2>{status === "online" ? copy.systemReady : status === "checking" ? copy.checking : copy.apiUnavailable}</h2>
        <p className="card-copy">{status === "online" ? copy.online : copy.offline}</p>
      </div>
      <span className={`status-pill ${status}`}>
        <span />{status === "online" ? "ONLINE" : status === "checking" ? "..." : "OFFLINE"}
      </span>
    </section>
  );
}