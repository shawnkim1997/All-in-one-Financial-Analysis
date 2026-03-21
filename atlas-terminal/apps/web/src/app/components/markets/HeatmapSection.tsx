"use client";

import { useEffect, useMemo, useState } from "react";

type HeatmapStock = {
  ticker: string;
  name: string;
  sector: string;
  market_cap: number;
  change_pct: number;
};

const INDEX_OPTIONS = [
  { id: "sp500", label: "S&P 500" },
  { id: "nasdaq100", label: "NASDAQ 100" },
  { id: "kospi", label: "KOSPI" },
  { id: "ftse100", label: "FTSE 100" },
];

export function HeatmapSection({
  selectedIndex,
  onSelectIndex,
}: {
  selectedIndex: string;
  onSelectIndex: (v: string) => void;
}) {
  const [stocks, setStocks] = useState<HeatmapStock[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/markets/heatmap/${selectedIndex}?top_n=50`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setStocks(Array.isArray(d?.stocks) ? d.stocks : []))
      .finally(() => setLoading(false));
  }, [selectedIndex]);

  const grouped = useMemo(() => {
    const sectors: Record<string, HeatmapStock[]> = {};
    for (const s of stocks) {
      const k = s.sector || "Other";
      if (!sectors[k]) sectors[k] = [];
      sectors[k].push(s);
    }
    return sectors;
  }, [stocks]);

  const totalMcap = stocks.reduce((sum, s) => sum + (s.market_cap || 0), 0);

  return (
    <div id="heatmap-section" className="bg-bg-card border border-border rounded-lg p-4">
      <div className="heatmap-header">
        <h3 className="text-text-secondary text-sm font-semibold">Stock Heatmap</h3>
        <div className="index-toggle">
          {INDEX_OPTIONS.map((idx) => (
            <button
              key={idx.id}
              className={`index-btn ${selectedIndex === idx.id ? "active" : ""}`}
              onClick={() => onSelectIndex(idx.id)}
            >
              {idx.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="heatmap-loading">Loading heatmap...</div>
      ) : (
        <div className="treemap-container">
          {Object.entries(grouped).map(([sector, sectorStocks]) => {
            const sectorMcap = sectorStocks.reduce((s, st) => s + (st.market_cap || 0), 0);
            const sectorPct = totalMcap > 0 ? (sectorMcap / totalMcap) * 100 : 0;
            return (
              <div
                key={sector}
                className="treemap-sector"
                style={{ flexBasis: `${Math.max(sectorPct, 8)}%`, flexGrow: Math.max(sectorPct, 8) }}
              >
                <div className="treemap-sector-label">{sector}</div>
                <div className="treemap-stocks">
                  {sectorStocks.map((stock) => {
                    const stockPct = sectorMcap > 0 ? (stock.market_cap / sectorMcap) * 100 : 0;
                    const intensity = Math.min(Math.abs(stock.change_pct) / 4, 1);
                    const isPositive = stock.change_pct >= 0;
                    const primaryLabel = selectedIndex === "kospi" ? (stock.name || stock.ticker) : stock.ticker;
                    const secondaryLabel = selectedIndex === "kospi" ? stock.ticker : "";
                    return (
                      <div
                        key={stock.ticker}
                        className="treemap-cell"
                        style={{
                          flexBasis: `${Math.max(stockPct, 8)}%`,
                          flexGrow: Math.max(stockPct, 8),
                          backgroundColor: isPositive
                            ? `rgba(0, 212, 170, ${0.15 + intensity * 0.6})`
                            : `rgba(255, 71, 87, ${0.15 + intensity * 0.6})`,
                        }}
                        title={`${stock.name}\n${stock.change_pct >= 0 ? "+" : ""}${stock.change_pct}%`}
                      >
                        <span className="treemap-ticker">{primaryLabel}</span>
                        {secondaryLabel ? <span className="treemap-subticker">{secondaryLabel}</span> : null}
                        <span className="treemap-change">
                          {stock.change_pct >= 0 ? "+" : ""}
                          {stock.change_pct}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

