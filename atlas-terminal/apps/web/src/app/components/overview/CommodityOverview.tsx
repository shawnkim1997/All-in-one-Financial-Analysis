"use client";

interface CommodityOverviewProps {
  ticker: string;
  data: Record<string, unknown>;
}

export function CommodityOverview({ ticker, data }: CommodityOverviewProps) {
  const seasonal = (data?.seasonal_pattern ?? {}) as Record<string, unknown>;
  const correlations = (data?.correlation_matrix ?? {}) as Record<string, unknown>;
  const related = Array.isArray(data?.related_assets) ? data.related_assets : [];
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">
        <span className="text-accent-green">{ticker}</span> Commodity Overview
      </h1>
      <div className="bg-bg-card border border-border rounded-lg p-5">
        <div className="text-text-primary font-semibold text-lg">{String(data?.name ?? ticker)}</div>
        <div className="text-3xl font-mono font-bold text-text-primary mt-1">
          {data?.price != null ? `$${Number(data.price).toFixed(2)}` : "—"}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Open Interest", value: data?.open_interest?.toLocaleString?.() || "—" },
          { label: "Volume", value: data?.volume?.toLocaleString?.() || "—" },
          { label: "52W High", value: data?.high_52w != null ? `$${Number(data.high_52w).toFixed(2)}` : "—" },
          { label: "52W Low", value: data?.low_52w != null ? `$${Number(data.low_52w).toFixed(2)}` : "—" },
        ].map((m) => (
          <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs">{m.label}</div>
            <div className="text-text-primary font-mono font-semibold mt-1">{m.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-bg-card border border-border rounded-lg p-5">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Seasonal Pattern (10Y avg monthly)</h3>
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 text-xs">
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
            const v = Number(seasonal[String(m)] ?? 0) || 0;
            return (
              <div key={m} className="bg-bg-primary border border-border rounded p-2">
                <div className="text-text-muted">M{m}</div>
                <div className={`font-mono ${v >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {v >= 0 ? "+" : ""}
                  {v}%
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {related.length > 0 && (
        <div className="bg-bg-card border border-border rounded-lg p-5">
          <h3 className="text-text-secondary text-sm font-semibold mb-3">Related Assets</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
            {related.map((r: Record<string, unknown>, idx: number) => (
              <div key={String(r.symbol ?? idx)} className="bg-bg-primary border border-border rounded p-3">
                <div className="text-text-secondary text-xs">{String(r.symbol ?? "")}</div>
                <div className="text-text-primary font-mono">{r.price != null ? `$${Number(r.price).toFixed(2)}` : "—"}</div>
                <div className={`text-xs font-mono ${Number(r.change_pct || 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                  {Number(r.change_pct || 0) >= 0 ? "+" : ""}
                  {Number(r.change_pct ?? 0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-bg-card border border-border rounded-lg p-5">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Correlation Matrix (1Y)</h3>
        <div className="space-y-1 text-sm">
          {Object.keys(correlations).length === 0 && <div className="text-text-muted">No correlation data</div>}
          {Object.entries(correlations).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-text-secondary">{k}</span>
              <span className="text-text-primary font-mono">{String(v)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
