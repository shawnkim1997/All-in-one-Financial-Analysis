"use client";

import type { FScoreCriterionSeries } from "./types";

function BinarySparkline({ history }: { history: { year: number; pass_flag: boolean }[] }) {
  const w = 80;
  const h = 20;
  const n = history.length;
  if (n === 0) {
    return <div className="w-20 h-5 rounded bg-bg-primary/50 border border-border shrink-0" title="No history" />;
  }
  const step = n > 1 ? (w - 8) / (n - 1) : 0;
  const pts = history.map((pt, i) => {
    const x = n > 1 ? 4 + i * step : w / 2;
    const y = pt.pass_flag ? 5 : 15;
    return { x, y, pt };
  });
  const lineD = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-20 h-5 shrink-0" aria-hidden>
      <path d={lineD} fill="none" stroke="#6B7280" strokeWidth="1.2" strokeLinecap="round" />
      {pts.map((p) => (
        <circle
          key={p.pt.year}
          cx={p.x}
          cy={p.y}
          r={3}
          fill={p.pt.pass_flag ? "#00D4AA" : "#F87171"}
        />
      ))}
    </svg>
  );
}

export function FScorePanel({
  total,
  criteria,
}: {
  total: number;
  criteria: FScoreCriterionSeries[];
}) {
  const color = total >= 7 ? "text-accent-green" : total >= 4 ? "text-accent-yellow" : "text-accent-red";

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex items-baseline gap-3 mb-3">
        <span className={`text-4xl font-mono font-bold ${color}`}>{total}</span>
        <span className="text-text-muted text-sm font-mono">/ 9</span>
        <span className="text-text-muted text-xs">
          {total >= 7 ? "Strong" : total >= 4 ? "Moderate" : "Weak"}
        </span>
      </div>
      <p className="text-text-muted text-xs mb-2">Up to 3 fiscal years per criterion (Piotroski-style).</p>
      <div className="space-y-1.5 overflow-y-auto flex-1 pr-1">
        {criteria.map((c) => (
          <div key={c.key} className="flex items-center justify-between gap-2 text-sm">
            <span className="text-text-muted truncate flex-1 min-w-0" title={c.label}>
              {c.label}
            </span>
            <BinarySparkline history={c.history} />
          </div>
        ))}
      </div>
    </div>
  );
}
