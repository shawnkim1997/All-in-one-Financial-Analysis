"use client";

import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartPalette } from "../../lib/chart-theme";

export interface YieldFxRow {
  date: string;
  spread_pct: number;
  fx: number;
}

const PAIR_LABEL: Record<string, { title: string; fx: string }> = {
  usdjpy: { title: "US 10Y − JP 10Y vs USD/JPY", fx: "USD/JPY" },
  eurusd: { title: "US 10Y − EZ 10Y vs EUR/USD", fx: "EUR/USD" },
  usdkrw: { title: "US 10Y − KR 10Y vs USD/KRW", fx: "USD/KRW" },
};

export function YieldFxDualAxisChart({
  pair,
  rows,
}: {
  pair: string;
  rows: YieldFxRow[];
}) {
  const meta = PAIR_LABEL[pair] ?? { title: "Yield spread vs FX", fx: "FX" };

  if (!rows.length) {
    return (
      <div className="h-[280px] flex items-center justify-center text-text-muted text-sm font-mono">
        No yield/FX series.
      </div>
    );
  }

  return (
    <div className="h-[300px] w-full">
      <p className="text-text-muted text-xs font-mono mb-2">{meta.title}</p>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
          <XAxis dataKey="date" tick={{ fill: chartPalette.textMuted, fontSize: 10 }} minTickGap={24} />
          <YAxis
            yAxisId="left"
            tick={{ fill: chartPalette.navy, fontSize: 10 }}
            domain={["auto", "auto"]}
            label={{ value: "Spread (ppt)", angle: -90, position: "insideLeft", fill: chartPalette.navy, fontSize: 10 }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fill: chartPalette.blue, fontSize: 10 }}
            domain={["auto", "auto"]}
            label={{ value: meta.fx, angle: 90, position: "insideRight", fill: chartPalette.blue, fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ background: chartPalette.canvas, border: `1px solid ${chartPalette.grid}`, fontSize: 12 }}
            labelStyle={{ color: chartPalette.text }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="spread_pct"
            name="US10Y − peer (ppt)"
            stroke={chartPalette.navy}
            dot={false}
            strokeWidth={2}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="fx"
            name={meta.fx}
            stroke={chartPalette.blue}
            dot={false}
            strokeWidth={2}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
