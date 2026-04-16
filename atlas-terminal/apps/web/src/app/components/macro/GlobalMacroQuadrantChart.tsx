"use client";

import {
  CartesianGrid,
  Cell,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { chartPalette } from "../../lib/chart-theme";

export interface QuadrantPoint {
  id: string;
  label: string;
  growth_z: number;
  inflation_z: number;
  growth_momentum?: number | null;
  inflation_momentum?: number | null;
  quadrant: string;
}

const FLAG: Record<string, string> = {
  US: "🇺🇸",
  EU: "🇪🇺",
  JP: "🇯🇵",
  CN: "🇨🇳",
  KR: "🇰🇷",
};

const QUADRANT_COLOR: Record<string, string> = {
  Reflation: chartPalette.gold,
  Recovery: chartPalette.green,
  Stagflation: chartPalette.red,
  Overheat: chartPalette.blue,
};

function QuadrantTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: QuadrantPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  const flag = FLAG[p.id] ?? "▪";
  return (
    <div className="bg-bg-card border border-border rounded-md px-3 py-2 text-xs font-mono shadow-lg">
      <div className="text-text-primary font-semibold mb-1">
        {flag} {p.label}
      </div>
      <div className="text-text-muted">Quadrant: {p.quadrant}</div>
      <div className="text-brand-navy">Growth Z: {p.growth_z?.toFixed(2)}</div>
      <div className="text-brand-blue">Inflation Z: {p.inflation_z?.toFixed(2)}</div>
    </div>
  );
}

export function GlobalMacroQuadrantChart({ points }: { points: QuadrantPoint[] }) {
  if (!points.length) {
    return (
      <div className="h-[320px] flex items-center justify-center text-text-muted text-sm font-mono">
        No quadrant data.
      </div>
    );
  }

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 16, bottom: 8, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
          <XAxis
            type="number"
            dataKey="growth_z"
            name="Growth Z"
            stroke={chartPalette.textMuted}
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            label={{ value: "Growth momentum (Z)", position: "bottom", fill: chartPalette.textMuted, fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="inflation_z"
            name="Inflation Z"
            stroke={chartPalette.textMuted}
            tick={{ fill: chartPalette.textMuted, fontSize: 11 }}
            label={{ value: "Inflation momentum (Z)", angle: -90, position: "insideLeft", fill: chartPalette.textMuted, fontSize: 11 }}
          />
          <ReferenceLine x={0} stroke={chartPalette.neutral} strokeDasharray="4 4" />
          <ReferenceLine y={0} stroke={chartPalette.neutral} strokeDasharray="4 4" />
          <Tooltip content={<QuadrantTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={points} fill={chartPalette.green} name="Country">
            {points.map((entry) => (
              <Cell key={entry.id} fill={QUADRANT_COLOR[entry.quadrant] ?? chartPalette.green} />
            ))}
            <LabelList dataKey="id" position="top" fill={chartPalette.text} fontSize={11} fontFamily="monospace" />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
