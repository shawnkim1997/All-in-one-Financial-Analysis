"use client";

import { useState, useMemo } from "react";

interface OECDCountry {
  country: string;
  iso: string;
  cli_current: number | null;
  cli_prev: number | null;
  direction: string;
  bci: number | null;
  cci: number | null;
  series: { date: string; value: number }[];
}

export interface OECDData {
  updated_at: string | null;
  countries: OECDCountry[];
  error?: string;
}

const COLORS = [
  "#00d4aa", "#ff4757", "#ffa502", "#3742fa", "#a29bfe",
  "#fd79a8", "#00cec9", "#e17055", "#6c5ce7", "#fdcb6e",
];

function directionBadge(d: string) {
  const map: Record<string, { label: string; cls: string }> = {
    expanding: { label: "Expanding", cls: "bg-accent-green/25 text-accent-green" },
    recovering: { label: "Recovering", cls: "bg-accent-yellow/15 text-accent-yellow" },
    slowing: { label: "Slowing", cls: "bg-accent-yellow/15 text-accent-yellow" },
    contracting: { label: "Contracting", cls: "bg-accent-red/25 text-accent-red" },
  };
  const info = map[d] || { label: d, cls: "bg-bg-primary text-text-muted" };
  return <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${info.cls}`}>{info.label}</span>;
}

export function OECDCycleChart({ data }: { data: OECDData | null }) {
  const [selected, setSelected] = useState<Set<string>>(new Set(["USA", "EA", "JPN", "KOR", "CHN"]));

  const visibleCountries = useMemo(() => {
    if (!data) return [];
    return data.countries.filter((c) => selected.has(c.iso));
  }, [data, selected]);

  if (!data || data.error) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">OECD Leading Indicators</h3>
        <div className="text-text-muted text-sm">{data?.error || "Loading OECD data..."}</div>
      </div>
    );
  }

  const allDates: string[] = [];
  const dateSet = new Set<string>();
  for (const c of visibleCountries) {
    for (const pt of c.series) {
      if (!dateSet.has(pt.date)) {
        dateSet.add(pt.date);
        allDates.push(pt.date);
      }
    }
  }
  allDates.sort();

  let minVal = 95, maxVal = 105;
  for (const c of visibleCountries) {
    for (const pt of c.series) {
      if (pt.value < minVal) minVal = pt.value;
      if (pt.value > maxVal) maxVal = pt.value;
    }
  }
  const padding = (maxVal - minVal) * 0.1 || 1;
  minVal -= padding;
  maxVal += padding;

  const W = 800, H = 280, PL = 50, PR = 20, PT = 10, PB = 30;
  const chartW = W - PL - PR;
  const chartH = H - PT - PB;

  function x(idx: number) { return PL + (allDates.length > 1 ? (idx / (allDates.length - 1)) * chartW : chartW / 2); }
  function y(val: number) { return PT + chartH - ((val - minVal) / (maxVal - minVal)) * chartH; }

  const baseline100Y = y(100);

  function toggle(iso: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(iso)) next.delete(iso);
      else next.add(iso);
      return next;
    });
  }

  return (
    <div className="bg-bg-card border border-border rounded-lg p-4">
      <div className="flex items-end justify-between mb-3">
        <div>
          <h3 className="text-text-secondary text-sm font-semibold">OECD Leading Indicators (CLI)</h3>
          <div className="text-text-muted text-xs mt-1">100 baseline = long-term trend. Above 100 = expansion phase.</div>
        </div>
      </div>

      {/* Country Toggle */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {data.countries.map((c, i) => (
          <button
            key={c.iso}
            onClick={() => toggle(c.iso)}
            className={`text-[11px] px-2 py-1 rounded font-medium border transition-colors ${
              selected.has(c.iso)
                ? "border-transparent text-bg-primary"
                : "border-border text-text-muted hover:text-text-secondary"
            }`}
            style={selected.has(c.iso) ? { backgroundColor: COLORS[i % COLORS.length] } : {}}
          >
            {c.iso}
          </button>
        ))}
      </div>

      {/* SVG Chart */}
      {allDates.length > 1 ? (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[minVal, 100, maxVal].map((v) => (
            <line key={v} x1={PL} x2={W - PR} y1={y(v)} y2={y(v)} stroke="currentColor" strokeOpacity={0.1} />
          ))}
          {/* 100 baseline */}
          <line x1={PL} x2={W - PR} y1={baseline100Y} y2={baseline100Y}
            stroke="#00d4aa" strokeOpacity={0.3} strokeDasharray="4 2" />
          <text x={PL - 4} y={baseline100Y + 4} textAnchor="end" fill="#00d4aa" fontSize="10" opacity={0.6}>100</text>

          {/* Lines */}
          {visibleCountries.map((c) => {
            const colorIdx = data.countries.findIndex((dc) => dc.iso === c.iso);
            const color = COLORS[colorIdx % COLORS.length];
            const dateMap = new Map(c.series.map((pt) => [pt.date, pt.value]));
            const points = allDates
              .map((d, i) => ({ x: x(i), y: dateMap.has(d) ? y(dateMap.get(d)!) : null }))
              .filter((p) => p.y !== null) as { x: number; y: number }[];
            if (points.length < 2) return null;
            const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
            return <path key={c.iso} d={d} fill="none" stroke={color} strokeWidth={1.8} />;
          })}

          {/* X-axis labels */}
          {allDates.filter((_, i) => i % Math.max(1, Math.floor(allDates.length / 6)) === 0).map((d) => {
            const idx = allDates.indexOf(d);
            return (
              <text key={d} x={x(idx)} y={H - 5} textAnchor="middle" fill="currentColor" fontSize="9" opacity={0.5}>
                {d}
              </text>
            );
          })}
        </svg>
      ) : (
        <div className="h-40 flex items-center justify-center text-text-muted text-sm">No chart data available</div>
      )}

      {/* Country Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-2 mt-3">
        {data.countries.filter((c) => selected.has(c.iso)).map((c) => (
          <div key={c.iso} className="bg-bg-primary border border-border rounded-md p-2.5">
            <div className="flex items-center justify-between">
              <span className="text-text-primary text-xs font-semibold">{c.iso}</span>
              {directionBadge(c.direction)}
            </div>
            <div className="text-text-primary font-mono font-bold text-lg mt-1">
              {c.cli_current?.toFixed(2) ?? "—"}
            </div>
            {c.cli_prev != null && (
              <div className={`text-[10px] font-mono ${(c.cli_current ?? 0) >= c.cli_prev ? "text-accent-green" : "text-accent-red"}`}>
                prev {c.cli_prev.toFixed(2)}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
