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
  Reflation: "#FFD93D",
  Recovery: "#00D4AA",
  Stagflation: "#FF4757",
  Overheat: "#4DA6FF",
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
      <div className="text-accent-green">Growth Z: {p.growth_z?.toFixed(2)}</div>
      <div className="text-accent-blue">Inflation Z: {p.inflation_z?.toFixed(2)}</div>
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
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A3A" />
          <XAxis
            type="number"
            dataKey="growth_z"
            name="Growth Z"
            stroke="#6B7280"
            tick={{ fill: "#9CA3AF", fontSize: 11 }}
            label={{ value: "Growth momentum (Z)", position: "bottom", fill: "#6B7280", fontSize: 11 }}
          />
          <YAxis
            type="number"
            dataKey="inflation_z"
            name="Inflation Z"
            stroke="#6B7280"
            tick={{ fill: "#9CA3AF", fontSize: 11 }}
            label={{ value: "Inflation momentum (Z)", angle: -90, position: "insideLeft", fill: "#6B7280", fontSize: 11 }}
          />
          <ReferenceLine x={0} stroke="#4B5563" strokeDasharray="4 4" />
          <ReferenceLine y={0} stroke="#4B5563" strokeDasharray="4 4" />
          <Tooltip content={<QuadrantTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={points} fill="#00D4AA" name="Country">
            {points.map((entry) => (
              <Cell key={entry.id} fill={QUADRANT_COLOR[entry.quadrant] ?? "#00D4AA"} />
            ))}
            <LabelList dataKey="id" position="top" fill="#E5E7EB" fontSize={11} fontFamily="monospace" />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
