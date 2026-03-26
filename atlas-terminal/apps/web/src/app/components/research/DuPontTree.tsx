"use client";

import type { DuPontTreePayload, DuPontTreeNode } from "./types";

function trendClass(t: string): string {
  if (t === "up") return "text-accent-green";
  if (t === "down") return "text-accent-red";
  return "text-text-secondary";
}

function NodeCard({ node, subtitle }: { node: DuPontTreeNode; subtitle?: string }) {
  const val = node.unit === "x" ? `${node.value.toFixed(2)}×` : `${node.value.toFixed(2)}%`;
  return (
    <div className="rounded-md border border-border bg-bg-primary/40 px-3 py-2">
      <div className="text-text-muted text-xs">{node.label}</div>
      <div className={`font-mono text-lg ${trendClass(node.trend)}`}>{val}</div>
      {node.vs_5y_avg_pct != null && (
        <div className="text-text-muted text-[10px] mt-0.5">
          vs 5y avg {node.vs_5y_avg_pct > 0 ? "+" : ""}
          {node.vs_5y_avg_pct.toFixed(1)}%
        </div>
      )}
      {subtitle && <div className="text-text-muted text-[10px] mt-1">{subtitle}</div>}
    </div>
  );
}

export function DuPontTree({ tree }: { tree: DuPontTreePayload | null }) {
  if (!tree) {
    return <div className="text-text-muted text-sm">DuPont decomposition not available.</div>;
  }

  return (
    <div className="flex flex-col gap-3 h-full min-h-0">
      <NodeCard node={tree.root} subtitle="ROE = NPM × Asset turnover × Equity multiplier" />
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 flex-1 min-h-0">
        <NodeCard node={tree.npm} />
        <NodeCard node={tree.asset_turnover} />
        <NodeCard node={tree.equity_mult} />
      </div>
    </div>
  );
}
