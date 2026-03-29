"use client";

import { useEffect, useState } from "react";
import { KpiSection, type KpiHistoryData } from "./KpiSection";
import { PeerComparison, type PeerComparisonData } from "./PeerComparison";

interface EquityOverviewProps {
  ticker: string;
  sector: Record<string, unknown> | null;
  health: Record<string, unknown> | null;
}

export function EquityOverview({ ticker, sector, health }: EquityOverviewProps) {
  const [peerData, setPeerData] = useState<PeerComparisonData | null>(null);
  const [kpiData, setKpiData] = useState<KpiHistoryData | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/market/peers/${encodeURIComponent(ticker)}`).then((r) => (r.ok ? r.json() : null)),
      fetch(`/api/financials/${encodeURIComponent(ticker)}/kpi-history`).then((r) => (r.ok ? r.json() : null)),
    ]).then(([p, k]) => {
      if (!cancelled) {
        setPeerData(p && Array.isArray(p.peers) ? p : null);
        setKpiData(k && Array.isArray(k.quarters) ? k : null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [ticker]);
  const metrics: { label: string; value: string }[] = [
    { label: "Sector", value: String(sector?.sector ?? "—") },
    { label: "Industry", value: String(sector?.industry ?? "—") },
    { label: "Market Cap", value: sector?.market_cap ? `$${(Number(sector.market_cap) / 1e9).toFixed(1)}B` : "—" },
    { label: "P/E (TTM)", value: sector?.pe_ratio != null ? Number(sector.pe_ratio).toFixed(1) : "—" },
    { label: "P/E (NTM)", value: sector?.forward_pe != null ? Number(sector.forward_pe).toFixed(1) : "—" },
    { label: "PEG Ratio", value: sector?.peg_ratio != null ? Number(sector.peg_ratio).toFixed(2) : "—" },
    { label: "Beta", value: sector?.beta != null ? Number(sector.beta).toFixed(2) : "—" },
    { label: "Div Yield", value: sector?.dividend_yield != null ? `${Number(sector.dividend_yield).toFixed(2)}%` : "—" },
    { label: "52W High", value: sector?.fifty_two_week_high != null ? `$${Number(sector.fifty_two_week_high).toFixed(2)}` : "—" },
    { label: "52W Low", value: sector?.fifty_two_week_low != null ? `$${Number(sector.fifty_two_week_low).toFixed(2)}` : "—" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">
        <span className="text-accent-green">{ticker}</span> Overview
      </h1>
      {sector?.current_price != null && (
        <p className="text-3xl font-mono font-bold text-text-primary mb-6">${Number(sector.current_price).toFixed(2)}</p>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {metrics.map((m) => (
          <div key={m.label} className="bg-bg-card border border-border rounded-lg p-4">
            <div className="text-text-muted text-xs mb-1">{m.label}</div>
            <div className="text-text-primary font-semibold">{m.value}</div>
          </div>
        ))}
      </div>
      <ConsensusGauge sector={sector} />
      <KpiSection data={kpiData} />
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
        <Card title="Altman Z-Score" value={health?.altman_z != null ? Number(health.altman_z).toFixed(2) : "—"} />
        <Card title="Current Ratio" value={health?.current_ratio != null ? Number(health.current_ratio).toFixed(2) : "—"} />
        <Card title="Interest Cov." value={health?.interest_coverage != null ? `${Number(health.interest_coverage).toFixed(1)}x` : "—"} />
        <Card title="D/E Ratio" value={health?.debt_to_equity != null ? Number(health.debt_to_equity).toFixed(2) : "—"} />
      </div>
      <div className="bg-bg-card border border-border rounded-lg p-5">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">DuPont Analysis</h3>
        {!!health?.dupont && typeof health.dupont === "object" && health.dupont !== null ? (
          <div className="space-y-2">
            {[
              { label: "ROE", value: (health.dupont as { roe?: unknown }).roe },
              { label: "Net Profit Margin", value: (health.dupont as { npm?: unknown }).npm },
              { label: "Asset Turnover", value: (health.dupont as { asset_turnover?: unknown }).asset_turnover },
              { label: "Equity Multiplier", value: (health.dupont as { equity_multiplier?: unknown }).equity_multiplier },
            ].map((d) => (
              <div key={d.label} className="flex justify-between">
                <span className="text-text-muted text-sm">{d.label}</span>
                <span className="text-text-primary font-mono">{d.value != null ? Number(d.value).toFixed(2) : "—"}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-text-muted">No data</div>
        )}
      </div>
      <PeerComparison currentTicker={ticker} data={peerData} />
    </div>
  );
}

function ConsensusGauge({ sector }: { sector: Record<string, unknown> | null }) {
  const current = sector?.current_price != null ? Number(sector.current_price) : null;
  const target = sector?.target_mean_price != null ? Number(sector.target_mean_price) : null;
  const low = sector?.target_low_price != null ? Number(sector.target_low_price) : null;
  const high = sector?.target_high_price != null ? Number(sector.target_high_price) : null;
  const rec = sector?.recommendation as string | undefined;
  const count = sector?.analyst_count != null ? Number(sector.analyst_count) : null;

  if (!current || !target) return null;

  const upside = ((target - current) / current) * 100;
  const upsideColor = upside >= 0 ? "text-accent-green" : "text-accent-red";
  const recLabel = rec ? rec.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "—";

  // gauge position: map current price within [low, high] range
  const gaugeLow = low ?? target * 0.7;
  const gaugeHigh = high ?? target * 1.3;
  const range = gaugeHigh - gaugeLow;
  const currentPct = range > 0 ? Math.max(0, Math.min(100, ((current - gaugeLow) / range) * 100)) : 50;
  const targetPct = range > 0 ? Math.max(0, Math.min(100, ((target - gaugeLow) / range) * 100)) : 50;

  return (
    <div className="bg-bg-card border border-border rounded-lg p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary text-sm font-semibold">Analyst Consensus</h3>
        {count != null && <span className="text-text-muted text-xs">{count} analysts</span>}
      </div>
      <div className="flex items-baseline gap-4 mb-4">
        <div>
          <span className="text-text-muted text-xs block">Target</span>
          <span className="text-2xl font-mono font-bold text-text-primary">${target.toFixed(2)}</span>
        </div>
        <div>
          <span className="text-text-muted text-xs block">Upside</span>
          <span className={`text-xl font-mono font-bold ${upsideColor}`}>
            {upside >= 0 ? "+" : ""}{upside.toFixed(1)}%
          </span>
        </div>
        <div>
          <span className="text-text-muted text-xs block">Rating</span>
          <span className="text-lg font-semibold text-text-primary">{recLabel}</span>
        </div>
      </div>
      {/* Visual gauge bar */}
      <div className="relative h-2 bg-bg-hover rounded-full mb-2">
        {/* target marker */}
        <div className="absolute top-0 h-2 w-0.5 bg-accent-yellow" style={{ left: `${targetPct}%` }} />
        {/* current price marker */}
        <div className="absolute -top-1 h-4 w-1 bg-accent-green rounded-sm" style={{ left: `${currentPct}%` }} />
      </div>
      <div className="flex justify-between text-text-muted text-xs font-mono">
        <span>${gaugeLow.toFixed(0)}</span>
        <span>${gaugeHigh.toFixed(0)}</span>
      </div>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="bg-bg-card border border-border rounded-lg p-5">
      <h3 className="text-text-secondary text-sm font-semibold mb-3">{title}</h3>
      <div className="text-3xl font-mono font-bold text-text-primary">{value}</div>
    </div>
  );
}
