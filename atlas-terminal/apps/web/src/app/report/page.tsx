"use client";

import { useCallback, useState } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend, ReferenceLine,
} from "recharts";
import { useTicker } from "../lib/use-ticker";

/* ═══════════════════════════════════════════════════════════════════
   Design Tokens — "Morgan Stanley Blue"
   ═══════════════════════════════════════════════════════════════════ */
const C = {
  navy: "#1B2A4A", blue: "#2E5B9A", gold: "#C4A35A",
  green: "#2D8B5E", red: "#C0392B", gray: "#6B7B8D",
  lightGray: "#E8ECF0", bg: "#FFFFFF", text: "#1A1A2E", muted: "#6B7B8D",
};

/* ═══════════════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════════════ */
interface FinancialPeriod { [key: string]: any }

interface ResearchDash {
  ticker: string; fscore_total: number;
  fscore_criteria: { key: string; label: string; history: { year: number; pass_flag: boolean }[] }[];
  dupont_tree?: { root: { value: number }; npm: { value: number; trend: string }; asset_turnover: { value: number; trend: string }; equity_mult: { value: number; trend: string } };
  sankey: any; waterfall: { id: string; label: string; value: number; cumulative: number; step_type: string }[];
  anomalies: { account_key: string; display_name: string; change_pct: number; direction: string }[];
}

interface InstitutionalData { ticker: string; sections: Record<string, string>; quant_context: string }

interface DCFResult { base: number | null; bull: number | null; bear: number | null; current_price: number | null; scenarios: Record<string, { intrinsic_value: number | null; upside: number }> }
interface SensitivityResult { wacc_values: number[]; tg_values: number[]; matrix: (number | null)[][] }
interface MonteCarloResult { histogram: { counts: number[]; bin_edges: number[] }; mean: number | null; median: number | null; percentile_5: number | null; percentile_95: number | null; upside_pct: number | null; current_price: number | null }
interface TornadoItem { variable: string; low: number; high: number; base: number }
interface ReverseDCFResult { implied_growth: number | null; current_price: number | null }
interface ConsensusData { target_mean: number | null; target_high: number | null; target_low: number | null; target_median: number | null; recommendation: string; num_analysts: number }
interface PeerData { ticker: string; sector: string; industry: string; averages: Record<string, number | null>; peers: Record<string, any>[] }
interface EarningsHistory { date: string; eps_actual: number | null; eps_estimate: number | null; surprise: number }
interface QuarterlyEarnings { period: string; revenue: number | null; earnings: number | null }
interface HealthData { dupont: Record<string, number>; altman_z: number | null; current_ratio: number | null; interest_coverage: number | null; debt_to_equity: number | null; red_flags: string[] }
interface TechnicalData { [key: string]: any }

type ValuationTier = "dcf" | "ev_ebitda" | "ps_revenue" | "pb_nav";
interface RelativeValData {
  tier: ValuationTier;
  tierLabel: string;
  tierReason: string;
  method: string;
  multipleName: string;
  peerAvgMultiple: number;
  companyMetric: number;
  metricLabel: string;
  bear: { multiple: number; value: number };
  base: { multiple: number; value: number };
  bull: { multiple: number; value: number };
  netDebt: number;
  shares: number;
  cashRunwayQuarters: number | null;
  revenueGrowth: number | null;
  rule40: number | null;
  ebitda: number | null;
  fcf: number | null;
}

/* ═══════════════════════════════════════════════════════════════════
   Utility
   ═══════════════════════════════════════════════════════════════════ */
function fmtB(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "N/A";
  if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(1)}T`;
  if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(1)}B`;
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}
function fmtPct(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "N/A";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}
function fmtPrice(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "N/A";
  return `$${v.toFixed(2)}`;
}
function getValue(data: Record<string, any>, key: string): number | null {
  for (const k of key.split("|")) { const v = data[k.trim()]; if (v != null && typeof v === "number" && !isNaN(v)) return v; }
  return null;
}
async function fetchJson(url: string, opts?: RequestInit) {
  try { const r = await fetch(url, opts); return r.ok ? r.json() : null; } catch { return null; }
}
function renderMarkdown(text: string) {
  return text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n- /g, "<br/>&bull; ").replace(/\n\* /g, "<br/>&bull; ").replace(/\n/g, "<br/>");
}

/* ═══════════════════════════════════════════════════════════════════
   SECTION COMPONENTS
   ═══════════════════════════════════════════════════════════════════ */

function CoverPage({ ticker, info, consensus, dcf, relativeVal }: { ticker: string; info: Record<string, any>; consensus: ConsensusData | null; dcf: DCFResult | null; relativeVal: RelativeValData | null }) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const price = info.currentPrice || info.regularMarketPrice || 0;
  const target = consensus?.target_mean ?? info.targetMeanPrice ?? 0;
  const upside = price > 0 && target > 0 ? ((target - price) / price) * 100 : 0;
  const rec = consensus?.recommendation?.toUpperCase() || "N/A";
  const recColor = rec.includes("BUY") || rec.includes("STRONG") ? C.green : rec.includes("SELL") ? C.red : C.gold;

  return (
    <div className="report-page cover-page flex flex-col items-center justify-center text-center">
      <div className="mb-10">
        <div className="text-sm tracking-[0.3em] uppercase" style={{ color: C.gold }}>ATLAS TERMINAL</div>
        <div className="text-xs tracking-[0.2em] uppercase mt-1" style={{ color: C.muted }}>Institutional Equity Research</div>
      </div>
      <div className="w-24 h-px mb-10" style={{ background: C.gold }} />
      <h1 className="text-5xl font-serif font-bold mb-3" style={{ color: C.navy }}>{info.longName || ticker}</h1>
      <p className="text-xl mb-1" style={{ color: C.blue }}>{ticker} &mdash; {info.exchange || ""}</p>
      <p className="text-base mb-6" style={{ color: C.muted }}>{info.sector || ""} &bull; {info.industry || ""}</p>

      {/* Rating Badge */}
      <div className="inline-flex items-center gap-3 px-6 py-3 rounded-lg mb-8" style={{ background: "#F4F6F9", border: `2px solid ${recColor}` }}>
        <div className="text-xs uppercase tracking-wider" style={{ color: C.muted }}>Consensus</div>
        <div className="text-2xl font-bold font-mono" style={{ color: recColor }}>{rec}</div>
        <div className="w-px h-8" style={{ background: C.lightGray }} />
        <div className="text-right">
          <div className="text-xs" style={{ color: C.muted }}>Target</div>
          <div className="font-mono font-bold" style={{ color: C.navy }}>{fmtPrice(target)}</div>
        </div>
        <div className="text-right">
          <div className="text-xs" style={{ color: C.muted }}>Upside</div>
          <div className="font-mono font-bold" style={{ color: upside >= 0 ? C.green : C.red }}>{fmtPct(upside)}</div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6 mb-8" style={{ maxWidth: 640 }}>
        {[
          { label: "Price", value: fmtPrice(price) },
          { label: "Market Cap", value: fmtB(info.marketCap) },
          { label: relativeVal ? `${relativeVal.method} Fair Value` : "DCF Fair Value", value: relativeVal ? fmtPrice(relativeVal.base.value) : dcf?.base != null ? fmtPrice(dcf.base) : "N/A" },
          { label: "Analysts", value: consensus ? `${consensus.num_analysts}` : "N/A" },
        ].map((k) => (
          <div key={k.label}>
            <div className="text-xs uppercase tracking-wider" style={{ color: C.muted }}>{k.label}</div>
            <div className="text-xl font-mono font-bold" style={{ color: C.navy }}>{k.value}</div>
          </div>
        ))}
      </div>
      <div className="w-24 h-px my-6" style={{ background: C.gold }} />
      <p className="text-sm" style={{ color: C.muted }}>{dateStr}</p>
    </div>
  );
}

function TableOfContents({ hasInstitutional }: { hasInstitutional: boolean }) {
  const sections = [
    "Investment Snapshot & Key Metrics",
    "Company Profile",
    "Financial Performance",
    "Balance Sheet & Cash Flow",
    "Quality Assessment — F-Score & DuPont",
    "Operating Income Bridge",
    "YoY Anomalies",
    "Valuation — DCF 3-Scenario Analysis",
    "Sensitivity Matrix & Monte Carlo",
    "Peer Comparison",
    "Earnings Analysis",
    ...(hasInstitutional ? [
      "Executive Summary (AI)",
      "Goldman Sachs / Morgan Stanley / JP Morgan",
      "BlackRock / Bridgewater / Berkshire Hathaway",
      "Citadel / Two Sigma / Elliott Mgmt / ARK Invest",
    ] : []),
    "Disclaimer",
  ];
  return (
    <div className="report-page">
      <div className="page-header">Table of Contents</div>
      <div className="space-y-2 mt-4">
        {sections.map((s, i) => (
          <div key={i} className="flex items-center gap-2 text-sm" style={{ color: C.text }}>
            <span className="font-mono text-xs w-6 text-right" style={{ color: C.blue }}>{i + 1}.</span>
            <span className="flex-1">{s}</span>
            <span className="flex-1 border-b border-dotted" style={{ borderColor: C.lightGray }} />
            <span className="font-mono text-xs" style={{ color: C.muted }}>{i + 2}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function KpiRow({ info }: { info: Record<string, any> }) {
  const kpis = [
    { label: "Revenue", value: fmtB(info.totalRevenue), sub: fmtPct((info.revenueGrowth || 0) * 100) },
    { label: "Net Income", value: fmtB(info.netIncomeToCommon), sub: `Margin ${((info.profitMargins || 0) * 100).toFixed(1)}%` },
    { label: "Free Cash Flow", value: fmtB(info.freeCashflow), sub: `Yield ${info.freeCashflow && info.marketCap ? ((info.freeCashflow / info.marketCap) * 100).toFixed(1) : "N/A"}%` },
    { label: "ROE", value: `${((info.returnOnEquity || 0) * 100).toFixed(1)}%`, sub: `ROA ${((info.returnOnAssets || 0) * 100).toFixed(1)}%` },
    { label: "P/E (TTM)", value: info.trailingPE ? `${info.trailingPE.toFixed(1)}x` : "N/A", sub: `Fwd ${info.forwardPE ? info.forwardPE.toFixed(1) + "x" : "N/A"}` },
    { label: "EV/EBITDA", value: info.enterpriseToEbitda ? `${info.enterpriseToEbitda.toFixed(1)}x` : "N/A", sub: `D/E ${info.debtToEquity ?? "N/A"}` },
  ];
  return (
    <div className="grid grid-cols-6 gap-3 mb-6">
      {kpis.map((k) => (
        <div key={k.label} className="text-center p-3 rounded" style={{ background: "#F4F6F9" }}>
          <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: C.muted }}>{k.label}</div>
          <div className="text-lg font-mono font-bold" style={{ color: C.navy }}>{k.value}</div>
          <div className="text-[10px]" style={{ color: C.blue }}>{k.sub}</div>
        </div>
      ))}
    </div>
  );
}

function CompanyProfile({ info }: { info: Record<string, any> }) {
  const desc = info.longBusinessSummary || info.description || "";
  if (!desc) return null;
  const stats = [
    { l: "Employees", v: info.fullTimeEmployees?.toLocaleString() || "N/A" },
    { l: "Country", v: info.country || "N/A" },
    { l: "Founded", v: info.companyOfficers?.[0]?.fiscalYear || "N/A" },
    { l: "52W High", v: fmtPrice(info.fiftyTwoWeekHigh) },
    { l: "52W Low", v: fmtPrice(info.fiftyTwoWeekLow) },
    { l: "Beta", v: info.beta ? info.beta.toFixed(2) : "N/A" },
    { l: "Avg Volume", v: info.averageVolume ? `${(info.averageVolume / 1e6).toFixed(1)}M` : "N/A" },
    { l: "Dividend Yield", v: info.dividendYield ? `${(info.dividendYield * 100).toFixed(2)}%` : "N/A" },
  ];
  return (
    <div className="report-section">
      <h2 className="section-title">Company Profile</h2>
      <p className="text-xs leading-relaxed mb-4" style={{ color: C.text }}>{desc.length > 800 ? desc.slice(0, 800) + "..." : desc}</p>
      <div className="grid grid-cols-4 gap-x-6 gap-y-2">
        {stats.map((s) => (
          <div key={s.l} className="flex justify-between text-xs border-b py-1" style={{ borderColor: C.lightGray }}>
            <span style={{ color: C.muted }}>{s.l}</span>
            <span className="font-mono" style={{ color: C.navy }}>{s.v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FinancialCharts({ statements }: { statements: { income_statement?: FinancialPeriod[]; balance_sheet?: FinancialPeriod[]; cash_flow?: FinancialPeriod[] } }) {
  const is = statements.income_statement;
  if (!is || is.length === 0) return null;

  const chartData = is.slice(0, 5).reverse().map((p) => {
    const rev = getValue(p, "TotalRevenue|Total Revenue|Revenue");
    const ni = getValue(p, "NetIncome|Net Income|Net Income Common Stockholders");
    const gp = getValue(p, "GrossProfit|Gross Profit");
    const op = getValue(p, "OperatingIncome|Operating Income");
    const yr = p.asOfDate || p.fiscalYear || p.year || "";
    return {
      year: typeof yr === "string" ? yr.slice(0, 4) : String(yr),
      revenue: rev ? rev / 1e9 : 0, netIncome: ni ? ni / 1e9 : 0,
      grossMargin: rev && gp ? (gp / rev) * 100 : 0,
      opMargin: rev && op ? (op / rev) * 100 : 0,
      netMargin: rev && ni ? (ni / rev) * 100 : 0,
    };
  });

  return (
    <div className="report-section">
      <h2 className="section-title">Income Statement Trends</h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="chart-title">Revenue & Net Income ($B)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="revenue" fill={C.blue} name="Revenue" radius={[2, 2, 0, 0]} />
              <Bar dataKey="netIncome" fill={C.gold} name="Net Income" radius={[2, 2, 0, 0]} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <h3 className="chart-title">Margin Trends (%)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Line type="monotone" dataKey="grossMargin" stroke={C.green} name="Gross" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="opMargin" stroke={C.blue} name="Operating" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="netMargin" stroke={C.gold} name="Net" strokeWidth={2} dot={{ r: 3 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function BalanceSheetCashFlow({ statements }: { statements: { balance_sheet?: FinancialPeriod[]; cash_flow?: FinancialPeriod[] } }) {
  const bs = statements.balance_sheet;
  const cf = statements.cash_flow;
  if ((!bs || bs.length === 0) && (!cf || cf.length === 0)) return null;

  const bsData = (bs || []).slice(0, 5).reverse().map((p) => {
    const ta = getValue(p, "TotalAssets|Total Assets");
    const tl = getValue(p, "TotalLiabilitiesNetMinorityInterest|Total Liabilities Net Minority Interest|TotalLiab|Total Liabilities");
    const te = getValue(p, "StockholdersEquity|Stockholders Equity|TotalStockholderEquity|Total Stockholder Equity");
    const cash = getValue(p, "CashAndCashEquivalents|Cash And Cash Equivalents|CashCashEquivalentsAndShortTermInvestments");
    const yr = p.asOfDate || p.fiscalYear || "";
    return { year: typeof yr === "string" ? yr.slice(0, 4) : String(yr), assets: ta ? ta / 1e9 : 0, liabilities: tl ? tl / 1e9 : 0, equity: te ? te / 1e9 : 0, cash: cash ? cash / 1e9 : 0 };
  });

  const cfData = (cf || []).slice(0, 5).reverse().map((p) => {
    const ocf = getValue(p, "OperatingCashFlow|Operating Cash Flow|CashFlowFromContinuingOperatingActivities");
    const capex = getValue(p, "CapitalExpenditure|Capital Expenditure");
    const fcf = getValue(p, "FreeCashFlow|Free Cash Flow") ?? (ocf != null && capex != null ? ocf + capex : null);
    const yr = p.asOfDate || p.fiscalYear || "";
    return { year: typeof yr === "string" ? yr.slice(0, 4) : String(yr), ocf: ocf ? ocf / 1e9 : 0, capex: capex ? Math.abs(capex) / 1e9 : 0, fcf: fcf ? fcf / 1e9 : 0 };
  });

  return (
    <div className="report-section">
      <div className="grid grid-cols-2 gap-6">
        {bsData.length > 0 && (
          <div>
            <h3 className="chart-title">Balance Sheet ($B)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={bsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="assets" fill={C.blue} name="Total Assets" radius={[2, 2, 0, 0]} />
                <Bar dataKey="equity" fill={C.green} name="Equity" radius={[2, 2, 0, 0]} />
                <Bar dataKey="cash" fill={C.gold} name="Cash" radius={[2, 2, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {cfData.length > 0 && (
          <div>
            <h3 className="chart-title">Cash Flow ($B)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={cfData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="year" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="ocf" fill={C.blue} name="Operating CF" radius={[2, 2, 0, 0]} />
                <Bar dataKey="fcf" fill={C.green} name="Free CF" radius={[2, 2, 0, 0]} />
                <Bar dataKey="capex" fill={C.red} name="CapEx" radius={[2, 2, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

function QualityScores({ research, health }: { research: ResearchDash | null; health: HealthData | null }) {
  if (!research && !health) return null;
  const { fscore_total = 0, fscore_criteria = [], dupont_tree } = research || {};
  const altmanZ = health?.altman_z;
  const zLabel = altmanZ == null ? "N/A" : altmanZ > 2.99 ? "Safe" : altmanZ > 1.81 ? "Gray Zone" : "Distress";
  const zColor = altmanZ == null ? C.muted : altmanZ > 2.99 ? C.green : altmanZ > 1.81 ? C.gold : C.red;

  return (
    <div className="report-section">
      <h2 className="section-title">Quality Assessment</h2>
      <div className="grid grid-cols-3 gap-6">
        {/* F-Score */}
        <div>
          <h3 className="chart-title">Piotroski F-Score: {fscore_total}/9</h3>
          <div className="flex items-center gap-1 mb-3">
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} className="h-6 flex-1 rounded-sm flex items-center justify-center text-[10px] font-bold"
                style={{ background: i < fscore_total ? C.green : "#E8ECF0", color: i < fscore_total ? "#fff" : C.muted }}>
                {i + 1}
              </div>
            ))}
          </div>
          <div className="space-y-0.5">
            {fscore_criteria.map((c) => (
              <div key={c.key} className="flex items-center gap-2 text-[11px]">
                <span style={{ color: c.history[0]?.pass_flag ? C.green : C.red }}>{c.history[0]?.pass_flag ? "\u2713" : "\u2717"}</span>
                <span style={{ color: C.text }}>{c.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Altman Z + Risk */}
        <div>
          <h3 className="chart-title">Financial Health</h3>
          <div className="p-4 rounded mb-3" style={{ background: "#F4F6F9" }}>
            <div className="text-center mb-2">
              <div className="text-[10px] uppercase" style={{ color: C.muted }}>Altman Z-Score</div>
              <div className="text-3xl font-mono font-bold" style={{ color: zColor }}>{altmanZ?.toFixed(2) ?? "N/A"}</div>
              <div className="text-[10px] font-bold" style={{ color: zColor }}>{zLabel}</div>
            </div>
            <div className="space-y-1 mt-3">
              {[
                { l: "Current Ratio", v: health?.current_ratio?.toFixed(2) },
                { l: "Interest Coverage", v: health?.interest_coverage?.toFixed(1) },
                { l: "Debt/Equity", v: health?.debt_to_equity?.toFixed(2) },
              ].map((r) => (
                <div key={r.l} className="flex justify-between text-[11px]">
                  <span style={{ color: C.muted }}>{r.l}</span>
                  <span className="font-mono" style={{ color: C.navy }}>{r.v ?? "N/A"}</span>
                </div>
              ))}
            </div>
          </div>
          {health?.red_flags && health.red_flags.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-bold mb-1" style={{ color: C.red }}>Red Flags</div>
              {health.red_flags.slice(0, 4).map((f, i) => (
                <div key={i} className="text-[10px] mb-0.5" style={{ color: C.red }}>&bull; {f}</div>
              ))}
            </div>
          )}
        </div>

        {/* DuPont */}
        {dupont_tree && (
          <div>
            <h3 className="chart-title">DuPont ROE Decomposition</h3>
            <div className="p-4 rounded" style={{ background: "#F4F6F9" }}>
              <div className="text-center mb-3">
                <div className="text-[10px] uppercase" style={{ color: C.muted }}>Return on Equity</div>
                <div className="text-3xl font-mono font-bold" style={{ color: C.navy }}>{dupont_tree.root.value.toFixed(1)}%</div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                {[
                  { label: "Net Margin", val: `${dupont_tree.npm.value.toFixed(1)}%`, trend: dupont_tree.npm.trend },
                  { label: "Asset T/O", val: `${dupont_tree.asset_turnover.value.toFixed(2)}x`, trend: dupont_tree.asset_turnover.trend },
                  { label: "Equity Mult", val: `${dupont_tree.equity_mult.value.toFixed(2)}x`, trend: dupont_tree.equity_mult.trend },
                ].map((d) => (
                  <div key={d.label} className="p-2 rounded" style={{ background: "#fff" }}>
                    <div className="text-[9px] uppercase" style={{ color: C.muted }}>{d.label}</div>
                    <div className="text-sm font-mono font-bold" style={{ color: C.navy }}>{d.val}</div>
                    <div className="text-[9px]" style={{ color: d.trend === "up" ? C.green : d.trend === "down" ? C.red : C.muted }}>
                      {d.trend === "up" ? "\u25B2" : d.trend === "down" ? "\u25BC" : "\u25C6"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function WaterfallChart({ waterfall }: { waterfall: ResearchDash["waterfall"] }) {
  if (!waterfall || waterfall.length === 0) return null;
  const data = waterfall.map((w) => ({ name: w.label.length > 14 ? w.label.slice(0, 14) + ".." : w.label, value: w.value / 1e9, fill: w.step_type === "total" ? C.navy : w.value >= 0 ? C.green : C.red }));
  return (
    <div className="report-section">
      <h2 className="section-title">Operating Income Bridge ($B)</h2>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-20} textAnchor="end" height={50} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>{data.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function AnomalyTable({ anomalies }: { anomalies: ResearchDash["anomalies"] }) {
  if (!anomalies || anomalies.length === 0) return null;
  return (
    <div className="report-section">
      <h2 className="section-title">YoY Anomalies (&gt;30% Change)</h2>
      <table className="w-full text-xs">
        <thead>
          <tr style={{ borderBottom: `2px solid ${C.navy}` }}>
            <th className="text-left py-1.5">Line Item</th>
            <th className="text-right py-1.5">YoY Change</th>
            <th className="text-center py-1.5">Direction</th>
          </tr>
        </thead>
        <tbody>
          {anomalies.slice(0, 12).map((a) => (
            <tr key={a.account_key} style={{ borderBottom: `1px solid ${C.lightGray}` }}>
              <td className="py-1" style={{ color: C.text }}>{a.display_name}</td>
              <td className="text-right font-mono" style={{ color: a.direction === "up" ? C.green : C.red }}>{a.change_pct != null ? `${a.change_pct > 0 ? "+" : ""}${a.change_pct.toFixed(1)}%` : "N/A"}</td>
              <td className="text-center">{a.direction === "up" ? "\u25B2" : "\u25BC"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Valuation Section ── */
function DCFValuationSection({ dcf, reverseDcf, info }: { dcf: DCFResult | null; reverseDcf: ReverseDCFResult | null; info: Record<string, any> }) {
  if (!dcf) return null;
  const price = dcf.current_price || info.currentPrice || 0;
  const scenarios = [
    { label: "Bear", value: dcf.bear, color: C.red, upside: dcf.scenarios?.bear?.upside },
    { label: "Base", value: dcf.base, color: C.blue, upside: dcf.scenarios?.base?.upside },
    { label: "Bull", value: dcf.bull, color: C.green, upside: dcf.scenarios?.bull?.upside },
  ];
  const chartData = scenarios.map((s) => ({ name: s.label, value: s.value || 0, fill: s.color }));

  return (
    <div className="report-section">
      <h2 className="section-title">DCF 3-Scenario Valuation</h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={50} />
              <Tooltip formatter={(v: number) => fmtPrice(v)} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>{chartData.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar>
              {price > 0 && <ReferenceLine x={price} stroke={C.gold} strokeWidth={2} strokeDasharray="5 5" label={{ value: `Current $${price.toFixed(0)}`, fill: C.gold, fontSize: 10 }} />}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div>
          <div className="space-y-3">
            {scenarios.map((s) => (
              <div key={s.label} className="flex items-center justify-between p-3 rounded" style={{ background: "#F4F6F9" }}>
                <div>
                  <div className="text-xs font-bold" style={{ color: s.color }}>{s.label} Case</div>
                  <div className="text-xl font-mono font-bold" style={{ color: C.navy }}>{s.value != null ? fmtPrice(s.value) : "N/A"}</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px]" style={{ color: C.muted }}>vs Current</div>
                  <div className="font-mono font-bold" style={{ color: s.upside != null && s.upside >= 0 ? C.green : C.red }}>
                    {s.upside != null ? fmtPct(s.upside) : "N/A"}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {reverseDcf?.implied_growth != null && (
            <div className="mt-3 p-3 rounded text-center" style={{ background: "#F4F6F9", borderLeft: `3px solid ${C.gold}` }}>
              <div className="text-[10px] uppercase" style={{ color: C.muted }}>Market Implied Growth Rate (Reverse DCF)</div>
              <div className="text-2xl font-mono font-bold" style={{ color: C.navy }}>{reverseDcf.implied_growth.toFixed(1)}%</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SensitivityHeatmap({ sensitivity, currentPrice }: { sensitivity: SensitivityResult | null; currentPrice: number }) {
  if (!sensitivity || !sensitivity.matrix || sensitivity.matrix.length === 0) return null;
  const { wacc_values, tg_values, matrix } = sensitivity;
  const getColor = (v: number | null) => {
    if (v == null) return C.lightGray;
    const diff = currentPrice > 0 ? (v - currentPrice) / currentPrice : 0;
    if (diff > 0.3) return "#1a7a3e";
    if (diff > 0.1) return "#4CAF50";
    if (diff > -0.1) return "#FFF9C4";
    if (diff > -0.3) return "#FF8A65";
    return "#E53935";
  };
  return (
    <div className="report-section">
      <h2 className="section-title">Sensitivity Matrix — WACC vs Terminal Growth</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th className="p-1.5 font-bold" style={{ color: C.navy, background: "#F4F6F9" }}>WACC \ TG</th>
              {tg_values.map((tg) => (
                <th key={tg} className="p-1.5 text-center font-bold" style={{ color: C.navy, background: "#F4F6F9" }}>{tg.toFixed(1)}%</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, ri) => (
              <tr key={ri}>
                <td className="p-1.5 font-bold" style={{ color: C.navy, background: "#F4F6F9" }}>{wacc_values[ri]?.toFixed(1)}%</td>
                {row.map((cell, ci) => (
                  <td key={ci} className="p-1.5 text-center font-mono font-bold" style={{ background: getColor(cell), color: cell != null && Math.abs((cell - currentPrice) / currentPrice) > 0.1 ? "#fff" : C.navy }}>
                    {cell != null ? `$${cell.toFixed(0)}` : "-"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[9px] mt-2 text-center" style={{ color: C.muted }}>Green = above current price ({fmtPrice(currentPrice)}), Red = below current price</p>
    </div>
  );
}

function MonteCarloSection({ mc }: { mc: MonteCarloResult | null }) {
  if (!mc || !mc.histogram) return null;
  const { counts, bin_edges } = mc.histogram;
  const data = counts.map((c, i) => ({
    range: `$${bin_edges[i]?.toFixed(0)}`,
    count: c,
    fill: mc.current_price != null && bin_edges[i] != null && bin_edges[i]! >= mc.current_price ? C.green : C.red,
  }));
  return (
    <div className="report-section">
      <h2 className="section-title">Monte Carlo Simulation (5,000 runs)</h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="range" tick={{ fontSize: 8 }} interval={Math.floor(data.length / 8)} angle={-30} textAnchor="end" height={45} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" name="Frequency">{data.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar>
              {mc.current_price != null && <ReferenceLine x={`$${mc.current_price.toFixed(0)}`} stroke={C.gold} strokeWidth={2} />}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {[
            { l: "Mean Value", v: fmtPrice(mc.mean) },
            { l: "Median Value", v: fmtPrice(mc.median) },
            { l: "5th Percentile", v: fmtPrice(mc.percentile_5) },
            { l: "95th Percentile", v: fmtPrice(mc.percentile_95) },
            { l: "Current Price", v: fmtPrice(mc.current_price) },
            { l: "P(Upside)", v: mc.upside_pct != null ? `${mc.upside_pct.toFixed(1)}%` : "N/A" },
          ].map((s) => (
            <div key={s.l} className="p-3 rounded text-center" style={{ background: "#F4F6F9" }}>
              <div className="text-[9px] uppercase" style={{ color: C.muted }}>{s.l}</div>
              <div className="text-sm font-mono font-bold" style={{ color: C.navy }}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TornadoSection({ tornado }: { tornado: TornadoItem[] | null }) {
  if (!tornado || tornado.length === 0) return null;
  const data = tornado.slice(0, 6).map((t) => ({ name: t.variable, low: t.low - t.base, high: t.high - t.base }));
  return (
    <div className="report-section">
      <h2 className="section-title">Tornado Sensitivity (&plusmn;10% Variable Shift)</h2>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
          <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v > 0 ? "+" : ""}${v.toFixed(0)}`} />
          <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={90} />
          <Tooltip formatter={(v: number) => `$${v > 0 ? "+" : ""}${v.toFixed(2)}`} />
          <Bar dataKey="low" fill={C.red} name="−10%" stackId="a" />
          <Bar dataKey="high" fill={C.green} name="+10%" stackId="a" />
          <Legend wrapperStyle={{ fontSize: 10 }} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function PeerComparisonSection({ peers }: { peers: PeerData | null }) {
  if (!peers || !peers.peers || peers.peers.length === 0) return null;
  return (
    <div className="report-section">
      <h2 className="section-title">Peer Valuation Comparison — {peers.sector} / {peers.industry}</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${C.navy}` }}>
              {["Ticker", "Mkt Cap", "Trailing P/E", "Forward P/E", "P/B", "P/S", "EV/EBITDA"].map((h) => (
                <th key={h} className="py-1.5 px-2 text-right first:text-left font-bold" style={{ color: C.navy }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {peers.peers.slice(0, 10).map((p, i) => {
              const isSelf = p.ticker === peers.ticker;
              return (
                <tr key={i} style={{ borderBottom: `1px solid ${C.lightGray}`, background: isSelf ? "#F0F7FF" : "transparent" }}>
                  <td className="py-1 px-2 font-mono font-bold" style={{ color: isSelf ? C.blue : C.navy }}>{p.ticker}</td>
                  <td className="py-1 px-2 text-right font-mono">{fmtB(p.market_cap)}</td>
                  <td className="py-1 px-2 text-right font-mono">{p.trailing_pe != null ? `${p.trailing_pe.toFixed(1)}x` : "-"}</td>
                  <td className="py-1 px-2 text-right font-mono">{p.forward_pe != null ? `${p.forward_pe.toFixed(1)}x` : "-"}</td>
                  <td className="py-1 px-2 text-right font-mono">{p.pb != null ? `${p.pb.toFixed(1)}x` : "-"}</td>
                  <td className="py-1 px-2 text-right font-mono">{p.ps != null ? `${p.ps.toFixed(1)}x` : "-"}</td>
                  <td className="py-1 px-2 text-right font-mono">{p.ev_ebitda != null ? `${p.ev_ebitda.toFixed(1)}x` : "-"}</td>
                </tr>
              );
            })}
            {/* Averages */}
            <tr style={{ borderTop: `2px solid ${C.navy}` }}>
              <td className="py-1.5 px-2 font-bold" style={{ color: C.gold }}>Avg</td>
              <td className="py-1.5 px-2" />
              <td className="py-1.5 px-2 text-right font-mono font-bold" style={{ color: C.gold }}>{peers.averages.pe != null ? `${peers.averages.pe.toFixed(1)}x` : "-"}</td>
              <td className="py-1.5 px-2" />
              <td className="py-1.5 px-2 text-right font-mono font-bold" style={{ color: C.gold }}>{peers.averages.pb != null ? `${peers.averages.pb.toFixed(1)}x` : "-"}</td>
              <td className="py-1.5 px-2 text-right font-mono font-bold" style={{ color: C.gold }}>{peers.averages.ps != null ? `${peers.averages.ps.toFixed(1)}x` : "-"}</td>
              <td className="py-1.5 px-2 text-right font-mono font-bold" style={{ color: C.gold }}>{peers.averages.ev_ebitda != null ? `${peers.averages.ev_ebitda.toFixed(1)}x` : "-"}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EarningsSection({ history, quarterly }: { history: EarningsHistory[] | null; quarterly: QuarterlyEarnings[] | null }) {
  if ((!history || history.length === 0) && (!quarterly || quarterly.length === 0)) return null;

  const epsData = (history || []).slice(0, 12).reverse().map((h) => ({
    date: h.date?.slice(0, 7) || "",
    actual: h.eps_actual, estimate: h.eps_estimate,
    surprise: h.surprise,
    fill: h.surprise >= 0 ? C.green : C.red,
  }));

  const qData = (quarterly || []).slice(0, 8).reverse().map((q) => ({
    period: q.period?.slice(0, 7) || "",
    revenue: q.revenue ? q.revenue / 1e9 : 0,
    earnings: q.earnings ? q.earnings / 1e9 : 0,
  }));

  const beatCount = epsData.filter((d) => d.surprise >= 0).length;
  const beatRate = epsData.length > 0 ? (beatCount / epsData.length * 100).toFixed(0) : "N/A";

  return (
    <div className="report-section">
      <h2 className="section-title">Earnings Analysis</h2>
      <div className="grid grid-cols-2 gap-6">
        {epsData.length > 0 && (
          <div>
            <h3 className="chart-title">EPS Beat/Miss History (Beat Rate: {beatRate}%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={epsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="date" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" height={40} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="actual" name="Actual EPS" radius={[2, 2, 0, 0]}>
                  {epsData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Bar>
                <Bar dataKey="estimate" fill="transparent" stroke={C.navy} strokeWidth={1} name="Estimate" radius={[2, 2, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
        {qData.length > 0 && (
          <div>
            <h3 className="chart-title">Quarterly Revenue & Earnings ($B)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={qData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
                <XAxis dataKey="period" tick={{ fontSize: 9 }} angle={-30} textAnchor="end" height={40} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="revenue" fill={C.blue} name="Revenue" radius={[2, 2, 0, 0]} />
                <Bar dataKey="earnings" fill={C.gold} name="Earnings" radius={[2, 2, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

function TechnicalSnapshot({ technical, info }: { technical: TechnicalData | null; info: Record<string, any> }) {
  if (!technical) return null;
  const rsi = typeof technical.rsi_14 === "number" ? technical.rsi_14 : null;
  const sma50 = technical.sma?.sma_50 ?? null;
  const sma200 = technical.sma?.sma_200 ?? null;
  const macdVal = typeof technical.macd === "object" ? technical.macd?.macd : technical.macd;
  const macdSig = typeof technical.macd === "object" ? technical.macd?.signal : technical.macd_signal;
  const bbUpper = technical.bollinger_bands?.upper ?? technical.bb_upper ?? null;
  const bbLower = technical.bollinger_bands?.lower ?? technical.bb_lower ?? null;
  const atr = typeof technical.atr_14 === "number" ? technical.atr_14 : typeof technical.atr === "number" ? technical.atr : null;

  const metrics = [
    { l: "RSI (14)", v: rsi?.toFixed(1), color: rsi != null && rsi > 70 ? C.red : rsi != null && rsi < 30 ? C.green : C.navy },
    { l: "SMA 50", v: fmtPrice(sma50), color: C.navy },
    { l: "SMA 200", v: fmtPrice(sma200), color: C.navy },
    { l: "MACD", v: typeof macdVal === "number" ? macdVal.toFixed(3) : "N/A", color: typeof macdVal === "number" && macdVal > 0 ? C.green : C.red },
    { l: "Signal", v: typeof macdSig === "number" ? macdSig.toFixed(3) : "N/A", color: C.muted },
    { l: "BB Upper", v: fmtPrice(bbUpper), color: C.navy },
    { l: "BB Lower", v: fmtPrice(bbLower), color: C.navy },
    { l: "ATR", v: typeof atr === "number" ? atr.toFixed(2) : "N/A", color: C.navy },
  ];
  const price = info.currentPrice || info.regularMarketPrice || 0;
  const trend = sma50 && sma200 && sma50 > sma200 ? "Bullish (Golden Cross)" : sma50 && sma200 ? "Bearish (Death Cross)" : "Neutral";
  const trendColor = trend.includes("Bullish") ? C.green : trend.includes("Bearish") ? C.red : C.gold;

  return (
    <div className="report-section">
      <h2 className="section-title">Technical Summary</h2>
      <div className="grid grid-cols-2 gap-6">
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          {metrics.map((m) => (
            <div key={m.l} className="flex justify-between text-xs py-1 border-b" style={{ borderColor: C.lightGray }}>
              <span style={{ color: C.muted }}>{m.l}</span>
              <span className="font-mono font-bold" style={{ color: m.color }}>{m.v ?? "N/A"}</span>
            </div>
          ))}
        </div>
        <div className="p-4 rounded" style={{ background: "#F4F6F9" }}>
          <div className="text-center">
            <div className="text-[10px] uppercase mb-1" style={{ color: C.muted }}>Overall Trend</div>
            <div className="text-lg font-bold mb-3" style={{ color: trendColor }}>{trend}</div>
            <div className="text-xs" style={{ color: C.text }}>
              Price {fmtPrice(price)} is {price > (sma50 || 0) ? "above" : "below"} SMA50 ({fmtPrice(sma50)})
              and {price > (sma200 || 0) ? "above" : "below"} SMA200 ({fmtPrice(sma200)})
            </div>
            <div className="text-xs mt-2" style={{ color: C.text }}>
              RSI at {rsi?.toFixed(1) ?? "N/A"} — {rsi != null && rsi > 70 ? "Overbought" : rsi != null && rsi < 30 ? "Oversold" : "Neutral"}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Valuation Tier Detection ── */
function detectValuationTier(fcf: number | null, ebitda: number | null, revenueGrowth: number | null): ValuationTier {
  if (fcf != null && fcf > 0) return "dcf";
  if (ebitda != null && ebitda > 0) return "ev_ebitda";
  if (revenueGrowth != null && revenueGrowth > 0.10) return "ps_revenue";
  return "pb_nav";
}

function buildRelativeVal(
  tier: ValuationTier, peers: PeerData | null, info: Record<string, any>,
  di: { fcf: number; total_debt: number; cash: number; shares: number } | null, hi: any,
): RelativeValData | null {
  if (!di || !di.shares || di.shares <= 0) return null;
  const netDebt = (di.total_debt || 0) - (di.cash || 0);
  const revenue = hi?.revenue || info.totalRevenue || 0;
  const ebitda = hi?.ebitda || 0;
  const fcf = hi?.free_cash_flow ?? info.freeCashflow ?? di.fcf ?? 0;
  const revGrowth = hi?.revenue_growth ?? info.revenueGrowth ?? null;
  const profitMargin = hi?.profit_margin ?? info.profitMargins ?? 0;
  const rule40 = revGrowth != null ? (revGrowth * 100) + (profitMargin * 100) : null;
  const cash = di.cash || 0;
  const qBurn = fcf < 0 ? Math.abs(fcf) / 4 : 0;
  const cashRunway = qBurn > 0 ? cash / qBurn : null;

  if (tier === "ev_ebitda") {
    const peerAvg = peers?.averages?.ev_ebitda ?? 12;
    const impliedEV = peerAvg * ebitda;
    const baseVal = (impliedEV - netDebt) / di.shares;
    return {
      tier, tierLabel: "EV/EBITDA Relative Valuation",
      tierReason: "Free cash flow is negative due to heavy capital investment, but EBITDA is positive — the company generates operating profit before reinvestment.",
      method: "EV/EBITDA", multipleName: "EV/EBITDA", peerAvgMultiple: peerAvg,
      companyMetric: ebitda, metricLabel: "EBITDA",
      bear: { multiple: peerAvg * 0.7, value: (peerAvg * 0.7 * ebitda - netDebt) / di.shares },
      base: { multiple: peerAvg, value: baseVal },
      bull: { multiple: peerAvg * 1.3, value: (peerAvg * 1.3 * ebitda - netDebt) / di.shares },
      netDebt, shares: di.shares, cashRunwayQuarters: cashRunway, revenueGrowth: revGrowth, rule40, ebitda, fcf,
    };
  }
  if (tier === "ps_revenue") {
    const peerAvg = peers?.averages?.ps ?? 4;
    const impliedMC = peerAvg * revenue;
    const baseVal = impliedMC / di.shares;
    return {
      tier, tierLabel: "Price/Sales Relative Valuation",
      tierReason: "Both FCF and EBITDA are negative, but revenue is growing rapidly. P/S (Price-to-Sales) multiple is the appropriate valuation framework for high-growth, pre-profit companies.",
      method: "P/S", multipleName: "P/S", peerAvgMultiple: peerAvg,
      companyMetric: revenue, metricLabel: "Revenue",
      bear: { multiple: peerAvg * 0.6, value: (peerAvg * 0.6 * revenue) / di.shares },
      base: { multiple: peerAvg, value: baseVal },
      bull: { multiple: peerAvg * 1.5, value: (peerAvg * 1.5 * revenue) / di.shares },
      netDebt, shares: di.shares, cashRunwayQuarters: cashRunway, revenueGrowth: revGrowth, rule40, ebitda, fcf,
    };
  }
  // pb_nav
  const bookVal = hi?.book_value || 0;
  const peerAvg = peers?.averages?.pb ?? 2;
  const baseVal = bookVal > 0 ? bookVal * peerAvg : 0;
  return {
    tier, tierLabel: "Price/Book (NAV) Valuation",
    tierReason: "FCF, EBITDA, and revenue growth are all weak or negative. Asset-based valuation (P/B) provides the most relevant framework.",
    method: "P/B", multipleName: "P/B", peerAvgMultiple: peerAvg,
    companyMetric: bookVal * di.shares, metricLabel: "Book Value",
    bear: { multiple: peerAvg * 0.6, value: bookVal * peerAvg * 0.6 },
    base: { multiple: peerAvg, value: baseVal },
    bull: { multiple: peerAvg * 1.5, value: bookVal * peerAvg * 1.5 },
    netDebt, shares: di.shares, cashRunwayQuarters: cashRunway, revenueGrowth: revGrowth, rule40, ebitda, fcf,
  };
}

/* ── Relative Valuation Section ── */
function RelativeValuationSection({ rv, info }: { rv: RelativeValData; info: Record<string, any> }) {
  const price = info.currentPrice || 0;
  const scenarios = [
    { label: "Bear", ...rv.bear, color: C.red },
    { label: "Base", ...rv.base, color: C.blue },
    { label: "Bull", ...rv.bull, color: C.green },
  ];
  const chartData = scenarios.map((s) => ({ name: `${s.label} (${s.multiple.toFixed(1)}x)`, value: Math.max(s.value, 0), fill: s.color }));

  return (
    <div className="report-section">
      {/* Tier Banner */}
      <div className="p-3 rounded mb-4" style={{ background: "#FFF8E1", borderLeft: `4px solid ${C.gold}` }}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm">&#9888;</span>
          <span className="text-xs font-bold" style={{ color: C.navy }}>DCF Not Applicable — {rv.tierLabel}</span>
        </div>
        <p className="text-[10px] leading-relaxed" style={{ color: C.text }}>{rv.tierReason}</p>
      </div>

      <h2 className="section-title">{rv.method} Scenario Analysis</h2>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h3 className="chart-title">Peer Avg {rv.multipleName}: {rv.peerAvgMultiple.toFixed(1)}x &bull; {rv.metricLabel}: {fmtB(rv.companyMetric)}</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v.toFixed(0)}`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 9 }} width={100} />
              <Tooltip formatter={(v: number) => fmtPrice(v)} />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>{chartData.map((d, i) => <Cell key={i} fill={d.fill} />)}</Bar>
              {price > 0 && <ReferenceLine x={price} stroke={C.gold} strokeWidth={2} strokeDasharray="5 5" label={{ value: `Current $${price.toFixed(0)}`, fill: C.gold, fontSize: 10 }} />}
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-3">
          {scenarios.map((s) => {
            const upside = price > 0 ? ((s.value - price) / price) * 100 : 0;
            return (
              <div key={s.label} className="flex items-center justify-between p-3 rounded" style={{ background: "#F4F6F9" }}>
                <div>
                  <div className="text-xs font-bold" style={{ color: s.color }}>{s.label} ({s.multiple.toFixed(1)}x)</div>
                  <div className="text-xl font-mono font-bold" style={{ color: C.navy }}>{fmtPrice(Math.max(s.value, 0))}</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px]" style={{ color: C.muted }}>vs Current</div>
                  <div className="font-mono font-bold" style={{ color: upside >= 0 ? C.green : C.red }}>{fmtPct(upside)}</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── Path to Profitability ── */
function PathToProfitability({ rv, stmts }: { rv: RelativeValData; stmts: { income_statement?: FinancialPeriod[] } }) {
  const is = stmts.income_statement;
  // Compute margin trends from statements
  const marginData = (is || []).slice(0, 5).reverse().map((p) => {
    const rev = getValue(p, "TotalRevenue|Total Revenue|Revenue");
    const gp = getValue(p, "GrossProfit|Gross Profit");
    const op = getValue(p, "OperatingIncome|Operating Income");
    const ni = getValue(p, "NetIncome|Net Income|Net Income Common Stockholders");
    const yr = p.asOfDate || p.fiscalYear || "";
    return {
      year: typeof yr === "string" ? yr.slice(0, 4) : String(yr),
      grossMargin: rev && gp ? (gp / rev) * 100 : null,
      opMargin: rev && op ? (op / rev) * 100 : null,
      netMargin: rev && ni ? (ni / rev) * 100 : null,
    };
  });

  const kpis = [
    { l: "FCF (TTM)", v: fmtB(rv.fcf), color: (rv.fcf ?? 0) >= 0 ? C.green : C.red },
    { l: "EBITDA (TTM)", v: fmtB(rv.ebitda), color: (rv.ebitda ?? 0) > 0 ? C.green : C.red },
    { l: "Revenue Growth", v: rv.revenueGrowth != null ? fmtPct(rv.revenueGrowth * 100) : "N/A", color: (rv.revenueGrowth ?? 0) > 0 ? C.green : C.red },
    { l: "Rule of 40", v: rv.rule40 != null ? rv.rule40.toFixed(1) : "N/A", color: (rv.rule40 ?? 0) >= 40 ? C.green : (rv.rule40 ?? 0) >= 20 ? C.gold : C.red },
    { l: "Cash Runway", v: rv.cashRunwayQuarters != null ? `${rv.cashRunwayQuarters.toFixed(1)} Q` : "N/A", color: (rv.cashRunwayQuarters ?? 0) > 8 ? C.green : (rv.cashRunwayQuarters ?? 0) > 4 ? C.gold : C.red },
    { l: "Net Debt", v: fmtB(rv.netDebt), color: rv.netDebt > 0 ? C.red : C.green },
  ];

  return (
    <div className="report-section">
      <h2 className="section-title">Path to Profitability</h2>
      <div className="grid grid-cols-6 gap-2 mb-4">
        {kpis.map((k) => (
          <div key={k.l} className="text-center p-2 rounded" style={{ background: "#F4F6F9" }}>
            <div className="text-[9px] uppercase tracking-wider" style={{ color: C.muted }}>{k.l}</div>
            <div className="text-sm font-mono font-bold" style={{ color: k.color }}>{k.v}</div>
          </div>
        ))}
      </div>
      {marginData.length > 1 && (
        <div>
          <h3 className="chart-title">Margin Trajectory — Is Profitability Approaching?</h3>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={marginData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="year" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v: number) => `${v?.toFixed(1)}%`} />
              <ReferenceLine y={0} stroke={C.navy} strokeDasharray="3 3" />
              <Line type="monotone" dataKey="grossMargin" stroke={C.green} name="Gross" strokeWidth={2} dot={{ r: 3 }} connectNulls />
              <Line type="monotone" dataKey="opMargin" stroke={C.blue} name="Operating" strokeWidth={2} dot={{ r: 3 }} connectNulls />
              <Line type="monotone" dataKey="netMargin" stroke={C.gold} name="Net" strokeWidth={2} dot={{ r: 3 }} connectNulls />
              <Legend wrapperStyle={{ fontSize: 10 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

/* ── Wall Street 10 ── */
function WallStreet10Section({ sections }: { sections: Record<string, string> }) {
  const order: [string, string, string][] = [
    ["executive_summary", "Executive Summary", "\uD83C\uDFAF"],
    ["goldman_sachs", "Goldman Sachs", "\uD83C\uDFDB\uFE0F"],
    ["morgan_stanley", "Morgan Stanley", "\uD83D\uDCCA"],
    ["jp_morgan", "JP Morgan", "\uD83C\uDFE2"],
    ["blackrock", "BlackRock", "\uD83D\uDEE1\uFE0F"],
    ["bridgewater", "Bridgewater", "\uD83C\uDF0D"],
    ["berkshire", "Berkshire Hathaway", "\uD83E\uDDCA"],
    ["citadel", "Citadel", "\u26A1"],
    ["two_sigma", "Two Sigma", "\uD83D\uDD22"],
    ["elliott", "Elliott Management", "\uD83D\uDCB0"],
    ["ark_invest", "ARK Invest", "\uD83D\uDE80"],
  ];
  return (
    <>
      {order.map(([key, name, icon]) => {
        const content = sections[key];
        if (!content) return null;
        const isExec = key === "executive_summary";
        return (
          <div key={key} className={`report-section ${isExec ? "executive-summary" : ""}`}
            style={isExec ? { background: "#F4F6F9", borderLeft: `4px solid ${C.gold}`, padding: "16px 20px" } : undefined}>
            <h2 className="section-title" style={isExec ? { color: C.gold } : undefined}>{icon} {name}</h2>
            <div className="prose prose-sm max-w-none text-xs leading-relaxed" style={{ color: C.text }}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }} />
          </div>
        );
      })}
    </>
  );
}

function Disclaimer() {
  return (
    <div className="report-page flex flex-col justify-end">
      <div className="w-full h-px mb-6" style={{ background: C.lightGray }} />
      <h2 className="text-sm font-serif font-bold mb-3" style={{ color: C.navy }}>Disclaimer</h2>
      <p className="text-[10px] leading-relaxed" style={{ color: C.muted }}>
        This report was generated by ATLAS Terminal&apos;s AI analysis engine using Gemini AI and pre-computed
        quantitative data from public sources (SEC EDGAR, Yahoo Finance). This is NOT investment advice.
        All financial data is sourced from public filings and market data providers and may contain
        errors or be outdated. The AI-generated perspectives are simulated institutional viewpoints
        and do not represent the actual views of any named financial institution. Past performance
        does not guarantee future results. Always consult a qualified financial advisor before making
        investment decisions.
      </p>
      <div className="mt-8 text-center">
        <div className="text-xs tracking-[0.2em] uppercase" style={{ color: C.gold }}>ATLAS TERMINAL</div>
        <div className="text-[10px] mt-1" style={{ color: C.muted }}>Advanced Terminal for Liquid Asset Surveillance</div>
        <div className="text-[10px] mt-1" style={{ color: C.muted }}>Generated {new Date().toISOString().slice(0, 16).replace("T", " ")} UTC</div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════
   MAIN REPORT PAGE
   ═══════════════════════════════════════════════════════════════════ */
export default function ReportPage() {
  const { ticker } = useTicker();
  const [info, setInfo] = useState<Record<string, any>>({});
  const [stmts, setStmts] = useState<{ income_statement?: FinancialPeriod[]; balance_sheet?: FinancialPeriod[]; cash_flow?: FinancialPeriod[] }>({});
  const [research, setResearch] = useState<ResearchDash | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [consensus, setConsensus] = useState<ConsensusData | null>(null);
  const [peers, setPeers] = useState<PeerData | null>(null);
  const [epsHistory, setEpsHistory] = useState<EarningsHistory[] | null>(null);
  const [quarterly, setQuarterly] = useState<QuarterlyEarnings[] | null>(null);
  const [technical, setTechnical] = useState<TechnicalData | null>(null);
  const [dcf, setDcf] = useState<DCFResult | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResult | null>(null);
  const [monteCarlo, setMonteCarlo] = useState<MonteCarloResult | null>(null);
  const [tornado, setTornado] = useState<TornadoItem[] | null>(null);
  const [reverseDcf, setReverseDcf] = useState<ReverseDCFResult | null>(null);
  const [institutional, setInstitutional] = useState<InstitutionalData | null>(null);
  const [valTier, setValTier] = useState<ValuationTier>("dcf");
  const [relativeVal, setRelativeVal] = useState<RelativeValData | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");

  const generateReport = useCallback(async () => {
    setLoading(true); setError(""); setProgress("Phase 1/4 — Gathering market data (9 parallel requests)...");
    const apiKey = localStorage.getItem("atlas_gemini_key") || "";

    try {
      /* ── Phase 1: All GET endpoints ── */
      const [rOv, rSec, rHi, rSt, rRs, rHl, rCo, rPr, rEh, rEq, rTe] = await Promise.allSettled([
        fetchJson(`/api/market/overview/${ticker}`),
        fetchJson(`/api/market/sector/${ticker}`),
        fetchJson(`/api/financials/${ticker}/highlights`),
        fetchJson(`/api/financials/${ticker}/statements`),
        fetchJson(`/api/research/dashboard/${ticker}`),
        fetchJson(`/api/market/health/${ticker}`),
        fetchJson(`/api/valuation/consensus/${ticker}`),
        fetchJson(`/api/market/peers/${ticker}`),
        fetchJson(`/api/earnings/${ticker}/history`),
        fetchJson(`/api/earnings/${ticker}/quarterly`),
        fetchJson(`/api/technical/${ticker}/indicators`),
      ]);

      // Merge overview + sector + highlights into a single info object
      const ov = rOv.status === "fulfilled" ? rOv.value : null;
      const sec = rSec.status === "fulfilled" ? rSec.value : null;
      const hi = rHi.status === "fulfilled" ? rHi.value : null;
      const mergedInfo: Record<string, any> = {};
      if (ov?.data) Object.assign(mergedInfo, {
        longName: ov.data.name, sector: ov.data.sector, industry: ov.data.industry,
        marketCap: ov.data.market_cap, trailingPE: ov.data.pe_ratio,
        dividendYield: ov.data.dividend_yield ? ov.data.dividend_yield / 100 : 0,
        beta: ov.data.beta, fiftyTwoWeekHigh: ov.data.high_52w, fiftyTwoWeekLow: ov.data.low_52w,
        currentPrice: ov.data.price, longBusinessSummary: ov.data.description,
      });
      if (sec) Object.assign(mergedInfo, {
        sector: sec.sector || mergedInfo.sector, industry: sec.industry || mergedInfo.industry,
        marketCap: sec.market_cap || mergedInfo.marketCap, trailingPE: sec.pe_ratio || mergedInfo.trailingPE,
        forwardPE: sec.forward_pe, currentPrice: sec.current_price || mergedInfo.currentPrice,
        targetMeanPrice: sec.target_mean_price, fiftyTwoWeekHigh: sec.fifty_two_week_high || mergedInfo.fiftyTwoWeekHigh,
        fiftyTwoWeekLow: sec.fifty_two_week_low || mergedInfo.fiftyTwoWeekLow,
        fullTimeEmployees: sec.employees, exchange: sec.exchange,
        debtToEquity: sec.debt_to_equity,
      });
      if (hi) Object.assign(mergedInfo, {
        totalRevenue: hi.revenue, profitMargins: hi.profit_margin,
        returnOnEquity: hi.roe, returnOnAssets: hi.roa, freeCashflow: hi.free_cash_flow,
        netIncomeToCommon: hi.revenue && hi.profit_margin ? hi.revenue * hi.profit_margin : undefined,
        enterpriseToEbitda: hi.ebitda && hi.revenue ? undefined : undefined,
        revenueGrowth: hi.revenue_growth, debtToEquity: hi.debt_to_equity ?? mergedInfo.debtToEquity,
        operatingMargins: hi.operating_margin, grossMargins: hi.gross_margin,
      });
      if (Object.keys(mergedInfo).length > 0) setInfo(mergedInfo);

      const st = rSt.status === "fulfilled" ? rSt.value : null;
      if (st) setStmts(st);
      const rs = rRs.status === "fulfilled" ? rRs.value : null;
      if (rs) setResearch(rs);
      const hl = rHl.status === "fulfilled" ? rHl.value : null;
      if (hl) setHealth(hl);
      const co = rCo.status === "fulfilled" ? rCo.value : null;
      if (co) setConsensus(co);
      const pr = rPr.status === "fulfilled" ? rPr.value : null;
      if (pr) setPeers(pr);
      const eh = rEh.status === "fulfilled" ? rEh.value : null;
      if (eh?.history) setEpsHistory(eh.history);
      const eq = rEq.status === "fulfilled" ? rEq.value : null;
      if (eq?.quarterly) setQuarterly(eq.quarterly);
      const te = rTe.status === "fulfilled" ? rTe.value : null;
      if (te) setTechnical(te);

      /* ── Phase 2: DCF Inputs + Tier Detection ── */
      setProgress("Phase 2/4 — Loading valuation inputs & detecting tier...");
      const [dcfInputs, smartDefaults] = await Promise.allSettled([
        fetchJson(`/api/valuation/dcf-inputs/${ticker}`),
        fetchJson(`/api/valuation/smart-defaults/${ticker}`),
      ]);
      const di = dcfInputs.status === "fulfilled" ? dcfInputs.value : null;
      const sd = smartDefaults.status === "fulfilled" ? smartDefaults.value : null;

      // Detect valuation tier
      const fcfVal = hi?.free_cash_flow ?? di?.fcf ?? null;
      const ebitdaVal = hi?.ebitda ?? null;
      const revGrowthVal = hi?.revenue_growth ?? null;
      const tier = detectValuationTier(fcfVal, ebitdaVal, revGrowthVal);
      setValTier(tier);

      if (tier === "dcf" && di && sd && di.fcf && di.shares) {
        // Tier 1: Full DCF analysis
        const waccDec = (sd.wacc || 9) / 100;
        const tgDec = (sd.terminal_growth || 2.5) / 100;
        const growthDec = (sd.fcf_growth || 10) / 100;
        const params = {
          ticker, fcf: di.fcf, base_fcf: di.fcf, shares: di.shares,
          total_debt: di.total_debt || 0, cash: di.cash || 0,
          wacc: waccDec, terminal_growth: tgDec, fcf_growth: growthDec,
        };
        const mcParams = {
          ...params, wacc_mean: waccDec, wacc_std: 0.015,
          growth_mean: growthDec, growth_std: 0.03,
          term_growth: tgDec, n_simulations: 5000,
        };

        setProgress("Phase 3/4 — Running DCF models (5 parallel)...");
        const [rDcf, rSens, rMc, rTor, rRev] = await Promise.allSettled([
          fetchJson("/api/valuation/dcf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params) }),
          fetchJson("/api/valuation/sensitivity", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params) }),
          fetchJson("/api/valuation/monte-carlo", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(mcParams) }),
          fetchJson("/api/valuation/tornado", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params) }),
          fetchJson("/api/valuation/reverse-dcf", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params) }),
        ]);

        if (rDcf.status === "fulfilled" && rDcf.value) setDcf(rDcf.value);
        if (rSens.status === "fulfilled" && rSens.value) setSensitivity(rSens.value);
        if (rMc.status === "fulfilled" && rMc.value) setMonteCarlo(rMc.value);
        if (rTor.status === "fulfilled" && rTor.value?.data) setTornado(rTor.value.data);
        if (rRev.status === "fulfilled" && rRev.value) setReverseDcf(rRev.value);
      } else if (tier !== "dcf") {
        // Tier 2/3/4: Relative valuation
        setProgress("Phase 3/4 — Computing relative valuation (peer multiples)...");
        const rv = buildRelativeVal(tier, pr, mergedInfo, di, hi);
        if (rv) setRelativeVal(rv);
      }

      /* ── Phase 4: Gemini AI ── */
      if (!apiKey) {
        setError("Quantitative report generated (20+ sections). Add Gemini API key in Settings for Wall Street 10 AI analysis.");
      } else {
        setProgress("Phase 4/4 — Generating Wall Street 10 analysis (Gemini AI, ~15s)...");
        const instRes = await fetch("/api/analysis/institutional", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker, api_key: apiKey }),
        });
        if (instRes.ok) { setInstitutional(await instRes.json()); }
        else { const err = await instRes.json().catch(() => ({})); setError(err.detail || "AI analysis failed. Quantitative data available below."); }
      }

      setProgress("");
    } catch { setError("Report generation failed. Check your connection."); }
    setLoading(false);
  }, [ticker]);

  const handlePrint = useCallback(() => { window.print(); }, []);

  const hasReport = institutional && institutional.sections;
  const hasData = Object.keys(info).length > 0 || Object.keys(stmts).length > 0 || research != null || dcf != null || relativeVal != null;
  const currentPrice = info.currentPrice || info.regularMarketPrice || dcf?.current_price || 0;

  return (
    <>
      {/* ─── Screen UI (hidden when printing) ─── */}
      <div className="no-print">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold"><span className="text-accent-green">{ticker}</span> Institutional Report</h1>
            <p className="text-text-muted text-sm mt-1">Wall Street 10 — Automated institutional-grade equity research with 20+ sections</p>
          </div>
          <div className="flex gap-2">
            {(hasReport || hasData) && (
              <button onClick={handlePrint} className="bg-accent-blue text-white px-5 py-2.5 rounded-md text-sm font-semibold hover:opacity-90 transition-opacity flex items-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Download PDF
              </button>
            )}
            <button onClick={generateReport} disabled={loading}
              className="bg-accent-green text-bg-primary px-5 py-2.5 rounded-md text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-opacity">
              {loading ? "Generating..." : hasData ? "Regenerate" : "Generate Report"}
            </button>
          </div>
        </div>

        {error && <div className="bg-accent-red/10 border border-accent-red/30 rounded-md px-4 py-3 text-accent-red text-sm mb-4">{error}</div>}

        {loading && (
          <div className="bg-bg-card border border-border rounded-lg p-8 text-center">
            <div className="text-accent-green animate-pulse text-lg font-mono mb-3">{progress}</div>
            <div className="w-80 h-1.5 bg-bg-primary rounded-full mx-auto overflow-hidden">
              <div className="h-full bg-accent-green rounded-full animate-pulse" style={{ width: progress.includes("1/4") ? "20%" : progress.includes("2/4") ? "40%" : progress.includes("3/4") ? "65%" : progress.includes("4/4") ? "85%" : "60%" }} />
            </div>
          </div>
        )}

        {!hasData && !loading && (
          <div className="bg-bg-card border border-border rounded-lg p-8 text-center">
            <div className="text-5xl mb-4">📊</div>
            <h2 className="text-text-primary text-lg font-semibold mb-2">Wall Street 10 Institutional Report</h2>
            <p className="text-text-muted text-sm max-w-lg mx-auto mb-4">
              Generate a comprehensive 20+ page equity research report featuring DCF valuation (3 scenarios),
              sensitivity matrix, Monte Carlo simulation, peer comparison, earnings analysis, financial deep-dive,
              and perspectives from 10 institutional frameworks.
            </p>
            <div className="grid grid-cols-4 gap-3 max-w-xl mx-auto mb-6 text-xs">
              {["DCF 3-Scenario", "Sensitivity Matrix", "Monte Carlo 5K", "Tornado Chart", "Peer Comparison", "Earnings Analysis", "F-Score & DuPont", "Wall Street 10 AI"].map((f) => (
                <div key={f} className="bg-bg-secondary px-2 py-1.5 rounded text-text-muted">{f}</div>
              ))}
            </div>
            <p className="text-text-muted text-xs">Gemini API key optional — quantitative sections work without it.</p>
          </div>
        )}
      </div>

      {/* ─── Printable Report ─── */}
      {(hasReport || hasData) && (
        <div className="report-container" id="atlas-report">
          {/* Page 1: Cover */}
          <CoverPage ticker={ticker} info={info} consensus={consensus} dcf={dcf} relativeVal={relativeVal} />

          {/* Page 2: TOC */}
          <TableOfContents hasInstitutional={!!hasReport} />

          {/* Page 3: Investment Snapshot */}
          <div className="report-page">
            <div className="page-header">Investment Snapshot &amp; Key Metrics</div>
            <KpiRow info={info} />
            {institutional?.sections?.executive_summary && (
              <div className="report-section" style={{ background: "#F4F6F9", borderLeft: `4px solid ${C.gold}`, padding: "16px 20px" }}>
                <div className="text-sm leading-relaxed" style={{ color: C.text }}
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(institutional.sections.executive_summary) }} />
              </div>
            )}
            <CompanyProfile info={info} />
          </div>

          {/* Page 4: Financial Performance */}
          <div className="report-page">
            <div className="page-header">Financial Performance</div>
            <FinancialCharts statements={stmts} />
            <BalanceSheetCashFlow statements={stmts} />
          </div>

          {/* Page 5: Quality & Risk */}
          <div className="report-page">
            <div className="page-header">Quality &amp; Risk Assessment</div>
            <QualityScores research={research} health={health} />
          </div>

          {/* Page 6: Waterfall + Anomalies */}
          {(research?.waterfall?.length || research?.anomalies?.length) ? (
            <div className="report-page">
              <div className="page-header">Operating Analysis</div>
              <WaterfallChart waterfall={research?.waterfall || []} />
              <AnomalyTable anomalies={research?.anomalies || []} />
            </div>
          ) : null}

          {/* ── Valuation Pages (Tier-Dependent) ── */}
          {valTier === "dcf" && dcf && (
            <>
              <div className="report-page">
                <div className="page-header">Valuation &mdash; DCF Analysis</div>
                <DCFValuationSection dcf={dcf} reverseDcf={reverseDcf} info={info} />
              </div>
              {(sensitivity || monteCarlo) && (
                <div className="report-page">
                  <div className="page-header">Valuation &mdash; Sensitivity &amp; Monte Carlo</div>
                  <SensitivityHeatmap sensitivity={sensitivity} currentPrice={currentPrice} />
                  <MonteCarloSection mc={monteCarlo} />
                </div>
              )}
              {tornado && tornado.length > 0 && (
                <div className="report-page">
                  <div className="page-header">Valuation &mdash; Tornado Sensitivity</div>
                  <TornadoSection tornado={tornado} />
                </div>
              )}
            </>
          )}

          {valTier !== "dcf" && relativeVal && (
            <>
              <div className="report-page">
                <div className="page-header">Valuation &mdash; {relativeVal.tierLabel}</div>
                <RelativeValuationSection rv={relativeVal} info={info} />
              </div>
              <div className="report-page">
                <div className="page-header">Path to Profitability</div>
                <PathToProfitability rv={relativeVal} stmts={stmts} />
              </div>
            </>
          )}

          {/* Page 10: Peer Comparison */}
          {peers && peers.peers?.length > 0 && (
            <div className="report-page">
              <div className="page-header">Peer Comparison</div>
              <PeerComparisonSection peers={peers} />
            </div>
          )}

          {/* Page 11: Earnings */}
          {(epsHistory?.length || quarterly?.length) ? (
            <div className="report-page">
              <div className="page-header">Earnings Analysis</div>
              <EarningsSection history={epsHistory} quarterly={quarterly} />
            </div>
          ) : null}

          {/* Page 12: Technical */}
          {technical && (
            <div className="report-page">
              <div className="page-header">Technical Summary</div>
              <TechnicalSnapshot technical={technical} info={info} />
            </div>
          )}

          {/* Pages 13+: Wall Street 10 (split across pages for readability) */}
          {institutional?.sections && Object.keys(institutional.sections).length > 0 && (() => {
            const keys = Object.keys(institutional.sections).filter((k) => k !== "executive_summary" && institutional.sections[k]);
            const pages: string[][] = [];
            for (let i = 0; i < keys.length; i += 3) pages.push(keys.slice(i, i + 3));
            return pages.map((pageKeys, pi) => (
              <div key={pi} className="report-page">
                {pi === 0 && <div className="page-header">Wall Street 10 &mdash; Institutional Perspectives</div>}
                {pi > 0 && <div className="page-header">Wall Street 10 &mdash; (continued)</div>}
                <WallStreet10Section sections={Object.fromEntries(pageKeys.map((k) => [k, institutional!.sections[k]]))} />
              </div>
            ));
          })()}

          {/* Last page: Disclaimer */}
          <Disclaimer />
        </div>
      )}

      {/* ─── Print Styles ─── */}
      <style jsx global>{`
        .report-container { max-width: 900px; margin: 24px auto 0; font-family: 'Inter', -apple-system, sans-serif; }
        .report-page { background: ${C.bg}; color: ${C.text}; padding: 40px 48px; margin-bottom: 16px; border-radius: 8px; }
        .cover-page { min-height: 600px; }
        .page-header { font-family: 'Georgia', 'Playfair Display', serif; font-size: 20px; font-weight: 700; color: ${C.navy}; border-bottom: 2px solid ${C.navy}; padding-bottom: 8px; margin-bottom: 20px; }
        .section-title { font-family: 'Georgia', 'Playfair Display', serif; font-size: 14px; font-weight: 700; color: ${C.navy}; margin-bottom: 10px; padding-bottom: 4px; border-bottom: 1px solid ${C.lightGray}; }
        .chart-title { font-size: 11px; font-weight: 600; color: ${C.blue}; margin-bottom: 6px; }
        .report-section { margin-bottom: 20px; }
        .report-section li { margin-left: 16px; list-style: disc; }

        @media print {
          body { background: white !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          .no-print, nav, aside, header, [class*="sidebar"], [class*="ticker-bar"], [class*="chat-panel"],
          [class*="app-shell"] > :first-child, [class*="app-shell"] > :last-child { display: none !important; }
          [class*="app-shell"] { display: block !important; }
          [class*="app-shell"] > :nth-child(2) { margin: 0 !important; padding: 0 !important; width: 100% !important; max-width: 100% !important; }
          .report-container { max-width: 100% !important; margin: 0 !important; }
          .report-page { page-break-after: always; page-break-inside: avoid; margin: 0; padding: 28px 36px; border-radius: 0; }
          .cover-page { min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; }
          .report-section { page-break-inside: avoid; }
          @page { size: A4; margin: 12mm 10mm; }
        }
      `}</style>
    </>
  );
}
