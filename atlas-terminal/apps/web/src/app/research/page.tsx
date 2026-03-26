"use client";

import { useEffect, useState } from "react";
import { ResearchGridLayout } from "../components/research/ResearchGridLayout";
import type { ResearchDashboardPayload } from "../components/research/types";
import { useTicker } from "../lib/use-ticker";

export default function ResearchPage() {
  const { ticker } = useTicker();
  const [assetType, setAssetType] = useState<string>("equity");
  const [dashboard, setDashboard] = useState<ResearchDashboardPayload | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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
        setLoadError("대시보드 데이터를 불러오지 못했습니다.");
        setDashboard(null);
      })
      .finally(() => setLoading(false));
  }, [ticker]);

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
                {dashboard.error} — 일부 위젯이 비어 있을 수 있습니다.
              </div>
            )}
            <ResearchGridLayout dashboard={dashboard} />
          </>
        ) : (
          <div className="bg-bg-card border border-border rounded-lg p-5 text-text-muted text-sm">
            대시보드 데이터가 없습니다. API 응답을 확인하거나 티커를 바꿔 보세요.
          </div>
        )
      ) : assetType === "etf" ? (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">ETF Research</h3>
          <div className="text-text-secondary text-sm">
            Holdings Analysis, Sector Breakdown, Overlap Analysis를 우선 제공합니다. Piotroski/F-Score 및 기업 재무
            대시보드는 ETF에 적용되지 않습니다.
          </div>
        </div>
      ) : (
        <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Commodity Research</h3>
          <div className="text-text-secondary text-sm">
            Seasonal Analysis와 Supply/Demand 요인을 중심으로 분석합니다. 주식 전용 지표는 표시하지 않습니다.
          </div>
        </div>
      )}
    </div>
  );
}
