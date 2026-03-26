"use client";

import { useState, useEffect } from "react";

interface KoreaIndicator {
  key: string;
  label: string;
  value: number;
  unit: string;
  prev: number | null;
  direction: string | null;
}

interface KoreaData {
  updated_at: string | null;
  indicators: KoreaIndicator[];
  source: string;
  error?: string;
}

function arrow(dir: string | null) {
  if (dir === "up") return <span className="text-accent-green">&uarr;</span>;
  if (dir === "down") return <span className="text-accent-red">&darr;</span>;
  if (dir === "flat") return <span className="text-text-muted">&rarr;</span>;
  return null;
}

export function KoreaMonitor() {
  const [data, setData] = useState<KoreaData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiKey = typeof window !== "undefined" ? localStorage.getItem("atlas_ecos_key") || "" : "";
    const params = apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : "";

    fetch(`/api/macro/korea${params}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-8 text-center">
        <div className="text-accent-green animate-pulse font-mono">Loading Korea data...</div>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Korea Economic Monitor</h3>
        <div className="text-text-muted text-sm">{data?.error || "Set an ECOS API key in Settings for full Korean data."}</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <div className="flex items-end justify-between mb-3">
          <div>
            <h3 className="text-text-secondary text-sm font-semibold">Korea Economic Monitor</h3>
            <div className="text-text-muted text-xs mt-1">
              Source: {data.source === "ecos" ? "\ud55c\uad6d\uc740\ud589 ECOS API" : "yfinance (limited)"}
            </div>
          </div>
          {data.source !== "ecos" && (
            <div className="text-accent-yellow text-xs">
              Add ECOS API key in Settings for full data
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {data.indicators.map((ind) => (
            <div key={ind.key} className="bg-bg-primary border border-border rounded-md p-3">
              <div className="text-text-muted text-xs">{ind.label}</div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-text-primary font-mono font-bold text-xl">
                  {ind.value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
                <span className="text-text-muted text-xs">{ind.unit}</span>
                {arrow(ind.direction)}
              </div>
              {ind.prev != null && (
                <div className="text-text-muted text-[10px] font-mono mt-1">
                  prev {ind.prev.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
