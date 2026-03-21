"use client";

interface ETFOverviewProps {
  ticker: string;
  data: Record<string, unknown>;
}

export function ETFOverview({ ticker, data }: ETFOverviewProps) {
  const returns = data?.returns || {};
  const risk = data?.risk || {};
  const holdings = Array.isArray(data?.holdings) ? data.holdings : [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">
        <span className="text-accent-green">{ticker}</span> ETF Overview
      </h1>
      <div className="bg-bg-card border border-border rounded-lg p-5">
        <div className="text-text-primary font-semibold text-lg">{data?.name || ticker}</div>
        <div className="text-3xl font-mono font-bold text-text-primary mt-1">
          {data?.price != null ? `$${Number(data.price).toFixed(2)}` : "—"}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Category", value: data?.category || "N/A" },
          { label: "AUM", value: data?.aum ? `$${(Number(data.aum) / 1e9).toFixed(1)}B` : "—" },
          { label: "Expense Ratio", value: data?.expense_ratio != null ? `${(Number(data.expense_ratio) * 100).toFixed(2)}%` : "—" },
          { label: "NAV", value: data?.nav != null ? `$${Number(data.nav).toFixed(2)}` : "—" },
          { label: "52W High", value: data?.high_52w != null ? `$${Number(data.high_52w).toFixed(2)}` : "—" },
          { label: "52W Low", value: data?.low_52w != null ? `$${Number(data.low_52w).toFixed(2)}` : "—" },
          { label: "1Y Return", value: returns?.["1y"] != null ? `${returns["1y"]}%` : "—" },
          { label: "YTD Return", value: returns?.ytd != null ? `${returns.ytd}%` : "—" },
        ].map((m) => (
          <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs">{m.label}</div>
            <div className="text-text-primary font-mono font-semibold mt-1">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-bg-card border border-border rounded-lg p-5">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Performance</h3>
        <div className="flex flex-wrap gap-2 text-sm">
          {["1m", "3m", "6m", "ytd", "1y", "3y", "5y"].map((k) => (
            <span key={k} className="bg-bg-primary border border-border rounded px-2 py-1 font-mono text-text-primary">
              {k.toUpperCase()}: {returns?.[k] != null ? `${returns[k]}%` : "—"}
            </span>
          ))}
        </div>
      </div>

      {holdings.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Top Holdings</h3>
          <div className="space-y-2">
            {holdings.slice(0, 10).map((h: Record<string, unknown>, i: number) => (
              <div key={`${h.symbol || h.name}-${i}`} className="flex justify-between text-sm">
                <span className="text-text-primary">{h.symbol || h.name || "—"}</span>
                <span className="text-text-muted font-mono">
                  {h.weight_pct != null ? `${(Number(h.weight_pct) * 100).toFixed(2)}%` : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Sharpe", value: risk?.sharpe },
          { label: "Sortino", value: risk?.sortino },
          { label: "Max DD", value: risk?.max_drawdown != null ? `${risk.max_drawdown}%` : null },
          { label: "Volatility", value: risk?.volatility != null ? `${risk.volatility}%` : null },
        ].map((r) => (
          <div key={r.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs">{r.label}</div>
            <div className="text-text-primary font-mono font-semibold mt-1">{r.value ?? "—"}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
