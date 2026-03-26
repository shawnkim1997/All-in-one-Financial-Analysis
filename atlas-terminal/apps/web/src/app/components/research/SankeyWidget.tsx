"use client";

import { ResponsiveSankey } from "@nivo/sankey";
import type { SankeyNivoLink, SankeyNivoNode } from "./types";

const nivoTheme = {
  background: "transparent",
  text: { fill: "#9CA3AF", fontSize: 11 },
  tooltip: {
    container: {
      background: "#1A1A26",
      color: "#E5E7EB",
      fontSize: 12,
      border: "1px solid #374151",
    },
  },
  labels: { text: { fill: "#D1D5DB" } },
};

export function SankeyWidget({
  nodes,
  links,
}: {
  nodes: SankeyNivoNode[];
  links: SankeyNivoLink[];
}) {
  const data = {
    nodes: nodes.map((n) => ({
      id: n.id,
      label: n.label || n.id,
    })),
    links: links.map((l) => ({
      source: l.source,
      target: l.target,
      value: Math.max(l.value, 0),
    })),
  };

  if (!data.nodes.length || !data.links.length) {
    return <div className="text-text-muted text-sm h-full flex items-center justify-center">No Sankey data.</div>;
  }

  return (
    <div className="w-full h-[min(420px,55vh)] min-h-[280px]">
      <ResponsiveSankey
        data={data}
        margin={{ top: 12, right: 140, bottom: 12, left: 50 }}
        align="justify"
        sort="input"
        colors={{ scheme: "category10" }}
        nodeOpacity={1}
        nodeHoverOthersOpacity={0.35}
        nodeThickness={18}
        nodeSpacing={24}
        nodeBorderWidth={0}
        linkOpacity={0.5}
        linkHoverOthersOpacity={0.15}
        linkContract={3}
        enableLinkGradient
        labelPosition="outside"
        labelOrientation="horizontal"
        labelPadding={12}
        labelTextColor={{ from: "color", modifiers: [["darker", 1]] }}
        theme={nivoTheme}
        valueFormat={(v) => {
          const abs = Math.abs(v);
          if (abs >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
          if (abs >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
          if (abs >= 1e3) return `$${(v / 1e3).toFixed(0)}K`;
          return `$${v.toFixed(0)}`;
        }}
      />
    </div>
  );
}
