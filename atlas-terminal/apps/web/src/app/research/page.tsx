"use client";

import { useEffect, useState } from "react";
import { ResearchGridLayout } from "../components/research/ResearchGridLayout";
import type { ResearchDashboardPayload } from "../components/research/types";
import { useTicker } from "../lib/use-ticker";

export default function ResearchPage() {
  const { ticker, initialized } = useTicker();
  const [assetType, setAssetType] = useState<string>("equity");
  const [dashboard, setDashboard] = useState<ResearchDashboardPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!initialized) return;
    setLoading(true);
    setLoadError(null);
    Promise.all([
      fetch(`/api/market/overview/${ticker}`).then((r) => (r.ok ? r.json() : { asset_type: "equity" })),
      fetch(`/api/research/dashboard/${encodeURIComponent(ticker)}`).then(async (r) => {
        if (!r.ok) {
          const errText = await r.text();
          throw new Error(errText || `HTTP ${r.status}`);
        }
        return r.json();
      }),
    ])
      .then(([overview, dash]) => {
        setAssetType(overview?.asset_type || "equity");
        setDashboard(dash as ResearchDashboardPayload);
      })
      .catch(() => {
        setLoadError("Failed to load dashboard data.");
        setDashboard(null);
      })
      .finally(() => setLoading(false));
  }, [ticker, initialized]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-accent-green animate-pulse font-mono">Loading research…</div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">
        <span className="text-accent-green">{ticker}</span> Research
      </h1>

      {assetType === "equity" ? (
        loadError ? (
          <div className="bg-bg-card border border-border rounded-lg p-5 text-accent-red text-sm">{loadError}</div>
        ) : dashboard ? (
          <>
            {dashboard.error && (
              <div className="mb-4 rounded-lg border border-accent-yellow/40 bg-bg-card px-4 py-3 text-sm text-accent-yellow">
                {dashboard.error} — Some widgets may be empty.
              </div>
            )}
            <ResearchGridLayout dashboard={dashboard} />
          </>
        ) : (
          <div className="bg-bg-card border border-border rounded-lg p-5 text-text-muted text-sm">
            No dashboard data available. Check the API response or try a different ticker.
          </div>
        )
      ) : assetType === "etf" ? (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">ETF Research</h3>
          <div className="text-text-secondary text-sm">
            Provides Holdings Analysis, Sector Breakdown, and Overlap Analysis. Piotroski F-Score and corporate financial dashboards are not applicable to ETFs.
          </div>
        </div>
      ) : (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Commodity Research</h3>
          <div className="text-text-secondary text-sm">
            Focuses on Seasonal Analysis and Supply/Demand factors. Equity-specific indicators are not displayed.
          </div>
        </div>
      )}
    </div>
  );
}
