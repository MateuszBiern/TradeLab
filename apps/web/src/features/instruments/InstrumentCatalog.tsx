import { useEffect, useState } from "react";
import type { FormEvent } from "react";

type CatalogInstrument = {
  id: string;
  asset_class: "stock" | "etf";
  venue_code: string;
  symbol: string;
  quote_code: string | null;
  name: string;
  country_code: string | null;
  last_price: number | null;
  last_price_date: string | null;
};

type SearchInstrument = {
  symbol: string;
  name: string;
  exchange: string;
  mic_code: string;
  country: string;
  currency: string;
  instrument_type: string;
  isin?: string | null;
};

type PriceBar = {
  bar_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
  quote_code: string | null;
};

const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const numberFormat = new Intl.NumberFormat("pl-PL", { maximumFractionDigits: 4 });

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl + path, init);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail ?? "Błąd API: " + response.status);
  return payload as T;
}

export function InstrumentCatalog() {
  const [items, setItems] = useState<CatalogInstrument[]>([]);
  const [assetClass, setAssetClass] = useState("stock");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchInstrument[]>([]);
  const [prices, setPrices] = useState<Record<string, PriceBar[]>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  async function loadCatalog() {
    const response = await request<{ items: CatalogInstrument[] }>(
      "/api/v1/instruments?asset_class=" + assetClass + "&limit=200",
    );
    setItems(response.items);
  }

  useEffect(() => {
    void loadCatalog().catch((error: Error) => setMessage(error.message));
  }, [assetClass]);

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setMessage("");
    try {
      const response = await request<{ items: SearchInstrument[] }>(
        "/api/v1/instruments/search?q=" + encodeURIComponent(query.trim()) + "&limit=20",
      );
      setResults(response.items);
      if (!response.items.length) setMessage("Nie znaleziono pasujących instrumentów.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nie udało się wyszukać instrumentów.");
    } finally {
      setLoading(false);
    }
  }

  async function addInstrument(instrument: SearchInstrument) {
    setLoading(true);
    setMessage("");
    try {
      await request("/api/v1/instruments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(instrument),
      });
      await loadCatalog();
      setMessage(instrument.name + " dodano do katalogu.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nie udało się dodać instrumentu.");
    } finally {
      setLoading(false);
    }
  }

  async function refreshPrices(instrument: CatalogInstrument) {
    setLoading(true);
    setMessage("");
    try {
      const response = await request<{ items: PriceBar[]; updated_count: number }>(
        "/api/v1/instruments/" + instrument.id + "/prices/refresh?interval=1day&limit=100",
        { method: "POST" },
      );
      setPrices((current) => ({ ...current, [instrument.id]: response.items }));
      await loadCatalog();
      setMessage("Zapisano " + response.updated_count + " dziennych punktów dla " + instrument.symbol + ".");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Nie udało się pobrać cen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="global-section instrument-section">
      <div className="section-title">
        <div>
          <p className="card-label">KATALOG RYNKU</p>
          <h2>Spółki, ETF-y i ceny historyczne</h2>
          <p className="card-copy">
            Katalog startowy obejmuje duże rynki, w tym GPW. Wyszukaj i dodaj kolejne instrumenty.
            Ceny są pobierane ręcznie na żądanie i służą do researchu.
          </p>
        </div>
        <select aria-label="Typ instrumentu" value={assetClass} onChange={(event) => setAssetClass(event.target.value)}>
          <option value="stock">Akcje</option>
          <option value="etf">ETF-y</option>
          <option value="all">Wszystkie</option>
        </select>
      </div>

      <form className="instrument-search" onSubmit={search}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Nazwa firmy lub ticker, np. NVIDIA, PKO, Toyota"
          aria-label="Wyszukaj spółkę lub ticker"
        />
        <button type="submit" disabled={loading || !query.trim()}>{loading ? "Proszę czekać…" : "Szukaj na rynkach"}</button>
      </form>
      {message && <p className="instrument-message" role="status">{message}</p>}

      {results.length > 0 && <div className="instrument-search-results">
        {results.map((result) => <article className="instrument-result" key={result.mic_code + ":" + result.symbol}>
          <div><strong>{result.name}</strong><span>{result.symbol} · {result.exchange} ({result.mic_code}) · {result.currency}</span></div>
          <button type="button" disabled={loading} onClick={() => void addInstrument(result)}>Dodaj</button>
        </article>)}
      </div>}

      <div className="instrument-table" role="table" aria-label="Katalog instrumentów">
        <div className="instrument-row instrument-head" role="row">
          <span>Instrument</span><span>Rynek</span><span>Ostatnia cena dzienna</span><span></span>
        </div>
        {items.map((instrument) => <div className="instrument-row" role="row" key={instrument.id}>
          <span><strong>{instrument.name}</strong><small>{instrument.symbol} · {instrument.country_code ?? "—"}</small></span>
          <span>{instrument.venue_code}</span>
          <span>{instrument.last_price == null ? "Brak pobranych danych" : numberFormat.format(instrument.last_price) + " " + (instrument.quote_code ?? "") + " · " + instrument.last_price_date}</span>
          <button type="button" disabled={loading} onClick={() => void refreshPrices(instrument)}>Pobierz dzienne ceny</button>
          {prices[instrument.id] && <div className="instrument-history">
            {prices[instrument.id].slice(0, 5).map((bar) => <span key={bar.bar_date}>
              {bar.bar_date}: {numberFormat.format(bar.close)} {bar.quote_code ?? ""}
            </span>)}
          </div>}
        </div>)}
      </div>
      <p className="instrument-footnote">
        Dane giełdowe mogą być opóźnione i zależą od uprawnień planu dostawcy. Przed ręczną decyzją sprawdź cenę i dostępność w swoim brokerze.
      </p>
    </section>
  );
}
