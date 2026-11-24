import { useEffect, useState } from "react";
import { copy } from "./copy";
import { StatusCard } from "../components/StatusCard";
import { marketApi } from "../features/market/marketApi";
import type { ApiStatus } from "../features/opportunities/types";
import { GlobalDashboard } from "../features/opportunities/GlobalDashboard";

export default function App() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking");

  useEffect(() => {
    marketApi.getHealth().then(() => setApiStatus("online")).catch(() => setApiStatus("offline"));
  }, []);

  return (
    <main className="shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="TradeLab AI start">
          <span className="brand-mark">T</span>
          <span>TradeLab <strong>AI</strong></span>
        </a>
        <span className="mode"><span className="mode-dot" />{copy.readOnly}</span>
      </header>
      <section className="welcome">
        <p className="eyebrow">{copy.eyebrow}</p>
        <h1>{copy.title}<br /><span>{copy.titleAccent}</span></h1>
        <p className="intro">{copy.subtitle}</p>
      </section>
      <StatusCard status={apiStatus} />
      <GlobalDashboard />
    </main>
  );
}