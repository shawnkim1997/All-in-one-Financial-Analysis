"use client";

import { CommodityOverview } from "./components/overview/CommodityOverview";
import { EquityOverview } from "./components/overview/EquityOverview";
import { ETFOverview } from "./components/overview/ETFOverview";
import { ErrorBanner } from "./components/ui/ErrorBanner";
import { LoadingPulse } from "./components/ui/LoadingPulse";
import { SectionHeading } from "./components/ui/SectionHeading";
import { useApi } from "./lib/use-api";
import { useTicker } from "./lib/use-ticker";

interface OverviewResp {
  asset_type?: string;
  data?: Record<string, unknown>;
}

export default function OverviewPage() {
  const { ticker, initialized } = useTicker();

  const sectorUrl = initialized ? `/api/market/sector/${ticker}` : null;
  const healthUrl = initialized ? `/api/market/health/${ticker}` : null;
  const overviewUrl = initialized ? `/api/market/overview/${ticker}` : null;

  const sector = useApi<Record<string, unknown>>(sectorUrl);
  const health = useApi<Record<string, unknown>>(healthUrl);
  const overview = useApi<OverviewResp>(overviewUrl);

  const loading = !initialized || sector.loading || health.loading || overview.loading;
  if (loading) return <LoadingPulse label="Loading data..." />;

  // Surface only truly catastrophic failures as a banner — per-component empty
  // states already handle partial data gracefully.
  const fatalError =
    sector.error && health.error && overview.error
      ? "Unable to reach the backend. Please start the API server or refresh."
      : null;

  if (fatalError) {
    return (
      <div className="atlas-page">
        <SectionHeading level={1}>{ticker} Overview</SectionHeading>
        <ErrorBanner variant="error" message={fatalError} />
      </div>
    );
  }

  const assetType = overview.data?.asset_type || "equity";
  const overviewData = overview.data?.data || {};

  if (assetType === "etf") {
    return <ETFOverview ticker={ticker} data={overviewData} />;
  }
  if (assetType === "commodity_future") {
    return <CommodityOverview ticker={ticker} data={overviewData} />;
  }
  return <EquityOverview ticker={ticker} sector={sector.data} health={health.data} />;
}
