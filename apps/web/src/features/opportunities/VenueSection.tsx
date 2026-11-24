import { copy } from "../../app/copy";
import type { Coverage } from "./types";

type Props = { coverage: Coverage | null };

export function VenueSection({ coverage }: Props) {
  const venues = coverage?.market_data_venues ?? [];
  return (
    <section className="global-section venue-section">
      <div className="section-title"><div><p className="card-label">INTEGRATIONS</p><h2>{copy.venueTitle}</h2><p className="card-copy">{copy.venueSubtitle}</p></div></div>
      <div className="venue-grid">
        <article className="venue-card">
          <div className="venue-top"><span className="venue-icon">₿</span><span className="venue-type">CRYPTO · DATA</span></div>
          <h3>{copy.cryptoVenues}</h3><p>{copy.cryptoVenueStatus}</p>
          <div className="venue-tags">{venues.map((venue) => <span key={venue.id}>{venue.name}</span>)}</div>
          <small>{copy.noExecution}</small>
        </article>
        <article className="venue-card">
          <div className="venue-top"><span className="venue-icon">X</span><span className="venue-type">BROKER · MANUAL</span></div>
          <h3>XTB</h3><p>{copy.xtbStatus}</p><small>{copy.xtbApi}</small>
        </article>
      </div>
    </section>
  );
}