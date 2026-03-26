"use client";

import type { ReactNode } from "react";
import { FScorePanel } from "./FScorePanel";
import { DuPontTree } from "./DuPontTree";
import { SankeyWidget } from "./SankeyWidget";
import { WaterfallWidget } from "./WaterfallWidget";
import { AnomalyChips } from "./AnomalyChips";
import type { ResearchDashboardPayload } from "./types";

function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="bg-bg-card border border-border rounded-lg overflow-hidden flex flex-col min-h-[280px] h-full shadow-sm">
      <div className="px-3 py-2 border-b border-border text-xs text-text-muted font-semibold tracking-wide uppercase select-none">
        {title}
      </div>
      <div className="p-3 flex-1 min-h-0 overflow-auto">{children}</div>
    </div>
  );
}

/**
 * CSS grid layout (no react-grid-layout) — avoids SSR/hydration issues with WidthProvider.
 */
export function ResearchGridLayout({ dashboard }: { dashboard: ResearchDashboardPayload }) {
  const { ticker, fscore_total, fscore_criteria, dupont_tree, sankey, waterfall, anomalies } = dashboard;
  const criteria = fscore_criteria ?? [];
  const sk = sankey ?? { nodes: [], links: [] };
  const wf = waterfall ?? [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
      <div className="lg:col-span-4 min-h-[300px]">
        <Panel title="F-Score history">
          <FScorePanel total={Number(fscore_total) || 0} criteria={criteria} />
        </Panel>
      </div>
      <div className="lg:col-span-8 min-h-[300px]">
        <Panel title="DuPont tree">
          <DuPontTree tree={dupont_tree} />
        </Panel>
      </div>
      <div className="lg:col-span-7 min-h-[380px]">
        <Panel title="Income statement flow">
          <SankeyWidget nodes={sk.nodes} links={sk.links} />
        </Panel>
      </div>
      <div className="lg:col-span-5 min-h-[380px]">
        <Panel title="Operating income bridge">
          <WaterfallWidget steps={wf} />
        </Panel>
      </div>
      <div className="lg:col-span-12 min-h-[200px]">
        <Panel title={`YoY anomalies — ${ticker}`}>
          <p className="text-text-muted text-xs mb-3">
            칩을 누르면 10-K 발췌와 Gemini로 설명합니다. 숫자는 서버에서만 계산됩니다.
          </p>
          <AnomalyChips ticker={ticker} anomalies={anomalies ?? []} />
        </Panel>
      </div>
    </div>
  );
}
