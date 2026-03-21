"""Market data endpoints: DCF inputs, analyst consensus, and comps.

Complements :mod:`server.services.market_fetcher` with higher-level data
retrieval functions that consume the raw financial statements and produce
ready-to-use outputs for the DCF engine and industry comparison panels.
"""

from typing import Dict, Optional

import pandas as pd

from server.utils.safe_float import _safe_float
from server.services.market_fetcher import (
    _get_annual_financials_balance_cashflow,
    _get_row_series,
)

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


def get_dcf_inputs(ticker: str) -> Dict[str, Optional[float]]:
    """Return FCF, Total Debt, Cash, and Shares Outstanding for DCF.

    Tries yahooquery (via ``_get_annual_financials_balance_cashflow``)
    first, then falls back to direct yfinance lookups.

    Returns
    -------
    dict
        Keys: ``fcf``, ``total_debt``, ``cash``, ``shares`` (any may be ``None``).
    """
    out: Dict[str, Optional[float]] = {"fcf": None, "total_debt": 0.0, "cash": 0.0, "shares": None}
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

        # Shares
        shares: Optional[float] = None
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

        # Total Debt
        total_debt: Optional[float] = None
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

        # Cash
        cash: Optional[float] = None
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
                for row_name in ("Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Cash"):
                    if row_name in balance.index:
                        cash = _safe_float(balance.loc[row_name].iloc[0])
                        if cash is not None:
                            break
            except (KeyError, TypeError, IndexError):
                pass
        out["cash"] = float(cash) if cash is not None else 0.0

        # FCF
        ocf = _get_row_series(cashflow, "Operating Cash Flow", "Cash From Operating Activities", "Cash From Operations") if cashflow is not None else None
        capx = _get_row_series(cashflow, "Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment") if cashflow is not None else None
        if ocf is not None and len(ocf) > 0:
            ocf_val = _safe_float(ocf.iloc[0])
            capx_val = _safe_float(capx.iloc[0]) if capx is not None and len(capx) > 0 else 0.0
            if capx_val is None:
                capx_val = 0.0
            if ocf_val is not None:
                latest_fcf = ocf_val - capx_val
                if latest_fcf == latest_fcf and not (isinstance(latest_fcf, float) and pd.isna(latest_fcf)):
                    out["fcf"] = latest_fcf
        return out
    except Exception:
        return out


def get_analyst_consensus(ticker: str) -> Dict[str, str]:
    """Fetch analyst consensus from yfinance: target price, recommendation, growth."""
    out = {"targetMeanPrice": "N/A", "recommendationKey": "N/A", "revenueGrowth": "N/A", "earningsGrowth": "N/A"}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        tp = info.get("targetMeanPrice")
        if tp is not None:
            try:
                out["targetMeanPrice"] = f"${float(tp):.2f}"
            except (TypeError, ValueError):
                out["targetMeanPrice"] = str(tp)
        rec = info.get("recommendationKey") or info.get("recommendation")
        if rec is not None:
            out["recommendationKey"] = str(rec)
        rg = info.get("revenueGrowth")
        if rg is not None:
            try:
                out["revenueGrowth"] = f"{float(rg) * 100:.1f}%"
            except (TypeError, ValueError):
                out["revenueGrowth"] = str(rg)
        eg = info.get("earningsGrowth")
        if eg is not None:
            try:
                out["earningsGrowth"] = f"{float(eg) * 100:.1f}%"
            except (TypeError, ValueError):
                out["earningsGrowth"] = str(eg)
        return out
    except Exception:
        return out


def get_comps_data(tickers: tuple) -> pd.DataFrame:
    """Fetch Forward P/E, EV/EBITDA, P/B for a set of tickers."""
    if not yf:
        return pd.DataFrame()
    rows = []
    for sym in tickers:
        sym = str(sym).strip().upper()
        if not sym:
            continue
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            forward_pe = info.get("forwardPE") or info.get("Forward PE") or info.get("trailingPE") or info.get("Trailing PE")
            ev_ebitda = info.get("enterpriseToEbitda")
            if ev_ebitda is None:
                ev, ebitda = info.get("enterpriseValue"), info.get("ebitda")
                if ev is not None and ebitda is not None and ebitda != 0:
                    ev_ebitda = ev / ebitda
            pb = info.get("priceToBook") or info.get("Price To Book")
            rows.append({
                "Ticker": sym,
                "Forward P/E": round(float(forward_pe), 2) if forward_pe is not None and _safe_float(forward_pe) is not None else None,
                "EV/EBITDA": round(float(ev_ebitda), 2) if ev_ebitda is not None and _safe_float(ev_ebitda) is not None else None,
                "P/B": round(float(pb), 2) if pb is not None and _safe_float(pb) is not None else None,
            })
        except Exception:
            rows.append({"Ticker": sym, "Forward P/E": None, "EV/EBITDA": None, "P/B": None})
    return pd.DataFrame(rows) if rows else pd.DataFrame()
