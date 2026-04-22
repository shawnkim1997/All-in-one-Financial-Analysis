"use client";

import { useState } from "react";
import { ErrorBanner } from "../ui/ErrorBanner";
import { LoadingPulse } from "../ui/LoadingPulse";
import { flags } from "../../lib/flags";
import { useApi } from "../../lib/use-api";

type StatementKey = "income" | "balance" | "cashflow";
type PeriodKey = "annual" | "quarter";

interface StatementResponse {
  ticker: string;
  statement: string;
  period: string;
  source: string;
  periods: string[];
  line_items: Record<string, Array<number | null>>;
}

const STATEMENTS: { key: StatementKey; label: string }[] = [
  { key: "income", label: "Income" },
  { key: "balance", label: "Balance Sheet" },
  { key: "cashflow", label: "Cash Flow" },
];

const LINE_LABELS: Record<string, string> = {
  revenue: "Revenue",
  totalRevenue: "Revenue",
  TotalRevenue: "Revenue",
  costOfRevenue: "Cost of Revenue",
  grossProfit: "Gross Profit",
  GrossProfit: "Gross Profit",
  operatingIncome: "Operating Income",
  OperatingIncome: "Operating Income",
  netIncome: "Net Income",
  NetIncome: "Net Income",
  totalAssets: "Total Assets",
  TotalAssets: "Total Assets",
  totalLiabilities: "Total Liabilities",
  TotalLiabilitiesNetMinorityInterest: "Total Liabilities",
  totalStockholdersEquity: "Equity",
  StockholdersEquity: "Equity",
  operatingCashFlow: "Operating Cash Flow",
  OperatingCashFlow: "Operating Cash Flow",
  capitalExpenditure: "Capex",
  CapitalExpenditure: "Capex",
  freeCashFlow: "Free Cash Flow",
};

function formatLineLabel(key: string): string {
  return LINE_LABELS[key] || key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ");
}

function formatValue(value: number | null): string {
  if (value == null) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
  return `${sign}$${abs.toFixed(0)}`;
}

function yoy(values: Array<number | null>, idx: number): number | null {
  const current = values[idx];
  const previous = values[idx + 1];
  if (current == null || previous == null || previous === 0) return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}

function Sparkline({ values }: { values: Array<number | null> }) {
  const nums = values.filter((value): value is number => value != null);
  if (nums.length < 2) return <span className="text-text-muted">—</span>;
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const range = max - min || 1;
  const points = values
    .map((value, idx) => {
      const v = value ?? min;
      return `${idx * 16},${24 - ((v - min) / range) * 22}`;
    })
    .join(" ");
  return (
    <svg width="72" height="26" aria-hidden="true">
      <polyline points={points} fill="none" stroke="#2E5B9A" strokeWidth="1.8" />
    </svg>
  );
}

export function FinancialStatements({ ticker }: { ticker: string }) {
  const [statement, setStatement] = useState<StatementKey>("income");
  const [period, setPeriod] = useState<PeriodKey>("annual");
  const url = flags.financials ? `/api/financials/${encodeURIComponent(ticker)}/table?statement=${statement}&period=${period}` : null;
  const { data, loading, error } = useApi<StatementResponse>(url, { cacheTtlMs: 300_000 });
  const entries = data ? Object.entries(data.line_items).slice(0, 12) : [];

  if (!flags.financials) return null;

  return (
    <div className="atlas-table-shell mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3 p-5">
        <div>
          <h3 className="font-serif text-lg font-bold text-brand-navy">Financial Statements</h3>
          <p className="mt-1 text-xs text-text-muted">Gateway-backed statement table with YoY deltas.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {STATEMENTS.map((item) => (
            <button key={item.key} type="button" onClick={() => setStatement(item.key)} className={`rounded border px-3 py-1.5 text-xs font-semibold ${statement === item.key ? "border-brand-navy bg-brand-navy text-white" : "border-border text-text-secondary hover:bg-surface-sunken"}`}>
              {item.label}
            </button>
          ))}
          {(["annual", "quarter"] as PeriodKey[]).map((item) => (
            <button key={item} type="button" onClick={() => setPeriod(item)} className={`rounded border px-3 py-1.5 text-xs font-semibold capitalize ${period === item ? "border-brand-gold bg-brand-gold/20 text-brand-navy" : "border-border text-text-secondary hover:bg-surface-sunken"}`}>
              {item}
            </button>
          ))}
        </div>
      </div>
      <ErrorBanner variant="error" message={error} className="mx-5 mb-4" />
      {loading ? <LoadingPulse height="h-40" label="Loading statements..." /> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="bg-surface-sunken">
              <tr className="border-y border-border-strong text-[11px] uppercase tracking-[0.12em] text-brand-navy">
                <th className="px-5 py-3 text-left font-semibold">Line Item</th>
                {(data?.periods || []).map((p) => <th key={p} className="px-3 py-3 text-right font-semibold">{p}</th>)}
                <th className="px-5 py-3 text-right font-semibold">Trend</th>
              </tr>
            </thead>
            <tbody>
              {entries.length > 0 ? entries.map(([key, values]) => (
                <tr key={key} className="border-b border-border/60 hover:bg-surface-sunken">
                  <td className="px-5 py-3 font-semibold text-brand-navy">{formatLineLabel(key)}</td>
                  {values.slice(0, data?.periods.length || 0).map((value, idx) => {
                    const growth = yoy(values, idx);
                    return (
                      <td key={`${key}-${idx}`} className="px-3 py-3 text-right font-mono tabular-nums text-text-primary">
                        <div>{formatValue(value)}</div>
                        {growth != null && <div className={`text-[10px] ${growth >= 0 ? "text-fin-positive" : "text-fin-negative"}`}>{growth >= 0 ? "+" : ""}{growth.toFixed(1)}%</div>}
                      </td>
                    );
                  })}
                  <td className="px-5 py-3 text-right"><Sparkline values={values} /></td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={(data?.periods.length || 0) + 2} className="px-5 py-8 text-center text-text-muted">
                    No statement data available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
