"use client";
import { useEffect, useState } from "react";
import { useTicker } from "./lib/use-ticker";

interface HealthData {
  dupont?: { roe?: number; npm?: number; asset_turnover?: number; equity_multiplier?: number };
  altman_z?: number;
  red_flags?: string[];
}

interface SectorData {
  sector?: string;
  industry?: string;
  market_cap?: number;
  pe_ratio?: number;
  dividend_yield?: number;
  beta?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  current_price?: number;
}

export default function OverviewPage() {
  const { ticker } = useTicker();
  const [sector, setSector] = useState<SectorData | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/market/sector/${ticker}`).then((r) => r.ok ? r.json() : null),
      fetch(`/api/market/health/${ticker}`).then((r) => r.ok ? r.json() : null),
    ]).then(([s, h]) => {
      setSector(s);
      setHealth(h);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [ticker]);

  if (loading) return <LoadingState />;

  const metrics = [
    { label: "Sector", value: sector?.sector || "—" },
    { label: "Industry", value: sector?.industry || "—" },
    { label: "Market Cap", value: sector?.market_cap ? `$${(sector.market_cap / 1e9).toFixed(1)}B` : "—" },
    { label: "P/E Ratio", value: sector?.pe_ratio?.toFixed(1) || "—" },
    { label: "Beta", value: sector?.beta?.toFixed(2) || "—" },
    { label: "Div Yield", value: sector?.dividend_yield ? `${sector.dividend_yield.toFixed(2)}%` : "—" },
    { label: "52W High", value: sector?.fifty_two_week_high ? `$${sector.fifty_two_week_high.toFixed(2)}` : "—" },
    { label: "52W Low", value: sector?.fifty_two_week_low ? `$${sector.fifty_two_week_low.toFixed(2)}` : "—" },
  ];

  const zScore = health?.altman_z;
  const zColor = zScore && zScore > 2.99 ? "text-accent-green" : zScore && zScore > 1.81 ? "text-accent-yellow" : "text-accent-red";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">
        <span className="text-accent-green">{ticker}</span> Overview
      </h1>
      {sector?.current_price && (
        <p className="text-3xl font-mono font-bold text-text-primary mb-6">
          ${sector.current_price.toFixed(2)}
        </p>
      )}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {metrics.map((m) => (
          <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">{m.label}</div>
            <div className="text-text-primary font-semibold">{m.value}</div>
          </div>
        ))}
      </div>

      {/* Health Section */}
      <div className="grid grid-cols-2 gap-4">
        {/* Altman Z-Score */}
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Altman Z-Score</h3>
          <div className={`text-4xl font-mono font-bold ${zColor}`}>
            {zScore?.toFixed(2) || "—"}
          </div>
          <div className="text-text-muted text-xs mt-2">
            {zScore && zScore > 2.99 ? "Safe Zone" : zScore && zScore > 1.81 ? "Grey Zone" : "Distress Zone"}
          </div>
        </div>

        {/* DuPont Analysis */}
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">DuPont Analysis</h3>
          {health?.dupont ? (
            <div className="space-y-2">
              {[
                { label: "ROE", value: health.dupont.roe },
                { label: "Net Profit Margin", value: health.dupont.npm },
                { label: "Asset Turnover", value: health.dupont.asset_turnover },
                { label: "Equity Multiplier", value: health.dupont.equity_multiplier },
              ].map((d) => (
                <div key={d.label} className="flex justify-between items-center">
                  <span className="text-text-muted text-sm">{d.label}</span>
                  <span className="text-text-primary font-mono font-semibold">
                    {d.value?.toFixed(2) || "—"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-text-muted">No data</div>
          )}
        </div>
      </div>

      {/* Red Flags */}
      {health?.red_flags && health.red_flags.length > 0 && (
        <div className="mt-4 bg-bg-card border border-accent-red/30 rounded-lg p-5">
          <h3 className="text-accent-red text-sm font-semibold mb-3">Red Flags</h3>
          <ul className="space-y-1.5">
            {health.red_flags.map((f, i) => (
              <li key={i} className="text-text-secondary text-sm flex items-start gap-2">
                <span className="text-accent-red mt-0.5">•</span> {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-accent-green animate-pulse font-mono">Loading data...</div>
    </div>
  );
}
