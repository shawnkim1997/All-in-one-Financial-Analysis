from typing import Optional
import pandas as pd
import streamlit as st
from utils.formatting import _safe_float
from config.constants import INCOME_ROW_MAP, BALANCE_ROW_MAP, CASHFLOW_ROW_MAP

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from yahooquery import Ticker as YQTicker
except ImportError:
    YQTicker = None


def _yq_df_to_our_shape(df: pd.DataFrame, row_map: list, date_col: str = "asOfDate") -> Optional[pd.DataFrame]:
    """Convert yahooquery DataFrame (rows=periods, columns=line items) to our shape: index=line names, columns=dates."""
    if df is None or df.empty or date_col not in df.columns:
        return None
    df = df.dropna(subset=[date_col]).sort_values(date_col, ascending=False).head(5)
    if df.empty:
        return None
    dates = df[date_col].astype(str).str[:10].tolist()
    data = {}
    for our_name, yq_col in row_map:
        cols = (yq_col,) if isinstance(yq_col, str) else yq_col
        val_col = next((c for c in cols if c in df.columns), None)
        if val_col is None:
            data[our_name] = [None] * len(dates)
            continue
        data[our_name] = [_safe_float(v) for v in df[val_col].tolist()]
    out = pd.DataFrame(data, index=dates).T
    out.columns = dates
    return out


def _share_issued_from_yq_balance(df_bal: pd.DataFrame) -> Optional[pd.Series]:
    """Try OrdinarySharesNumber then ShareIssued for shares outstanding in yahooquery balance."""
    if df_bal is None or df_bal.empty:
        return None
    for col in ("OrdinarySharesNumber", "ShareIssued"):
        if col in df_bal.columns and "asOfDate" in df_bal.columns:
            s = df_bal.set_index("asOfDate")[col].sort_index(ascending=False)
            s.index = s.index.astype(str).str[:10]
            return s.reindex(s.index)  # keep as series with date index
    return None


@st.cache_data(ttl=300)
def _get_annual_financials_balance_cashflow_yahooquery(ticker: str) -> tuple:
    """Fetch income, balance, cash flow from yahooquery. Return (fin_df, bal_df, cf_df) with index=line items, columns=dates. TTM fallback if annual insufficient."""
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
            # Build TTM: need at least 2 periods for Piotroski/Radar; use last 4Q and previous 4Q when 8+ quarters
            if inc_q is not None and not inc_q.empty and len(inc_q) >= 4:
                ttm0 = inc_q.head(4).sum(numeric_only=True)
                row0 = ttm0.to_dict() if hasattr(ttm0, "to_dict") else dict(ttm0)
                row0["asOfDate"] = inc_q["asOfDate"].iloc[0] if "asOfDate" in inc_q.columns else "TTM0"
                rows_inc = [row0]
                if len(inc_q) >= 8:
                    ttm1 = inc_q.iloc[4:8].sum(numeric_only=True)
                    row1 = ttm1.to_dict() if hasattr(ttm1, "to_dict") else dict(ttm1)
                    row1["asOfDate"] = inc_q["asOfDate"].iloc[4] if "asOfDate" in inc_q.columns else "TTM1"
                    rows_inc.append(row1)
                inc_a = pd.DataFrame(rows_inc)
            if bal_q is not None and not bal_q.empty:
                bal_a = bal_q.head(2) if (bal_a is None or bal_a.empty) else bal_a
            if cf_q is not None and not cf_q.empty and len(cf_q) >= 4 and (cf_a is None or cf_a.empty):
                ttm0_cf = cf_q.head(4).sum(numeric_only=True)
                row0_cf = ttm0_cf.to_dict() if hasattr(ttm0_cf, "to_dict") else dict(ttm0_cf)
                row0_cf["asOfDate"] = cf_q["asOfDate"].iloc[0] if "asOfDate" in cf_q.columns else "TTM0"
                rows_cf = [row0_cf]
                if len(cf_q) >= 8:
                    ttm1_cf = cf_q.iloc[4:8].sum(numeric_only=True)
                    row1_cf = ttm1_cf.to_dict() if hasattr(ttm1_cf, "to_dict") else dict(ttm1_cf)
                    row1_cf["asOfDate"] = cf_q["asOfDate"].iloc[4] if "asOfDate" in cf_q.columns else "TTM1"
                    rows_cf.append(row1_cf)
                cf_a = pd.DataFrame(rows_cf)
        fin_df = _yq_df_to_our_shape(inc_a, INCOME_ROW_MAP)
        bal_df = _yq_df_to_our_shape(bal_a, BALANCE_ROW_MAP)
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
        cf_df = _yq_df_to_our_shape(cf_a, CASHFLOW_ROW_MAP)
        return (fin_df, bal_df, cf_df)
    except Exception:
        return (None, None, None)


# ---------- Raw statements & FCF = OCF - CapEx ----------
def _get_row_series(df: pd.DataFrame, *names: str) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    for name in names:
        try:
            if name in df.index:
                return df.loc[name].copy()
        except (KeyError, TypeError):
            continue
    return None


def _fin_or_bal_empty(df) -> bool:
    """True if DataFrame is missing, empty, or has no columns (e.g. yfinance returned empty)."""
    return df is None or df.empty or (hasattr(df, "columns") and len(df.columns) == 0)


@st.cache_data(ttl=300)
def _get_annual_financials_balance_cashflow(ticker: str) -> tuple:
    """Return (fin_df, bal_df, cf_df). Uses yahooquery first; if missing/fail, falls back to yfinance with TTM when needed."""
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
                    c0 = qf.iloc[:, :4].sum(axis=1)
                    c1 = qf.iloc[:, 4:8].sum(axis=1)
                    fin = pd.concat([c0, c1], axis=1)
                    fin.columns = ["TTM0", "TTM1"]
                elif n >= 5:
                    c0 = qf.iloc[:, :4].sum(axis=1)
                    c1 = qf.iloc[:, 4:n].sum(axis=1)
                    fin = pd.concat([c0, c1], axis=1)
                    fin.columns = ["TTM0", "TTM1"]
                else:
                    fin = qf.iloc[:, : min(4, n)].sum(axis=1).to_frame("TTM0")
        if _fin_or_bal_empty(bal):
            qb = getattr(t, "quarterly_balance_sheet", None)
            if qb is not None and not qb.empty:
                n = len(qb.columns)
                bal = qb.iloc[:, : min(2, n)].copy()
                if bal.shape[1] == 1:
                    bal.columns = ["B0"]
                else:
                    bal.columns = ["B0", "B1"]
        if _fin_or_bal_empty(cf):
            qc = getattr(t, "quarterly_cashflow", None)
            if qc is not None and not qc.empty:
                n = len(qc.columns)
                cf = qc.iloc[:, : min(4, n)].sum(axis=1).to_frame("TTM0")
        return (fin, bal, cf)
    except Exception:
        return (None, None, None)
