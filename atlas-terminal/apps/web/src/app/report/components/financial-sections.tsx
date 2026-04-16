/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Financial performance + quality / risk sections.
 * Extracted from the original /report monolith.
 */
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from "recharts";
import { C } from "../design-tokens";
import { getValue } from "../lib/formatters";
import type { FinancialPeriod, ResearchDash, HealthData, StatementsBundle } from "../types";

export function FinancialCharts({ statements }: { statements: StatementsBundle }) {
  const is = statements.income_statement;
  if (!is || is.length === 0) return null;

  const chartData = is.slice(0, 5).reverse().map((p: FinancialPeriod) => {
    const period = p as Record<string, unknown>;
    const rev = getValue(period, "TotalRevenue|Total Revenue|Revenue");
    const ni = getValue(period, "NetIncome|Net Income|Net Income Common Stockholders");
    const gp = getValue(period, "GrossProfit|Gross Profit");
    const op = getValue(period, "OperatingIncome|Operating Income");
    const yr = (period.asOfDate || period.fiscalYear || period.year || "") as string | number;
    return {
      year: typeof yr === "string" ? yr.slice(0, 4) : String(yr),
      revenue: rev ? rev / 1e9 : 0,
      netIncome: ni ? ni / 1e9 : 0,
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
              <Tooltip formatter={(value: number | string) => `${Number(value).toFixed(1)}%`} />
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

export function BalanceSheetCashFlow({ statements }: { statements: StatementsBundle }) {
  const bs = statements.balance_sheet;
  const cf = statements.cash_flow;
  if ((!bs || bs.length === 0) && (!cf || cf.length === 0)) return null;

  const bsData = (bs || []).slice(0, 5).reverse().map((p: FinancialPeriod) => {
    const period = p as Record<string, unknown>;
    const ta = getValue(period, "TotalAssets|Total Assets");
    const tl = getValue(period, "TotalLiabilitiesNetMinorityInterest|Total Liabilities Net Minority Interest|TotalLiab|Total Liabilities");
    const te = getValue(period, "StockholdersEquity|Stockholders Equity|TotalStockholderEquity|Total Stockholder Equity");
    const cash = getValue(period, "CashAndCashEquivalents|Cash And Cash Equivalents|CashCashEquivalentsAndShortTermInvestments");
    const yr = (period.asOfDate || period.fiscalYear || "") as string | number;
    return {
      year: typeof yr === "string" ? yr.slice(0, 4) : String(yr),
      assets: ta ? ta / 1e9 : 0,
      liabilities: tl ? tl / 1e9 : 0,
      equity: te ? te / 1e9 : 0,
      cash: cash ? cash / 1e9 : 0,
    };
  });

  const cfData = (cf || []).slice(0, 5).reverse().map((p: FinancialPeriod) => {
    const period = p as Record<string, unknown>;
    const ocf = getValue(period, "OperatingCashFlow|Operating Cash Flow|CashFlowFromContinuingOperatingActivities");
    const capex = getValue(period, "CapitalExpenditure|Capital Expenditure");
    const fcf = getValue(period, "FreeCashFlow|Free Cash Flow") ?? (ocf != null && capex != null ? ocf + capex : null);
    const yr = (period.asOfDate || period.fiscalYear || "") as string | number;
    return {
      year: typeof yr === "string" ? yr.slice(0, 4) : String(yr),
      ocf: ocf ? ocf / 1e9 : 0,
      capex: capex ? Math.abs(capex) / 1e9 : 0,
      fcf: fcf ? fcf / 1e9 : 0,
    };
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

export function QualityScores({ research, health }: { research: ResearchDash | null; health: HealthData | null }) {
  if (!research && !health) return null;
  const { fscore_total = 0, fscore_criteria = [], dupont_tree } = research || {};
  const altmanZ = health?.altman_z;
  const zLabel = altmanZ == null ? "N/A" : altmanZ > 2.99 ? "Safe" : altmanZ > 1.81 ? "Gray Zone" : "Distress";
  const zColor = altmanZ == null ? C.muted : altmanZ > 2.99 ? C.green : altmanZ > 1.81 ? C.gold : C.red;

  return (
    <div className="report-section">
      <h2 className="section-title">Quality Assessment</h2>
      <div className="grid grid-cols-3 gap-6">
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

export function WaterfallChart({ waterfall }: { waterfall: ResearchDash["waterfall"] }) {
  if (!waterfall || waterfall.length === 0) return null;
  const data = waterfall.map((w) => ({
    name: w.label.length > 14 ? w.label.slice(0, 14) + ".." : w.label,
    value: w.value / 1e9,
    fill: w.step_type === "total" ? C.navy : w.value >= 0 ? C.green : C.red,
  }));
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

export function AnomalyTable({ anomalies }: { anomalies: ResearchDash["anomalies"] }) {
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
