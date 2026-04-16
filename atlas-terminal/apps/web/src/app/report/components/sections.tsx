/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Cover, TOC, Investment Snapshot (KpiRow + CompanyProfile), Disclaimer.
 * Pure presentational components extracted from the original 1400-line page.
 */
import { C } from "../design-tokens";
import { fmtB, fmtPct, fmtPrice, renderMarkdown } from "../lib/formatters";
import type { ConsensusData, DCFResult, RelativeValData, InstitutionalData } from "../types";

export function CoverPage({
  ticker, info, consensus, dcf, relativeVal,
}: {
  ticker: string;
  info: Record<string, any>;
  consensus: ConsensusData | null;
  dcf: DCFResult | null;
  relativeVal: RelativeValData | null;
}) {
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

export function TableOfContents({ hasInstitutional }: { hasInstitutional: boolean }) {
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

export function KpiRow({ info }: { info: Record<string, any> }) {
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

export function CompanyProfile({ info }: { info: Record<string, any> }) {
  const desc = info.longBusinessSummary || info.description || "";
  if (!desc) return null;
  const cur: string = info.currency || "USD";
  const stats = [
    { l: "Employees", v: info.fullTimeEmployees ? Number(info.fullTimeEmployees).toLocaleString() : "—" },
    { l: "Country", v: info.country || "—" },
    { l: "Exchange", v: info.exchange || "—" },
    { l: "52W High", v: fmtPrice(info.fiftyTwoWeekHigh, cur) },
    { l: "52W Low", v: fmtPrice(info.fiftyTwoWeekLow, cur) },
    { l: "Beta", v: info.beta ? Number(info.beta).toFixed(2) : "—" },
    { l: "Avg Volume", v: info.averageVolume ? `${(info.averageVolume / 1e6).toFixed(1)}M` : "—" },
    { l: "Dividend Yield", v: info.dividendYield ? `${(info.dividendYield * 100).toFixed(2)}%` : "—" },
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

export function ExecutiveSummaryBlock({ institutional }: { institutional: InstitutionalData | null }) {
  if (!institutional?.sections?.executive_summary) return null;
  return (
    <div className="report-section" style={{ background: "#F4F6F9", borderLeft: `4px solid ${C.gold}`, padding: "16px 20px" }}>
      <div className="text-sm leading-relaxed" style={{ color: C.text }}
        dangerouslySetInnerHTML={{ __html: renderMarkdown(institutional.sections.executive_summary) }} />
    </div>
  );
}

export function Disclaimer() {
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
