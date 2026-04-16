"use client";

import { ResponsiveBar } from "@nivo/bar";
import { chartPalette } from "../../lib/chart-theme";
import type { WaterfallStep } from "./types";

const barTheme = {
  background: "transparent",
  text: { fill: chartPalette.textMuted, fontSize: 11 },
  axis: {
    domain: { line: { stroke: chartPalette.grid } },
    ticks: { line: { stroke: chartPalette.grid }, text: { fill: chartPalette.textMuted } },
    legend: { text: { fill: chartPalette.textMuted } },
  },
  grid: { line: { stroke: chartPalette.grid } },
  tooltip: {
    container: {
      background: chartPalette.canvas,
      color: chartPalette.text,
      fontSize: 12,
      border: `1px solid ${chartPalette.grid}`,
    },
  },
};

function formatCompactNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e9) {
    return `${(value / 1e9).toLocaleString(undefined, { maximumFractionDigits: 1 })}B`;
  }
  if (abs >= 1e6) {
    return `${(value / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}M`;
  }
  if (abs >= 1e3) {
    return `${(value / 1e3).toLocaleString(undefined, { maximumFractionDigits: 0 })}K`;
  }
  return value.toLocaleString();
}

function niceStep(rawStep: number): number {
  if (!Number.isFinite(rawStep) || rawStep <= 0) return 1;
  const exponent = Math.floor(Math.log10(rawStep));
  const fraction = rawStep / 10 ** exponent;

  if (fraction <= 1) return 10 ** exponent;
  if (fraction <= 2) return 2 * 10 ** exponent;
  if (fraction <= 5) return 5 * 10 ** exponent;
  return 10 * 10 ** exponent;
}

function buildTickValues(values: number[], maxTicks = 5): number[] {
  if (!values.length) return [0];

  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min;

  if (span === 0) {
    return [min];
  }

  const step = niceStep(span / Math.max(1, maxTicks - 1));
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const ticks: number[] = [];

  for (let current = start; current <= end + step / 2; current += step) {
    ticks.push(Number(current.toFixed(6)));
  }

  return ticks.slice(0, maxTicks + 1);
}

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
  const tickValues = buildTickValues(data.map((d) => d.delta));

  return (
    <div className="w-full h-[min(380px,50vh)] min-h-[240px]">
      <ResponsiveBar
        data={data}
        keys={["delta"]}
        indexBy="label"
        layout="horizontal"
        margin={{ top: 8, right: 28, bottom: 56, left: 160 }}
        padding={0.35}
        valueScale={{ type: "linear" }}
        indexScale={{ type: "band", round: true }}
        colors={({ data: row }) => {
          const r = row as { type?: string; delta?: number };
          if (r.type === "total") return chartPalette.navy;
          return (r.delta ?? 0) >= 0 ? chartPalette.green : chartPalette.red;
        }}
        borderRadius={2}
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 0,
          tickPadding: 6,
          tickValues,
          legend: "USD (reported units)",
          legendPosition: "middle",
          legendOffset: 44,
          format: (v) => formatCompactNumber(Number(v)),
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
        labelTextColor={chartPalette.text}
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
