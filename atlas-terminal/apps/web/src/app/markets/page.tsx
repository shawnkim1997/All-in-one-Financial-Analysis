"use client";
import { useEffect, useState } from "react";
import { useTicker } from "../lib/use-ticker";
import { HeatmapSection } from "../components/markets/HeatmapSection";

type StatementType = "income_statement" | "balance_sheet" | "cash_flow";
type ViewTab = "overview" | "statements";

interface FinancialStatements {
  income_statement?: Record<string, unknown>[];
  balance_sheet?: Record<string, unknown>[];
  cash_flow?: Record<string, unknown>[];
}

interface OverviewItem {
  name: string;
  symbol: string;
  price: number;
  change_pct: number;
}

interface MarketOverviewResponse {
  indices?: OverviewItem[];
  commodities?: OverviewItem[];
  bonds?: OverviewItem[];
  crypto?: OverviewItem[];
  fx?: OverviewItem[];
  popular_etfs?: OverviewItem[];
}

interface SectorHeat {
  sector: string;
  etf: string;
  change_pct: number;
}

const TABS: { key: StatementType; label: string }[] = [
  { key: "income_statement", label: "Income Statement" },
  { key: "balance_sheet", label: "Balance Sheet" },
  { key: "cash_flow", label: "Cash Flow" },
];

// Define the row structure for each statement type
interface RowDef {
  key: string;
  label: string;
  isHeader?: boolean;
  isGrowth?: boolean;
  indent?: boolean;
  bold?: boolean;
}

// Keys support both yahooquery (CamelCase) and yfinance (Spaced) formats
const INCOME_ROWS: RowDef[] = [
  { key: "Total Revenue|TotalRevenue|Operating Revenue|OperatingRevenue", label: "Total Revenue", bold: true },
  { key: "_revenue_yoy", label: "YoY Growth (%)", isGrowth: true },
  { key: "Cost Of Revenue|CostOfRevenue|Reconciled Cost Of Revenue", label: "Cost of Revenue", indent: true },
  { key: "Gross Profit|GrossProfit", label: "Gross Profit", bold: true },
  { key: "_grossprofit_yoy", label: "YoY Growth (%)", isGrowth: true },
  { key: "_GrossMargin", label: "Gross Margin (%)", isGrowth: true },
  { key: "Selling General And Administration|SellingGeneralAndAdministration", label: "SG&A Expenses", indent: true },
  { key: "Research And Development|ResearchAndDevelopment", label: "R&D Expenses", indent: true },
  { key: "Operating Expense|OperatingExpense|Total Expenses", label: "Total Operating Expenses", indent: true },
  { key: "Operating Income|OperatingIncome|EBIT", label: "Operating Income (EBIT)", bold: true },
  { key: "_operatingincome_yoy", label: "YoY Growth (%)", isGrowth: true },
  { key: "_OperatingMargin", label: "Operating Margin (%)", isGrowth: true },
  { key: "Interest Expense|InterestExpense", label: "Interest Expense", indent: true },
  { key: "Other Income Expense|OtherIncomeExpense", label: "Other Income/Expense", indent: true },
  { key: "Pretax Income|PretaxIncome", label: "Income Before Tax", bold: true },
  { key: "_pretaxincome_yoy", label: "YoY Growth (%)", isGrowth: true },
  { key: "Tax Provision|TaxProvision", label: "Income Tax Expense", indent: true },
  { key: "_TaxRate", label: "Effective Tax Rate (%)", isGrowth: true },
  { key: "Net Income|NetIncome", label: "Net Income", bold: true },
  { key: "_netincome_yoy", label: "YoY Growth (%)", isGrowth: true },
  { key: "_NetMargin", label: "Net Margin (%)", isGrowth: true },
  { key: "EBITDA|Normalized EBITDA|NormalizedEBITDA", label: "EBITDA", bold: true },
  { key: "Basic EPS|BasicEPS", label: "Basic EPS" },
  { key: "Diluted EPS|DilutedEPS", label: "Diluted EPS" },
  { key: "Basic Average Shares|BasicAverageShares", label: "Shares Outstanding (Basic)" },
];

const BALANCE_ROWS: RowDef[] = [
  { key: "Total Assets|TotalAssets", label: "Total Assets", bold: true },
  { key: "Current Assets|CurrentAssets", label: "Current Assets", bold: true },
  { key: "Cash And Cash Equivalents|CashAndCashEquivalents", label: "Cash & Equivalents", indent: true },
  { key: "Cash Cash Equivalents And Short Term Investments|CashCashEquivalentsAndShortTermInvestments", label: "Cash & Short-term Investments", indent: true },
  { key: "Receivables", label: "Receivables", indent: true },
  { key: "Inventory", label: "Inventory", indent: true },
  { key: "Other Current Assets|OtherCurrentAssets", label: "Other Current Assets", indent: true },
  { key: "Total Non Current Assets|TotalNonCurrentAssets", label: "Non-Current Assets", bold: true },
  { key: "Net PPE|NetPPE", label: "PP&E (Net)", indent: true },
  { key: "Goodwill And Other Intangible Assets|GoodwillAndOtherIntangibleAssets|Goodwill", label: "Goodwill & Intangibles", indent: true },
  { key: "Total Liabilities Net Minority Interest|TotalLiabilitiesNetMinorityInterest", label: "Total Liabilities", bold: true },
  { key: "Current Liabilities|CurrentLiabilities", label: "Current Liabilities", bold: true },
  { key: "Current Debt|CurrentDebt|Current Debt And Capital Lease Obligation", label: "Current Debt", indent: true },
  { key: "Accounts Payable|AccountsPayable", label: "Accounts Payable", indent: true },
  { key: "Total Non Current Liabilities Net Minority Interest|TotalNonCurrentLiabilitiesNetMinorityInterest", label: "Non-Current Liabilities", bold: true },
  { key: "Long Term Debt|LongTermDebt|Long Term Debt And Capital Lease Obligation", label: "Long-term Debt", indent: true },
  { key: "Stockholders Equity|StockholdersEquity|Total Equity Gross Minority Interest", label: "Stockholders' Equity", bold: true },
  { key: "Retained Earnings|RetainedEarnings", label: "Retained Earnings", indent: true },
  { key: "Common Stock|CommonStock|Common Stock Equity", label: "Common Stock Equity", indent: true },
];

const CASHFLOW_ROWS: RowDef[] = [
  { key: "Operating Cash Flow|OperatingCashFlow", label: "Operating Cash Flow", bold: true },
  { key: "Net Income|Net Income From Continuing Operations|NetIncome", label: "Net Income", indent: true },
  { key: "Depreciation And Amortization|DepreciationAndAmortization|Depreciation Amortization Depletion", label: "D&A", indent: true },
  { key: "Change In Working Capital|ChangeInWorkingCapital", label: "Change in Working Capital", indent: true },
  { key: "Stock Based Compensation|StockBasedCompensation", label: "Stock-based Compensation", indent: true },
  { key: "Investing Cash Flow|InvestingCashFlow", label: "Investing Cash Flow", bold: true },
  { key: "Capital Expenditure|CapitalExpenditure|Purchase Of PPE", label: "Capital Expenditure", indent: true },
  { key: "Purchase Of Investment|PurchaseOfInvestment", label: "Purchases of Investments", indent: true },
  { key: "Sale Of Investment|SaleOfInvestment", label: "Sales of Investments", indent: true },
  { key: "Financing Cash Flow|FinancingCashFlow", label: "Financing Cash Flow", bold: true },
  { key: "Common Stock Issuance|CommonStockIssuance", label: "Stock Issuance", indent: true },
  { key: "Repurchase Of Capital Stock|RepurchaseOfCapitalStock", label: "Share Buybacks", indent: true },
  { key: "Common Stock Dividend Paid|CommonStockDividendPaid|Cash Dividends Paid", label: "Dividends Paid", indent: true },
  { key: "Issuance Of Debt|DebtIssuance|Long Term Debt Issuance", label: "Debt Issuance", indent: true },
  { key: "Repayment Of Debt|DebtRepayment|Long Term Debt Payments", label: "Debt Repayment", indent: true },
  { key: "Free Cash Flow|FreeCashFlow", label: "Free Cash Flow", bold: true },
  { key: "End Cash Position|EndCashPosition|Changes In Cash", label: "End Cash Position", bold: true },
];

const ROW_MAP: Record<StatementType, RowDef[]> = {
  income_statement: INCOME_ROWS,
  balance_sheet: BALANCE_ROWS,
  cash_flow: CASHFLOW_ROWS,
};

export default function MarketsPage() {
  const { ticker } = useTicker();
  const [data, setData] = useState<FinancialStatements | null>(null);
  const [tab, setTab] = useState<StatementType>("income_statement");
  const [viewTab, setViewTab] = useState<ViewTab>("overview");
  const [overview, setOverview] = useState<MarketOverviewResponse | null>(null);
  const [sectors, setSectors] = useState<SectorHeat[]>([]);
  const [selectedHeatmapIndex, setSelectedHeatmapIndex] = useState("sp500");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/financials/${ticker}/statements`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [ticker]);

  useEffect(() => {
    fetch("/api/market/overview")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setOverview(d))
      .catch(() => setOverview(null));
    fetch("/api/market/sectors")
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => setSectors(Array.isArray(d) ? d : []))
      .catch(() => setSectors([]));
  }, []);

  if (loading)
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-accent-green animate-pulse font-mono">Loading...</div>
      </div>
    );

  const rows = data?.[tab] || [];
  const rowDefs = ROW_MAP[tab];

  // Extract period dates (columns) - skip first period if all nulls
  const periods = rows
    .filter((r) => {
      const vals = Object.entries(r).filter(([k]) => !["period", "asOfDate", "periodType", "currencyCode"].includes(k));
      return vals.some(([, v]) => v != null);
    })
    .map((r) => ({
      date: String((r.asOfDate || r.period || "")).slice(0, 10),
      periodType: String(r.periodType || ""),
      data: r,
    }))
    .reverse(); // most recent first

  // Compute derived values
  function getValue(periodData: Record<string, unknown>, key: string): number | null {
    if (key.startsWith("_")) return null; // computed below
    // Support pipe-separated key alternatives
    const keys = key.split("|");
    for (const k of keys) {
      const v = periodData[k.trim()];
      if (v != null && typeof v === "number") return v;
    }
    return null;
  }

  function getComputedValue(periodData: Record<string, unknown>, key: string, prevPeriodData?: Record<string, unknown>): number | null {
    const rev = getValue(periodData, "Total Revenue|TotalRevenue|Operating Revenue|OperatingRevenue");
    if (key === "_GrossMargin") {
      const gp = getValue(periodData, "Gross Profit|GrossProfit");
      return rev && gp ? (gp / rev) * 100 : null;
    }
    if (key === "_OperatingMargin") {
      const oi = getValue(periodData, "Operating Income|OperatingIncome|EBIT");
      return rev && oi ? (oi / rev) * 100 : null;
    }
    if (key === "_NetMargin") {
      const ni = getValue(periodData, "Net Income|NetIncome");
      return rev && ni ? (ni / rev) * 100 : null;
    }
    if (key === "_TaxRate") {
      const tax = getValue(periodData, "Tax Provision|TaxProvision");
      const pretax = getValue(periodData, "Pretax Income|PretaxIncome");
      return pretax && tax ? (tax / pretax) * 100 : null;
    }
    // YoY growth — find the matching row definition to get the key alternatives
    if (key.endsWith("_yoy") && prevPeriodData) {
      const yoyMap: Record<string, string> = {
        "_revenue_yoy": "Total Revenue|TotalRevenue|Operating Revenue|OperatingRevenue",
        "_grossprofit_yoy": "Gross Profit|GrossProfit",
        "_operatingincome_yoy": "Operating Income|OperatingIncome|EBIT",
        "_pretaxincome_yoy": "Pretax Income|PretaxIncome",
        "_netincome_yoy": "Net Income|NetIncome",
      };
      const multiKey = yoyMap[key];
      if (multiKey) {
        const curr = getValue(periodData, multiKey);
        const prev = getValue(prevPeriodData, multiKey);
        if (curr != null && prev != null && prev !== 0) {
          return ((curr - prev) / Math.abs(prev)) * 100;
        }
      }
    }
    return null;
  }

  function getCellValue(rowDef: RowDef, periodIdx: number): number | null {
    if (periods.length === 0) return null;
    const pd = periods[periodIdx]?.data;
    if (!pd) return null;

    if (rowDef.key.startsWith("_")) {
      const prevPd = periodIdx < periods.length - 1 ? periods[periodIdx + 1]?.data : undefined;
      return getComputedValue(pd, rowDef.key, prevPd);
    }
    return getValue(pd, rowDef.key);
  }

  function formatCell(val: number | null, rowDef: RowDef): string {
    if (val == null) return "—";
    if (rowDef.isGrowth) return `${val >= 0 ? "" : ""}${val.toFixed(2)}%`;
    if (rowDef.key === "BasicEPS" || rowDef.key === "DilutedEPS") return val.toFixed(2);
    if (Math.abs(val) >= 1e9) return `${(val / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    if (Math.abs(val) >= 1e6) return `${(val / 1e6).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  // Check if row has any data
  function rowHasData(rowDef: RowDef): boolean {
    return periods.some((_, i) => getCellValue(rowDef, i) != null);
  }

  const filteredRows = rowDefs.filter(rowHasData);

  function renderOverviewCard(title: string, items: OverviewItem[] | undefined) {
    const indexMap: Record<string, string> = {
      "S&P 500": "sp500",
      NASDAQ: "nasdaq100",
      KOSPI: "kospi",
      "FTSE 100": "ftse100",
    };
    return (
      <div className="bg-bg-card border border-border rounded-lg p-4">
        <h3 className="text-text-secondary text-sm font-semibold mb-3">{title}</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
          {(items || []).map((item) => (
            <div
              key={`${title}-${item.symbol}`}
              className="bg-bg-primary border border-border rounded-md p-3"
              style={{ cursor: title === "Global Indices" ? "pointer" : "default" }}
              onClick={() => {
                if (title !== "Global Indices") return;
                const target = indexMap[item.name];
                if (target) {
                  setSelectedHeatmapIndex(target);
                  document.getElementById("heatmap-section")?.scrollIntoView({ behavior: "smooth" });
                }
              }}
            >
              <div className="text-text-muted text-xs">{item.name}</div>
              <div className="text-text-primary font-mono font-semibold">{item.price?.toLocaleString?.() ?? "—"}</div>
              <div className={`font-mono text-xs ${item.change_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                {item.change_pct >= 0 ? "+" : ""}
                {item.change_pct?.toFixed?.(2)}%
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">
        <span className="text-accent-green">{ticker}</span> Markets
      </h1>

      {/* Top Tabs */}
      <div className="flex gap-1 mb-4 bg-bg-card rounded-lg p-1 w-fit">
        {[
          { key: "overview", label: "Market Overview" },
          { key: "statements", label: "Financial Statements" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setViewTab(t.key as ViewTab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              viewTab === t.key ? "bg-accent-green text-bg-primary" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {viewTab === "overview" ? (
        <div className="space-y-4">
          {renderOverviewCard("Global Indices", overview?.indices)}
          <HeatmapSection selectedIndex={selectedHeatmapIndex} onSelectIndex={setSelectedHeatmapIndex} />
          <div className="bg-bg-card border border-border rounded-lg p-4">
            <h3 className="text-text-secondary text-sm font-semibold mb-3">Sector Performance</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              {sectors.map((sector) => (
                <div
                  key={sector.etf}
                  className="rounded-md p-3 flex flex-col items-center justify-center border border-border"
                  style={{
                    background:
                      sector.change_pct >= 0
                        ? `rgba(0, 212, 170, ${Math.min(Math.abs(sector.change_pct) / 5, 0.6)})`
                        : `rgba(255, 71, 87, ${Math.min(Math.abs(sector.change_pct) / 5, 0.6)})`,
                  }}
                >
                  <span className="text-xs font-semibold text-text-primary">{sector.sector}</span>
                  <span className={`text-sm font-mono font-bold ${sector.change_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}>
                    {sector.change_pct >= 0 ? "+" : ""}
                    {sector.change_pct}%
                  </span>
                </div>
              ))}
            </div>
          </div>
          {renderOverviewCard("Commodities", overview?.commodities)}
          {renderOverviewCard("Popular ETFs", overview?.popular_etfs)}
          {renderOverviewCard("Bonds", overview?.bonds)}
          {renderOverviewCard("Crypto", overview?.crypto)}
          {renderOverviewCard("FX", overview?.fx)}
        </div>
      ) : (
        <>
      {/* Unit Note */}
      <div className="text-text-muted text-xs mb-3 font-mono">Unit: Millions USD (except per-share data)</div>

      {/* Statement Tabs */}
      <div className="flex gap-1 mb-4 bg-bg-card rounded-lg p-1 w-fit">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t.key ? "bg-accent-green text-bg-primary" : "text-text-secondary hover:text-text-primary"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {periods.length > 0 ? (
        <div className="bg-bg-card border border-border rounded-lg overflow-x-auto">
          <table className="w-full text-xs">
            {/* Column Headers - Period Dates */}
            <thead>
              <tr className="border-b border-border bg-bg-primary/50">
                <th className="text-left px-4 py-3 text-text-muted font-semibold sticky left-0 bg-bg-card min-w-[220px] z-10">
                  {tab === "income_statement" ? "Income Statement" : tab === "balance_sheet" ? "Balance Sheet" : "Cash Flow Statement"}
                </th>
                {periods.map((p, i) => (
                  <th key={i} className="text-right px-4 py-3 text-text-muted font-semibold whitespace-nowrap min-w-[110px]">
                    <div className="text-text-secondary">{p.date && p.date !== "—" ? p.date.slice(0, 4) : `P${i + 1}`}</div>
                    <div className="text-text-muted text-[10px]">{p.date || "—"}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredRows.map((rowDef) => {
                const isGrowth = rowDef.isGrowth;
                return (
                  <tr
                    key={rowDef.key}
                    className={`border-b border-border/30 ${
                      isGrowth ? "bg-bg-primary/30" : rowDef.bold ? "bg-bg-primary/10" : ""
                    } hover:bg-bg-card/80 transition-colors`}
                  >
                    {/* Row Label */}
                    <td
                      className={`px-4 py-2 sticky left-0 bg-bg-card z-10 ${
                        rowDef.bold ? "font-semibold text-text-primary" : isGrowth ? "text-text-muted italic text-[11px]" : "text-text-secondary"
                      } ${rowDef.indent ? "pl-8" : ""} ${isGrowth ? "pl-8" : ""}`}
                    >
                      {isGrowth ? `↳ ${rowDef.label}` : rowDef.label}
                    </td>
                    {/* Period Values */}
                    {periods.map((_, pi) => {
                      const val = getCellValue(rowDef, pi);
                      const formatted = formatCell(val, rowDef);
                      let colorClass = "text-text-primary";

                      if (isGrowth && val != null) {
                        if (val > 0) colorClass = "text-accent-green";
                        else if (val < 0) colorClass = "text-accent-red";
                        else colorClass = "text-text-muted";
                      } else if (val != null && val < 0 && !isGrowth) {
                        colorClass = "text-accent-red";
                      }

                      return (
                        <td
                          key={pi}
                          className={`px-4 py-2 text-right font-mono whitespace-nowrap ${colorClass} ${
                            rowDef.bold && !isGrowth ? "font-semibold" : ""
                          } ${isGrowth ? "text-[11px]" : ""}`}
                        >
                          {isGrowth && val != null ? (
                            <span
                              className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                                val > 0 ? "bg-accent-green/15 text-accent-green" : val < 0 ? "bg-accent-red/15 text-accent-red" : "bg-bg-primary text-text-muted"
                              }`}
                            >
                              {formatted}
                            </span>
                          ) : (
                            formatted
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-bg-card border border-border rounded-lg p-8 text-center text-text-muted">
          No financial data available for {ticker}
        </div>
      )}
        </>
      )}
    </div>
  );
}
