"use client";

import { useEffect, useState, type ReactNode } from "react";
import { KpiSection, type KpiHistoryData } from "./KpiSection";
import { PeerComparison, type PeerComparisonData } from "./PeerComparison";
import { FinancialStatements } from "./FinancialStatements";
import { Ownership } from "./Ownership";
import { RedTeamCritique } from "./RedTeamCritique";
import { Card } from "../ui/Card";
import { SectionHeading } from "../ui/SectionHeading";
import { StatCard } from "../ui/StatCard";
import { useApi } from "../../lib/use-api";

interface EquityOverviewProps {
  ticker: string;
  sector: Record<string, unknown> | null;
  health: Record<string, unknown> | null;
}

interface FxRateMatrix {
  rates?: Record<string, number>;
}

const ZERO_DECIMAL_CURRENCIES = new Set(["KRW", "JPY"]);
const CURRENCY_LOCALES: Record<string, string> = {
  KRW: "ko-KR",
  JPY: "ja-JP",
  USD: "en-US",
  EUR: "de-DE",
  GBP: "en-GB",
  DKK: "da-DK",
};

function getCurrencyCode(ticker: string, sector: Record<string, unknown> | null): string {
  const raw = typeof sector?.currency === "string" ? sector.currency.trim().toUpperCase() : "";
  if (raw) return raw;
  if (ticker.endsWith(".KS") || ticker.endsWith(".KQ")) return "KRW";
  if (ticker.endsWith(".T")) return "JPY";
  return "USD";
}

function currencyLocale(currency: string): string {
  return CURRENCY_LOCALES[currency] || "en-US";
}

function formatCurrencyValue(value: number, currency: string, fractionDigits?: number): string {
  const digits = fractionDigits ?? (ZERO_DECIMAL_CURRENCIES.has(currency) ? 0 : 2);
  return new Intl.NumberFormat(currencyLocale(currency), {
    style: "currency",
    currency,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatCompactCurrency(value: number, currency: string): string {
  return new Intl.NumberFormat(currencyLocale(currency), {
    style: "currency",
    currency,
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 1,
  }).format(value);
}

function formatUsdEquivalent(value: number, currency: string, rates?: Record<string, number>, compact = false): string | null {
  if (currency === "USD") return null;
  const rate = rates?.[`${currency}_USD`];
  if (typeof rate !== "number" || !Number.isFinite(rate) || rate <= 0) return null;
  const usdValue = value * rate;
  return compact
    ? formatCompactCurrency(usdValue, "USD")
    : formatCurrencyValue(usdValue, "USD", ZERO_DECIMAL_CURRENCIES.has(currency) ? 0 : 2);
}

function moneyDisplay(
  value: number | null | undefined,
  currency: string,
  rates?: Record<string, number>,
  opts: { compact?: boolean } = {},
): { primary: string; secondary: string | null } {
  if (value == null || !Number.isFinite(value)) {
    return { primary: "—", secondary: null };
  }
  const primary = opts.compact ? formatCompactCurrency(value, currency) : formatCurrencyValue(value, currency);
  const usd = formatUsdEquivalent(value, currency, rates, opts.compact === true);
  return { primary, secondary: usd ? `= ${usd}` : null };
}

function splitLeadingCurrency(display: string, currency: string): { symbol: string; value: string } | null {
  const knownSymbols: Record<string, string> = {
    USD: "$",
    EUR: "€",
    GBP: "£",
    JPY: "¥",
    KRW: "₩",
  };
  const symbol = knownSymbols[currency];
  if (!symbol || !display.startsWith(symbol)) return null;
  return { symbol, value: display.slice(symbol.length) };
}

function MoneyValue({
  display,
  currency,
  emphasis = "card",
}: {
  display: string;
  currency: string;
  emphasis?: "hero" | "card" | "label";
}) {
  const parts = splitLeadingCurrency(display, currency);
  if (!parts) return <>{display}</>;

  const symbolClass =
    emphasis === "hero"
      ? "mr-1 align-top text-[0.56em] font-semibold text-text-secondary"
      : emphasis === "label"
        ? "mr-0.5 align-top text-[0.7em] font-semibold text-text-muted"
        : "mr-0.5 align-top text-[0.68em] font-semibold text-text-muted";

  return (
    <span className="tabular-nums">
      <span className={symbolClass}>{parts.symbol}</span>
      <span>{parts.value}</span>
    </span>
  );
}

export function EquityOverview({ ticker, sector, health }: EquityOverviewProps) {
  const [peerData, setPeerData] = useState<PeerComparisonData | null>(null);
  const [kpiData, setKpiData] = useState<KpiHistoryData | null>(null);
  const fx = useApi<FxRateMatrix>("/api/fx/rates", { cacheTtlMs: 300_000 });
  const currency = getCurrencyCode(ticker, sector);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/market/peers/${encodeURIComponent(ticker)}`).then((r) => (r.ok ? r.json() : null)),
      fetch(`/api/financials/${encodeURIComponent(ticker)}/kpi-history`).then((r) => (r.ok ? r.json() : null)),
    ]).then(([p, k]) => {
      if (!cancelled) {
        setPeerData(p && (Array.isArray(p.matrix) || Array.isArray(p.peers)) ? p : null);
        setKpiData(k && Array.isArray(k.quarters) ? k : null);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [ticker]);
  const marketCap = moneyDisplay(sector?.market_cap != null ? Number(sector.market_cap) : null, currency, fx.data?.rates, { compact: true });
  const high52w = moneyDisplay(sector?.fifty_two_week_high != null ? Number(sector.fifty_two_week_high) : null, currency, fx.data?.rates);
  const low52w = moneyDisplay(sector?.fifty_two_week_low != null ? Number(sector.fifty_two_week_low) : null, currency, fx.data?.rates);
  const spot = moneyDisplay(sector?.current_price != null ? Number(sector.current_price) : null, currency, fx.data?.rates);

  const metrics: { label: string; value: ReactNode; detail?: string }[] = [
    { label: "Sector", value: String(sector?.sector ?? "—") },
    { label: "Industry", value: String(sector?.industry ?? "—") },
    { label: "Market Cap", value: <MoneyValue display={marketCap.primary} currency={currency} />, detail: marketCap.secondary || undefined },
    { label: "P/E (TTM)", value: sector?.pe_ratio != null ? Number(sector.pe_ratio).toFixed(1) : "—" },
    { label: "P/E (NTM)", value: sector?.forward_pe != null ? Number(sector.forward_pe).toFixed(1) : "—" },
    { label: "PEG Ratio", value: sector?.peg_ratio != null ? Number(sector.peg_ratio).toFixed(2) : "—" },
    { label: "Beta", value: sector?.beta != null ? Number(sector.beta).toFixed(2) : "—" },
    { label: "Div Yield", value: sector?.dividend_yield != null ? `${Number(sector.dividend_yield).toFixed(2)}%` : "—" },
    { label: "52W High", value: <MoneyValue display={high52w.primary} currency={currency} />, detail: high52w.secondary || undefined },
    { label: "52W Low", value: <MoneyValue display={low52w.primary} currency={currency} />, detail: low52w.secondary || undefined },
  ];

  return (
    <div className="atlas-page">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <SectionHeading level={1}>{ticker} Overview</SectionHeading>
        <RedTeamCritique ticker={ticker} />
      </div>
      {sector?.current_price != null && (
        <div className="mb-6">
          <p className="text-3xl font-mono font-bold text-text-primary">
            <MoneyValue display={spot.primary} currency={currency} emphasis="hero" />
          </p>
          {spot.secondary && <p className="mt-1 text-sm font-mono text-text-muted">{spot.secondary}</p>}
        </div>
      )}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {metrics.map((m) => (
          <StatCard key={m.label} label={m.label} value={m.value} detail={m.detail} />
        ))}
      </div>
      <ConsensusGauge ticker={ticker} sector={sector} rates={fx.data?.rates} />
      <KpiSection data={kpiData} />
      <div className="grid grid-cols-1 gap-4 mb-4 lg:grid-cols-4">
        <OverviewStat title="Altman Z-Score" value={health?.altman_z != null ? Number(health.altman_z).toFixed(2) : "—"} />
        <OverviewStat title="Current Ratio" value={health?.current_ratio != null ? Number(health.current_ratio).toFixed(2) : "—"} />
        <OverviewStat title="Interest Cov." value={health?.interest_coverage != null ? `${Number(health.interest_coverage).toFixed(1)}x` : "—"} />
        <OverviewStat title="D/E Ratio" value={health?.debt_to_equity != null ? Number(health.debt_to_equity).toFixed(2) : "—"} />
      </div>
      <Card title="DuPont Analysis">
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
      </Card>
      <PeerComparison currentTicker={ticker} data={peerData} />
      <FinancialStatements ticker={ticker} />
      <Ownership ticker={ticker} />
    </div>
  );
}

function ConsensusGauge({
  ticker,
  sector,
  rates,
}: {
  ticker: string;
  sector: Record<string, unknown> | null;
  rates?: Record<string, number>;
}) {
  const currency = getCurrencyCode(ticker, sector);
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
  const targetDisplay = moneyDisplay(target, currency, rates);

  return (
    <Card title="Analyst Consensus" className="mb-6">
      <div className="flex items-center justify-between mb-3">
        {count != null && <span className="text-text-muted text-xs">{count} analysts</span>}
      </div>
      <div className="flex items-baseline gap-4 mb-4">
        <div>
          <span className="text-text-muted text-xs block">Target</span>
          <span className="text-2xl font-mono font-bold text-text-primary">
            <MoneyValue display={targetDisplay.primary} currency={currency} emphasis="card" />
          </span>
          {targetDisplay.secondary && <span className="mt-1 block text-xs font-mono text-text-muted">{targetDisplay.secondary}</span>}
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
      <div className="relative mb-2 h-2 rounded-full bg-surface-sunken">
        {/* target marker */}
        <div className="absolute top-0 h-2 w-0.5 bg-brand-gold" style={{ left: `${targetPct}%` }} />
        {/* current price marker */}
        <div className="absolute -top-1 h-4 w-1 rounded-sm bg-brand-navy" style={{ left: `${currentPct}%` }} />
      </div>
      <div className="flex justify-between text-text-muted text-xs font-mono">
        <span><MoneyValue display={moneyDisplay(gaugeLow, currency, rates).primary} currency={currency} emphasis="label" /></span>
        <span><MoneyValue display={moneyDisplay(gaugeHigh, currency, rates).primary} currency={currency} emphasis="label" /></span>
      </div>
    </Card>
  );
}

function OverviewStat({ title, value }: { title: string; value: string }) {
  return (
    <Card title={title}>
      <div className="text-3xl font-mono font-bold text-text-primary">{value}</div>
    </Card>
  );
}
