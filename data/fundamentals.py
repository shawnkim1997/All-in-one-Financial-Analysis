from typing import Optional
import pandas as pd
import streamlit as st
from utils.formatting import _safe_float

try:
    import yfinance as yf
except ImportError:
    yf = None

from data.financials import _get_row_series, _get_annual_financials_balance_cashflow


@st.cache_data(ttl=300)
def get_sector_industry(ticker: str) -> dict:
    """Return sector and industry from yfinance. Fallback to N/A."""
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


@st.cache_data(ttl=300)
def get_5yr_financial_trend(ticker: str) -> pd.DataFrame:
    """Extract up to 5 years: Revenue, Net Income, Operating Margin, FCF (OCF - CapEx). Handles missing years."""
    if not yf:
        return pd.DataFrame()
    try:
        t = yf.Ticker(ticker.upper())
        financials = t.financials  # annual
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
        cashflow_cols = list(cashflow.columns) if cashflow is not None else []
        for d in dates:
            yr = d.year if hasattr(d, "year") else int(str(d)[:4])
            rev = _safe_float(revenue.get(d)) if revenue is not None and d in revenue.index else None
            net_i = _safe_float(ni.get(d)) if ni is not None and d in ni.index else None
            op_i = _safe_float(op_income.get(d)) if op_income is not None and d in op_income.index else None
            oper_margin = (op_i / rev * 100) if (op_i is not None and rev and rev != 0) else ((net_i / rev * 100) if (net_i is not None and rev and rev != 0) else None)
            ocf_val = _safe_float(ocf.get(d)) if ocf is not None and d in ocf.index else None
            if ocf_val is None and ocf is not None and cashflow_cols:
                for c in cashflow_cols:
                    if (getattr(c, "year", None) or int(str(c)[:4])) == yr:
                        ocf_val = _safe_float(ocf.get(c))
                        break
            capx_val = _safe_float(capx.get(d)) if capx is not None and d in capx.index else None
            if capx_val is None and capx is not None and cashflow_cols:
                for c in cashflow_cols:
                    if (getattr(c, "year", None) or int(str(c)[:4])) == yr:
                        capx_val = _safe_float(capx.get(c))
                        break
            if ocf_val is not None and capx_val is not None:
                fcf = ocf_val - capx_val
            elif ocf_val is not None:
                fcf = ocf_val
            else:
                fcf = None
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


@st.cache_data(ttl=300)
def get_dcf_inputs(ticker: str) -> dict:
    """FCF, Cash, Total Debt, Shares: from yahooquery (via _get_annual_financials) or yfinance fallback."""
    out = {"fcf": None, "total_debt": 0.0, "cash": 0.0, "shares": None}
    if not ticker:
        return out
    try:
        fin, bal, cf = _get_annual_financials_balance_cashflow(ticker)
        if bal is not None and not bal.empty and cf is not None and not cf.empty:
            sh = _get_row_series(bal, "Share Issued")
            out["shares"] = _safe_float(sh.iloc[0]) if sh is not None and len(sh) > 0 else None
            td = _get_row_series(bal, "Total Debt")
            out["total_debt"] = float(td.iloc[0] or 0) if td is not None and len(td) > 0 else 0.0
            cash_s = _get_row_series(bal, "Cash And Cash Equivalents")
            out["cash"] = float(cash_s.iloc[0] or 0) if cash_s is not None and len(cash_s) > 0 else 0.0
            ocf = _get_row_series(cf, "Operating Cash Flow")
            capx = _get_row_series(cf, "Capital Expenditure")
            if ocf is not None and len(ocf) > 0:
                ocf_val = _safe_float(ocf.iloc[0])
                capx_val = _safe_float(capx.iloc[0]) if capx is not None and len(capx) > 0 else 0.0
                if ocf_val is not None:
                    out["fcf"] = ocf_val - (capx_val or 0)
            if out.get("fcf") is not None or out.get("shares") is not None:
                return out
    except Exception:
        pass
    if not yf:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        fast_info = getattr(t, "fast_info", None)
        cashflow = getattr(t, "cashflow", None)
        if cashflow is None or cashflow.empty:
            cashflow = getattr(t, "quarterly_cashflow", None)
        balance = getattr(t, "balance_sheet", None)
        if balance is None or balance.empty:
            balance = getattr(t, "quarterly_balance_sheet", None)

        # ----- Shares Outstanding: multi-step fallback (no manual by default) -----
        shares = None
        if fast_info is not None:
            try:
                s = getattr(fast_info, "shares", None)
                if s is None and hasattr(fast_info, "get"):
                    s = fast_info.get("shares")
                if s is not None and float(s) > 0:
                    shares = float(s)
            except (TypeError, ValueError, AttributeError):
                pass
        if shares is None:
            for key in ("sharesOutstanding", "Shares Outstanding", "impliedSharesOutstanding", "Float Shares"):
                s = info.get(key)
                if s is not None and float(s) > 0:
                    shares = float(s)
                    break
        if shares is None and balance is not None and not balance.empty:
            try:
                if "Share Issued" in balance.index:
                    shares = _safe_float(balance.loc["Share Issued"].iloc[0])
                if (shares is None or shares <= 0) and "Ordinary Shares Number" in balance.index:
                    shares = _safe_float(balance.loc["Ordinary Shares Number"].iloc[0])
            except (KeyError, TypeError, IndexError):
                pass
        out["shares"] = shares if (shares is not None and shares > 0) else None

        # ----- Total Debt: fast_info → info → balance -----
        total_debt = None
        if fast_info is not None:
            try:
                d = getattr(fast_info, "total_debt", None) or (fast_info.get("total_debt") if hasattr(fast_info, "get") else None)
                if d is not None and float(d) >= 0:
                    total_debt = float(d)
            except (TypeError, ValueError, AttributeError):
                pass
        if total_debt is None:
            total_debt = info.get("Total Debt")
        if total_debt is None and balance is not None and not balance.empty:
            try:
                if "Total Debt" in balance.index:
                    total_debt = _safe_float(balance.loc["Total Debt"].iloc[0])
            except (KeyError, TypeError, IndexError):
                pass
        out["total_debt"] = float(total_debt) if total_debt is not None else 0.0

        # ----- Cash: fast_info → info → balance -----
        cash = None
        if fast_info is not None:
            try:
                c = getattr(fast_info, "cash", None) or (fast_info.get("cash") if hasattr(fast_info, "get") else None)
                if c is not None and float(c) >= 0:
                    cash = float(c)
            except (TypeError, ValueError, AttributeError):
                pass
        if cash is None:
            cash = info.get("Cash And Cash Equivalents") or info.get("Cash")
        if cash is None and balance is not None and not balance.empty:
            try:
                for row in ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash"):
                    if row in balance.index:
                        cash = _safe_float(balance.loc[row].iloc[0])
                        if cash is not None:
                            break
            except (KeyError, TypeError, IndexError):
                pass
        out["cash"] = float(cash) if cash is not None else 0.0

        # ----- Base FCF = OCF - CapEx -----
        ocf = _get_row_series(cashflow, "Operating Cash Flow", "Cash From Operating Activities", "Cash From Operations") if cashflow is not None else None
        capx = _get_row_series(cashflow, "Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment") if cashflow is not None else None
        if ocf is not None and len(ocf) > 0:
            latest_date = ocf.index[0]
            ocf_val = _safe_float(ocf.iloc[0])
            capx_val = _safe_float(capx.get(latest_date)) if (capx is not None and hasattr(capx, "index") and latest_date in getattr(capx, "index", [])) else (_safe_float(capx.iloc[0]) if capx is not None and len(capx) > 0 else None)
            if capx_val is None:
                capx_val = 0.0
            if ocf_val is not None:
                latest_fcf = ocf_val - capx_val
                if latest_fcf == latest_fcf and not (isinstance(latest_fcf, float) and pd.isna(latest_fcf)):
                    out["fcf"] = latest_fcf
        return out
    except Exception:
        return out
