"use client";

interface EquityOverviewProps {
  ticker: string;
  sector: Record<string, unknown> | null;
  health: Record<string, unknown> | null;
}

export function EquityOverview({ ticker, sector, health }: EquityOverviewProps) {
  const metrics = [
    { label: "Sector", value: sector?.sector || "—" },
    { label: "Industry", value: sector?.industry || "—" },
    { label: "Market Cap", value: sector?.market_cap ? `$${(Number(sector.market_cap) / 1e9).toFixed(1)}B` : "—" },
    { label: "P/E Ratio", value: sector?.pe_ratio != null ? Number(sector.pe_ratio).toFixed(1) : "—" },
    { label: "Beta", value: sector?.beta != null ? Number(sector.beta).toFixed(2) : "—" },
    { label: "Div Yield", value: sector?.dividend_yield != null ? `${Number(sector.dividend_yield).toFixed(2)}%` : "—" },
    { label: "52W High", value: sector?.fifty_two_week_high != null ? `$${Number(sector.fifty_two_week_high).toFixed(2)}` : "—" },
    { label: "52W Low", value: sector?.fifty_two_week_low != null ? `$${Number(sector.fifty_two_week_low).toFixed(2)}` : "—" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">
        <span className="text-accent-green">{ticker}</span> Overview
      </h1>
      {sector?.current_price != null && (
        <p className="text-3xl font-mono font-bold text-text-primary mb-6">${Number(sector.current_price).toFixed(2)}</p>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {metrics.map((m) => (
          <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">{m.label}</div>
            <div className="text-text-primary font-semibold">{m.value}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
        <Card title="Altman Z-Score" value={health?.altman_z != null ? Number(health.altman_z).toFixed(2) : "—"} />
        <Card title="Current Ratio" value={health?.current_ratio != null ? Number(health.current_ratio).toFixed(2) : "—"} />
        <Card title="Interest Cov." value={health?.interest_coverage != null ? `${Number(health.interest_coverage).toFixed(1)}x` : "—"} />
        <Card title="D/E Ratio" value={health?.debt_to_equity != null ? Number(health.debt_to_equity).toFixed(2) : "—"} />
      </div>
      <div className="bg-bg-card border border-border rounded-lg p-5">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">DuPont Analysis</h3>
        {!!health?.dupont ? (
          <div className="space-y-2">
            {[
              { label: "ROE", value: health.dupont.roe },
              { label: "Net Profit Margin", value: health.dupont.npm },
              { label: "Asset Turnover", value: health.dupont.asset_turnover },
              { label: "Equity Multiplier", value: health.dupont.equity_multiplier },
            ].map((d) => (
              <div key={d.label} className="flex justify-between">
                <span className="text-text-muted text-sm">{d.label}</span>
                <span className="text-text-primary font-mono">{d.value != null ? Number(d.value).toFixed(2) : "—"}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-text-muted">No data</div>
        )}
      </div>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-bg-card border border-border rounded-lg p-5">
      <h3 className="text-text-secondary text-sm font-semibold mb-3">{title}</h3>
      <div className="text-3xl font-mono font-bold text-text-primary">{value}</div>
    </div>
  );
}
