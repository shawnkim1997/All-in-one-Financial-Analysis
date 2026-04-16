"use client";

import { ResearchGridLayout } from "../components/research/ResearchGridLayout";
import type { ResearchDashboardPayload } from "../components/research/types";
import { ErrorBanner } from "../components/ui/ErrorBanner";
import { LoadingPulse } from "../components/ui/LoadingPulse";
import { SectionHeading } from "../components/ui/SectionHeading";
import { useApi } from "../lib/use-api";
import { useTicker } from "../lib/use-ticker";

interface OverviewResp {
  asset_type?: string;
}

export default function ResearchPage() {
  const { ticker, initialized } = useTicker();

  const overviewUrl = initialized ? `/api/market/overview/${ticker}` : null;
  const dashUrl = initialized ? `/api/research/dashboard/${encodeURIComponent(ticker)}` : null;

  const overview = useApi<OverviewResp>(overviewUrl);
  const dashboard = useApi<ResearchDashboardPayload>(dashUrl);

  const assetType = overview.data?.asset_type || "equity";
  const loading = overview.loading || dashboard.loading;

  if (!initialized || loading) {
    return <LoadingPulse label="Loading research…" />;
  }

  return (
    <div className="atlas-page">
      <SectionHeading level={1}>{ticker} Research</SectionHeading>

      {assetType === "equity" ? (
        dashboard.error ? (
          <ErrorBanner
            variant="info"
            message={`${dashboard.error} Some quant widgets may be unavailable — try refreshing or checking the backend.`}
          />
        ) : dashboard.data ? (
          <>
            {dashboard.data.error && (
              <ErrorBanner
                className="mb-4"
                variant="info"
                message={`${dashboard.data.error} — Some widgets may be empty.`}
              />
            )}
            <ResearchGridLayout dashboard={dashboard.data} />
          </>
        ) : (
          <div className="atlas-card p-5 text-sm text-text-muted">
            No dashboard data available. Check the API response or try a different ticker.
          </div>
        )
      ) : assetType === "etf" ? (
        <div className="atlas-card p-5 mb-6">
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-text-secondary">ETF Research</h3>
          <div className="text-text-secondary text-sm">
            Provides Holdings Analysis, Sector Breakdown, and Overlap Analysis. Piotroski F-Score and corporate financial dashboards are not applicable to ETFs.
          </div>
        </div>
      ) : (
        <div className="atlas-card p-5 mb-6">
          <h3 className="text-sm font-semibold uppercase tracking-[0.12em] text-text-secondary">Commodity Research</h3>
          <div className="text-text-secondary text-sm">
            Focuses on Seasonal Analysis and Supply/Demand factors. Equity-specific indicators are not displayed.
          </div>
        </div>
      )}
    </div>
  );
}
