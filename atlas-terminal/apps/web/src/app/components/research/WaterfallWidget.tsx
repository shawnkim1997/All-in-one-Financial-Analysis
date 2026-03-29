"use client";

import { ResponsiveBar } from "@nivo/bar";
import type { WaterfallStep } from "./types";

const barTheme = {
  background: "transparent",
  text: { fill: "#9CA3AF", fontSize: 11 },
  axis: {
    domain: { line: { stroke: "#374151" } },
    ticks: { line: { stroke: "#374151" }, text: { fill: "#9CA3AF" } },
    legend: { text: { fill: "#9CA3AF" } },
  },
  grid: { line: { stroke: "#2D2D3A" } },
  tooltip: {
    container: {
      background: "#1A1A26",
      color: "#E5E7EB",
      fontSize: 12,
      border: "1px solid #374151",
    },
  },
};

export function WaterfallWidget({ steps }: { steps: WaterfallStep[] }) {
  if (!steps.length) {
    return (
      <div className="text-text-muted text-sm h-full flex items-center justify-center">
        Operating income bridge not available (need 2+ annual columns).
      </div>
    );
  }

  const data = steps.map((s) => ({
    id: s.id,
    label: s.label,
    delta: s.value,
    type: s.step_type,
  }));

  return (
    <div className="w-full h-[min(380px,50vh)] min-h-[240px]">
      <ResponsiveBar
        data={data}
        keys={["delta"]}
        indexBy="label"
        layout="horizontal"
        margin={{ top: 8, right: 28, bottom: 40, left: 160 }}
        padding={0.35}
        valueScale={{ type: "linear" }}
        indexScale={{ type: "band", round: true }}
        colors={({ data: row }) => {
          const r = row as { type?: string; delta?: number };
          if (r.type === "total") return "#6366F1";
          return (r.delta ?? 0) >= 0 ? "#00D4AA" : "#F87171";
        }}
        borderRadius={2}
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 0,
          tickPadding: 8,
          legend: "USD (reported units)",
          legendPosition: "middle",
          legendOffset: 32,
          format: (v) => {
            const n = Number(v);
            const abs = Math.abs(n);
            if (abs >= 1e9) return `${(n / 1e9).toLocaleString(undefined, { maximumFractionDigits: 1 })}B`;
            if (abs >= 1e6) return `${(n / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}M`;
            if (abs >= 1e3) return `${(n / 1e3).toLocaleString(undefined, { maximumFractionDigits: 0 })}K`;
            return n.toLocaleString();
          },
        }}
        axisLeft={{
          tickSize: 0,
          tickPadding: 8,
        }}
        enableGridX
        enableGridY={false}
        valueFormat={(v) => {
          const abs = Math.abs(v);
          if (abs >= 1e9) return `$${(v / 1e9).toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B`;
          if (abs >= 1e6) return `$${(v / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}M`;
          if (abs >= 1e3) return `$${(v / 1e3).toLocaleString(undefined, { maximumFractionDigits: 0 })}K`;
          return `$${v.toLocaleString()}`;
        }}
        labelSkipWidth={12}
        labelSkipHeight={12}
        labelTextColor="#E5E7EB"
        theme={barTheme}
        tooltip={({ value, indexValue }) => (
          <div className="px-2 py-1 text-xs">
            <strong>{String(indexValue)}</strong>
            <div className="font-mono">{typeof value === "number" ? value.toLocaleString() : value}</div>
          </div>
        )}
      />
    </div>
  );
}
