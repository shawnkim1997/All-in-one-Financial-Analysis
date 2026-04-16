"use client";

import { chartPalette } from "../../lib/chart-theme";

export interface KpiHistoryData {
  ticker: string;
  quarters: string[];
  revenue_growth: Array<number | null>;
  operating_margin: Array<number | null>;
  net_margin: Array<number | null>;
  roe: Array<number | null>;
  fcf: Array<number | null>;
}

function formatMetricValue(key: string, value: number | null): string {
  if (value == null) return "—";
  if (key === "fcf") {
    const abs = Math.abs(value);
    if (abs >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
    return `$${value.toFixed(0)}`;
  }
  return `${value.toFixed(1)}%`;
}

function formatDelta(value: number | null, previous: number | null, key: string): string {
  if (value == null || previous == null) return "—";
  if (key === "fcf") {
    const delta = value - previous;
    const abs = Math.abs(delta);
    if (abs >= 1e9) return `${delta >= 0 ? "+" : ""}$${(delta / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${delta >= 0 ? "+" : ""}$${(delta / 1e6).toFixed(1)}M`;
    return `${delta >= 0 ? "+" : ""}$${delta.toFixed(0)}`;
  }
  const delta = value - previous;
  return `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}pp`;
}

function Sparkline({ values }: { values: Array<number | null> }) {
  const points = values
    .map((value, index) => ({ value, index }))
    .filter((item): item is { value: number; index: number } => item.value != null);

  if (points.length < 2) {
    return <div className="h-16 rounded-md bg-bg-primary/60 border border-border" />;
  }

  const width = 180;
  const height = 64;
  const min = Math.min(...points.map((p) => p.value));
  const max = Math.max(...points.map((p) => p.value));
  const range = max - min || 1;
  const step = width / Math.max(points.length - 1, 1);
  const path = points
    .map((point, idx) => {
      const x = idx * step;
      const y = height - ((point.value - min) / range) * (height - 10) - 5;
      return `${idx === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  const last = points[points.length - 1];
  const lastX = (points.length - 1) * step;
  const lastY = height - ((last.value - min) / range) * (height - 10) - 5;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-16">
      <path d={path} fill="none" stroke={chartPalette.blue} strokeWidth="2" strokeLinecap="round" />
      <circle cx={lastX} cy={lastY} r="3" fill={chartPalette.gold} />
    </svg>
  );
}

export function KpiSection({ data }: { data: KpiHistoryData | null }) {
  if (!data || data.quarters.length === 0) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Key Performance Indicators</h3>
        <div className="text-text-muted text-sm">Quarterly KPI history is not available for this ticker.</div>
      </div>
    );
  }

  const cards = [
    { key: "revenue_growth", label: "Revenue QoQ", values: data.revenue_growth },
    { key: "operating_margin", label: "Operating Margin", values: data.operating_margin },
    { key: "net_margin", label: "Net Margin", values: data.net_margin },
    { key: "roe", label: "ROE", values: data.roe },
    { key: "fcf", label: "Free Cash Flow", values: data.fcf },
  ];

  return (
    <div className="mb-6">
      <h3 className="text-text-secondary text-sm font-semibold mb-3">Key Performance Indicators</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {cards.map((card) => {
          const latest = card.values[card.values.length - 1] ?? null;
          const previous = card.values.length > 1 ? card.values[card.values.length - 2] ?? null : null;
          const delta = latest != null && previous != null ? latest - previous : null;

          return (
            <div key={card.key} className="bg-bg-card border border-border rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-text-muted text-xs">{card.label}</div>
                  <div className="text-text-primary text-2xl font-mono font-bold mt-1">
                    {formatMetricValue(card.key, latest)}
                  </div>
                </div>
                <span
                  className={`text-xs px-2 py-1 rounded font-semibold ${
                    delta == null
                      ? "bg-bg-primary text-text-muted"
                      : delta >= 0
                        ? "bg-accent-green/15 text-accent-green"
                        : "bg-accent-red/15 text-accent-red"
                  }`}
                >
                  {formatDelta(latest, previous, card.key)}
                </span>
              </div>
              <Sparkline values={card.values} />
              <div className="mt-2 text-[11px] text-text-muted font-mono">
                {data.quarters.slice(Math.max(0, data.quarters.length - 4)).join("  ")}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
