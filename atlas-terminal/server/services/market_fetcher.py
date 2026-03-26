"""Yahoo Finance / yahooquery data fetching for financial statements.

Provides functions to retrieve annual income statements, balance sheets,
cash-flow statements, sector/industry metadata, DCF inputs, analyst
consensus, and peer-comparable multiples.  **Fallback order here:**
yahooquery first (annual or TTM from quarterly), then yfinance — see
``claude.md`` §2.3 feature table (differs from ``/api/financials`` which
tries yfinance first).
"""

from typing import Dict, List, Optional, Tuple

import pandas as pd

from server.utils.safe_float import _safe_float

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

try:
    from yahooquery import Ticker as YQTicker
except ImportError:
    YQTicker = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Row-mapping tables (yahooquery column names -> our canonical names)
# ---------------------------------------------------------------------------

_INCOME_ROW_MAP: List[Tuple[str, Tuple[str, ...]]] = [
    ("Total Revenue", ("TotalRevenue", "OperatingRevenue", "TotalRevenue")),
    ("Cost Of Revenue", ("CostOfRevenue", "ReconciledCostOfRevenue")),
    ("Gross Profit", ("GrossProfit",)),
    ("Operating Income", ("OperatingIncome", "EBIT", "TotalOperatingIncomeAsReported")),
    ("Net Income", ("NetIncome", "NetIncomeCommonStockholders", "NetIncomeContinuousOperations", "DilutedNIAvailtoComStockholders")),
    ("Operating Expense", ("OperatingExpense", "OperatingExpenses", "TotalExpenses")),
    ("Interest Expense", ("InterestExpense", "InterestExpenseNonOperating")),
    ("Research And Development Expenses", ("ResearchAndDevelopment", "ResearchAndDevelopmentExpenses")),
]

_BALANCE_ROW_MAP: List[Tuple[str, Tuple[str, ...]]] = [
    ("Total Assets", ("TotalAssets",)),
    ("Total Stockholder Equity", ("StockholdersEquity", "CommonStockEquity", "TotalEquityGrossMinorityInterest")),
    ("Total Liabilities", ("TotalLiabilitiesNetMinorityInterest", "TotalLiabilities")),
    ("Current Assets", ("CurrentAssets",)),
    ("Current Liabilities", ("CurrentLiabilities",)),
    ("Long Term Debt", ("LongTermDebt", "LongTermDebtAndCapitalLeaseObligation")),
    ("Total Debt", ("TotalDebt",)),
    ("Share Issued", ("OrdinarySharesNumber", "ShareIssued", "BasicAverageShares", "DilutedAverageShares")),
    ("Cash And Cash Equivalents", ("CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments", "EndCashPosition")),
    ("Retained Earnings", ("RetainedEarnings",)),
]

_CASHFLOW_ROW_MAP: List[Tuple[str, Tuple[str, ...]]] = [
    ("Operating Cash Flow", ("OperatingCashFlow", "CashFromOperatingActivities")),
    ("Capital Expenditure", ("CapitalExpenditure", "CapitalExpenditures")),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _yq_df_to_our_shape(
    df: pd.DataFrame,
    row_map: List[Tuple[str, Tuple[str, ...]]],
    date_col: str = "asOfDate",
) -> Optional[pd.DataFrame]:
    """Pivot a yahooquery DataFrame to index=line-items, columns=dates."""
    if df is None or df.empty or date_col not in df.columns:
        return None
    df = df.dropna(subset=[date_col]).sort_values(date_col, ascending=False).head(5)
    if df.empty:
        return None
    dates = df[date_col].astype(str).str[:10].tolist()
    data: Dict[str, list] = {}
    for our_name, yq_cols in row_map:
        cols = yq_cols if isinstance(yq_cols, tuple) else (yq_cols,)
        val_col = next((c for c in cols if c in df.columns), None)
        if val_col is None:
            data[our_name] = [None] * len(dates)
        else:
            data[our_name] = [_safe_float(v) for v in df[val_col].tolist()]
    out = pd.DataFrame(data, index=dates).T
    out.columns = dates
    return out


def _share_issued_from_yq_balance(df_bal: pd.DataFrame) -> Optional[pd.Series]:
    """Extract shares outstanding series from yahooquery balance sheet."""
    if df_bal is None or df_bal.empty:
        return None
    for col in ("OrdinarySharesNumber", "ShareIssued"):
        if col in df_bal.columns and "asOfDate" in df_bal.columns:
            s = df_bal.set_index("asOfDate")[col].sort_index(ascending=False)
            s.index = s.index.astype(str).str[:10]
            return s
    return None


def _get_row_series(df: Optional[pd.DataFrame], *names: str) -> Optional[pd.Series]:
    """Return the first matching row from *df* as a Series, or ``None``."""
    if df is None or df.empty:
        return None
    for name in names:
        try:
            if name in df.index:
                return df.loc[name].copy()
        except (KeyError, TypeError):
            continue
    return None


def _fin_or_bal_empty(df: object) -> bool:
    """True if *df* is missing, empty, or has no columns."""
    return df is None or (hasattr(df, "empty") and df.empty) or (hasattr(df, "columns") and len(df.columns) == 0)


# ---------------------------------------------------------------------------
# Core fetchers
# ---------------------------------------------------------------------------

def _get_annual_financials_balance_cashflow_yahooquery(
    ticker: str,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Fetch annual financials from yahooquery with TTM fallback."""
    if not YQTicker or not ticker:
        return (None, None, None)
    try:
        yq = YQTicker(ticker.upper())
        inc_a = yq.income_statement(frequency="a", trailing=False)
        bal_a = yq.balance_sheet(frequency="a", trailing=False)
        cf_a = yq.cash_flow(frequency="a", trailing=False)
        if inc_a is None or inc_a.empty or bal_a is None or bal_a.empty:
            inc_q = yq.income_statement(frequency="q", trailing=False)
            bal_q = yq.balance_sheet(frequency="q", trailing=False)
            cf_q = yq.cash_flow(frequency="q", trailing=False)
            if inc_q is not None and not inc_q.empty and len(inc_q) >= 4:
                ttm0 = inc_q.head(4).sum(numeric_only=True)
                row0 = ttm0.to_dict()
                row0["asOfDate"] = inc_q["asOfDate"].iloc[0] if "asOfDate" in inc_q.columns else "TTM0"
                rows_inc = [row0]
                if len(inc_q) >= 8:
                    ttm1 = inc_q.iloc[4:8].sum(numeric_only=True)
                    row1 = ttm1.to_dict()
                    row1["asOfDate"] = inc_q["asOfDate"].iloc[4] if "asOfDate" in inc_q.columns else "TTM1"
                    rows_inc.append(row1)
                inc_a = pd.DataFrame(rows_inc)
            if bal_q is not None and not bal_q.empty:
                bal_a = bal_q.head(2) if (bal_a is None or bal_a.empty) else bal_a
            if cf_q is not None and not cf_q.empty and len(cf_q) >= 4 and (cf_a is None or cf_a.empty):
                ttm0_cf = cf_q.head(4).sum(numeric_only=True)
                row0_cf = ttm0_cf.to_dict()
                row0_cf["asOfDate"] = cf_q["asOfDate"].iloc[0] if "asOfDate" in cf_q.columns else "TTM0"
                rows_cf = [row0_cf]
                if len(cf_q) >= 8:
                    ttm1_cf = cf_q.iloc[4:8].sum(numeric_only=True)
                    row1_cf = ttm1_cf.to_dict()
                    row1_cf["asOfDate"] = cf_q["asOfDate"].iloc[4] if "asOfDate" in cf_q.columns else "TTM1"
                    rows_cf.append(row1_cf)
                cf_a = pd.DataFrame(rows_cf)

        fin_df = _yq_df_to_our_shape(inc_a, _INCOME_ROW_MAP)
        bal_df = _yq_df_to_our_shape(bal_a, _BALANCE_ROW_MAP)
        if bal_df is not None and "Share Issued" not in bal_df.index and bal_a is not None and not bal_a.empty:
            for sh_col in ("OrdinarySharesNumber", "ShareIssued"):
                if sh_col in bal_a.columns:
                    row = {"Share Issued": [_safe_float(bal_a[sh_col].iloc[0])]}
                    if bal_df is not None and not bal_df.empty:
                        d = str(bal_a["asOfDate"].iloc[0])[:10] if "asOfDate" in bal_a.columns else bal_df.columns[0]
                        extra = pd.DataFrame(row, index=[d]).T
                        extra.columns = [d]
                        bal_df = pd.concat([bal_df, extra], axis=0)
                    break
        cf_df = _yq_df_to_our_shape(cf_a, _CASHFLOW_ROW_MAP)
        return (fin_df, bal_df, cf_df)
    except Exception:
        return (None, None, None)


def _get_annual_financials_balance_cashflow(
    ticker: str,
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Return ``(fin_df, bal_df, cf_df)`` using yahooquery then yfinance fallback."""
    if not ticker:
        return (None, None, None)
    fin_df, bal_df, cf_df = _get_annual_financials_balance_cashflow_yahooquery(ticker)
    if fin_df is not None and not fin_df.empty and bal_df is not None and not bal_df.empty:
        return (fin_df, bal_df, cf_df)
    if not yf:
        return (None, None, None)
    try:
        t = yf.Ticker(ticker.upper())
        fin = getattr(t, "financials", None)
        bal = getattr(t, "balance_sheet", None)
        cf = getattr(t, "cashflow", None)
        if _fin_or_bal_empty(fin):
            qf = getattr(t, "quarterly_financials", None)
            if qf is not None and not qf.empty:
                n = len(qf.columns)
                if n >= 8:
                    fin = pd.concat([qf.iloc[:, :4].sum(axis=1), qf.iloc[:, 4:8].sum(axis=1)], axis=1)
                    fin.columns = ["TTM0", "TTM1"]
                elif n >= 5:
                    fin = pd.concat([qf.iloc[:, :4].sum(axis=1), qf.iloc[:, 4:n].sum(axis=1)], axis=1)
                    fin.columns = ["TTM0", "TTM1"]
                else:
                    fin = qf.iloc[:, :min(4, n)].sum(axis=1).to_frame("TTM0")
        if _fin_or_bal_empty(bal):
            qb = getattr(t, "quarterly_balance_sheet", None)
            if qb is not None and not qb.empty:
                n = len(qb.columns)
                bal = qb.iloc[:, :min(2, n)].copy()
                bal.columns = ["B0", "B1"] if bal.shape[1] >= 2 else ["B0"]
        if _fin_or_bal_empty(cf):
            qc = getattr(t, "quarterly_cashflow", None)
            if qc is not None and not qc.empty:
                cf = qc.iloc[:, :min(4, len(qc.columns))].sum(axis=1).to_frame("TTM0")
        return (fin, bal, cf)
    except Exception:
        return (None, None, None)


def get_sector_industry(ticker: str) -> Dict[str, str]:
    """Return ``{'sector': ..., 'industry': ...}`` from yfinance."""
    if not yf:
        return {"sector": "N/A", "industry": "N/A"}
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        sector = (info.get("sector") or info.get("sectorDisp") or "N/A").strip() or "N/A"
        industry = (info.get("industry") or info.get("industryDisp") or "N/A").strip() or "N/A"
        return {"sector": sector, "industry": industry}
    except Exception:
        return {"sector": "N/A", "industry": "N/A"}


def get_5yr_financial_trend(ticker: str) -> pd.DataFrame:
    """Up to 5 years of Revenue, Net Income, Operating Margin, FCF."""
    if not yf:
        return pd.DataFrame()
    try:
        t = yf.Ticker(ticker.upper())
        financials = t.financials
        cashflow = t.cashflow
        if financials is None or financials.empty or cashflow is None or cashflow.empty:
            return pd.DataFrame()
        dates = sorted(financials.columns.tolist(), reverse=True)[:5]
        ocf = _get_row_series(cashflow, "Operating Cash Flow", "Cash From Operating Activities", "Cash From Operations")
        capx = _get_row_series(cashflow, "Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment")
        revenue = _get_row_series(financials, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(financials, "Net Income", "Net Income Common Stockholders")
        op_income = _get_row_series(financials, "Operating Income", "EBIT")
        rows = []
        for d in dates:
            yr = d.year if hasattr(d, "year") else int(str(d)[:4])
            rev = _safe_float(revenue.get(d)) if revenue is not None and d in revenue.index else None
            net_i = _safe_float(ni.get(d)) if ni is not None and d in ni.index else None
            op_i = _safe_float(op_income.get(d)) if op_income is not None and d in op_income.index else None
            oper_margin = (op_i / rev * 100) if (op_i is not None and rev and rev != 0) else ((net_i / rev * 100) if (net_i is not None and rev and rev != 0) else None)
            ocf_val = _safe_float(ocf.get(d)) if ocf is not None and d in ocf.index else None
            capx_val = _safe_float(capx.get(d)) if capx is not None and d in capx.index else None
            fcf = (ocf_val - capx_val) if (ocf_val is not None and capx_val is not None) else (ocf_val if ocf_val is not None else None)
            rows.append({
                "Year": yr,
                "Revenue": rev,
                "Net Income": net_i,
                "Operating Margin %": round(oper_margin, 2) if oper_margin is not None else None,
                "FCF": fcf,
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
