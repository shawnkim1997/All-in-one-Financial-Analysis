"use client";

import { Fragment } from "react";

interface MacroIndicator {
  key: string;
  label: string;
  value: number | null;
  unit: string;
  zscore: number | null;
  signal: string;
}

interface CountryHeatmapRow {
  country: string;
  region?: string;
  inflation: number | null;
  unemployment: number | null;
  policy_rate: number | null;
  gdp_growth?: number | null;
  debt_gdp?: number | null;
  score: number | null;
}

interface AssetValuationRow {
  asset: string;
  symbol: string;
  price: number;
  history_mean: number;
  zscore: number | null;
  status: string;
}

export interface MacroSnapshot {
  updated_at: string | null;
  cycle_score: number;
  regime: string;
  cycle_heatmap: MacroIndicator[];
  country_heatmap: CountryHeatmapRow[];
  asset_valuation: AssetValuationRow[];
}

function heatClass(score: number | null): string {
  if (score == null) return "bg-bg-primary text-text-muted";
  if (score >= 0.75) return "bg-accent-green/25 text-accent-green";
  if (score <= -0.75) return "bg-accent-red/25 text-accent-red";
  return "bg-accent-yellow/15 text-accent-yellow";
}

function fmt(v: number | null | undefined, suffix = "%"): string {
  if (v == null) return "—";
  return `${v.toFixed(2)}${suffix}`;
}

const REGION_ORDER = ["Americas", "Europe", "Asia-Pacific"];

export function MacroCycleHeatmap({ data }: { data: MacroSnapshot | null }) {
  if (!data) {
    return (
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Macro Cycle Heatmap</h3>
        <div className="text-text-muted text-sm">Macro snapshot is unavailable right now.</div>
      </div>
    );
  }

  const grouped: Record<string, CountryHeatmapRow[]> = {};
  for (const row of data.country_heatmap) {
    const region = row.region || "Other";
    (grouped[region] ||= []).push(row);
  }

  return (
    <div className="space-y-4">
      {/* US Cycle Indicators */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <div className="flex items-end justify-between gap-4 mb-4">
          <div>
            <h3 className="text-text-secondary text-sm font-semibold">Macro Cycle Heatmap</h3>
            <div className="text-text-muted text-xs mt-1">
              FRED-based cycle dashboard for inflation, labor, rates, and production.
            </div>
          </div>
          <div className="text-right">
            <div className="text-text-muted text-xs">Current Regime</div>
            <div className="text-text-primary font-mono font-bold text-lg">{data.regime}</div>
            <div className={`text-xs font-mono ${data.cycle_score >= 0 ? "text-accent-green" : "text-accent-red"}`}>
              Cycle Score {data.cycle_score >= 0 ? "+" : ""}{data.cycle_score.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {data.cycle_heatmap.map((item) => (
            <div key={item.key} className="bg-bg-primary border border-border rounded-md p-3">
              <div className="text-text-muted text-xs">{item.label}</div>
              <div className="text-text-primary font-mono font-bold text-xl mt-1">
                {item.value == null ? "—" : `${item.value.toFixed(2)}${item.unit ? ` ${item.unit}` : ""}`}
              </div>
              <div className="mt-2">
                <span className={`inline-flex px-2 py-1 rounded text-[11px] font-semibold ${heatClass(item.zscore)}`}>
                  Z {item.zscore == null ? "—" : item.zscore.toFixed(2)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Country Heatmap (grouped by region) */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Global Country Heatmap</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-left">
                <th className="py-2 pr-3">Country</th>
                <th className="py-2 pr-3">Inflation</th>
                <th className="py-2 pr-3">Unemployment</th>
                <th className="py-2 pr-3">Policy Rate</th>
                <th className="py-2 pr-3">GDP Growth</th>
                <th className="py-2 pr-3">Debt/GDP</th>
                <th className="py-2">Score</th>
              </tr>
            </thead>
            <tbody>
              {REGION_ORDER.map((region) => {
                const rows = grouped[region];
                if (!rows?.length) return null;
                return (
                  <Fragment key={region}>
                    <tr>
                      <td colSpan={7} className="pt-3 pb-1 text-[11px] font-semibold text-accent-green tracking-wider uppercase">
                        {region}
                      </td>
                    </tr>
                    {rows.map((row) => (
                      <tr key={row.country} className="border-b border-border/40 hover:bg-bg-primary/30 transition-colors">
                        <td className="py-2 pr-3 text-text-primary">{row.country}</td>
                        <td className="py-2 pr-3 font-mono text-text-primary">{fmt(row.inflation)}</td>
                        <td className="py-2 pr-3 font-mono text-text-primary">{fmt(row.unemployment)}</td>
                        <td className="py-2 pr-3 font-mono text-text-primary">{fmt(row.policy_rate)}</td>
                        <td className="py-2 pr-3 font-mono text-text-primary">{fmt(row.gdp_growth)}</td>
                        <td className="py-2 pr-3 font-mono text-text-primary">{fmt(row.debt_gdp)}</td>
                        <td className="py-2">
                          <span className={`inline-flex px-2 py-1 rounded text-[11px] font-semibold ${heatClass(row.score)}`}>
                            {row.score == null ? "—" : row.score.toFixed(2)}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Asset Valuation */}
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">Asset Valuation Snapshot</h3>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          {data.asset_valuation.map((asset) => (
            <div key={asset.symbol} className="bg-bg-primary border border-border rounded-md p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-text-primary font-semibold">{asset.asset}</div>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${heatClass(asset.zscore)}`}>
                  {asset.status}
                </span>
              </div>
              <div className="text-text-muted text-xs mt-1">{asset.symbol}</div>
              <div className="mt-2 text-text-primary font-mono">${asset.price.toFixed(2)}</div>
              <div className="text-text-muted text-xs font-mono mt-1">
                Mean ${asset.history_mean.toFixed(2)} | Z {asset.zscore == null ? "—" : asset.zscore.toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
