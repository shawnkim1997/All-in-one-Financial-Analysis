"use client";
import { useEffect, useState } from "react";
import { useTicker } from "./lib/use-ticker";
import { EquityOverview } from "./components/overview/EquityOverview";
import { ETFOverview } from "./components/overview/ETFOverview";
import { CommodityOverview } from "./components/overview/CommodityOverview";

export default function OverviewPage() {
  const { ticker, initialized } = useTicker();
  const [sector, setSector] = useState<Record<string, unknown> | null>(null);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [overview, setOverview] = useState<Record<string, unknown> | null>(null);
  const [assetType, setAssetType] = useState<string>("equity");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!initialized) return;
    const ac = new AbortController();
    setLoading(true);
    setSector(null);
    setHealth(null);
    setOverview(null);
    Promise.all([
      fetch(`/api/market/sector/${ticker}`, { signal: ac.signal }).then((r) => r.ok ? r.json() : null),
      fetch(`/api/market/health/${ticker}`, { signal: ac.signal }).then((r) => r.ok ? r.json() : null),
      fetch(`/api/market/overview/${ticker}`, { signal: ac.signal }).then((r) => r.ok ? r.json() : null),
    ]).then(([s, h, d]) => {
      if (ac.signal.aborted) return;
      setSector(s);
      setHealth(h);
      setAssetType(d?.asset_type || "equity");
      setOverview(d?.data || null);
      setLoading(false);
    }).catch(() => { if (!ac.signal.aborted) setLoading(false); });
    return () => ac.abort();
  }, [ticker, initialized]);

  if (loading) return <LoadingState />;

  if (assetType === "etf") {
    return <ETFOverview ticker={ticker} data={overview || {}} />;
  }
  if (assetType === "commodity_future") {
    return <CommodityOverview ticker={ticker} data={overview || {}} />;
  }
  return <EquityOverview ticker={ticker} sector={sector} health={health} />;
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-accent-green animate-pulse font-mono">Loading data...</div>
    </div>
  );
}
