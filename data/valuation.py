from typing import Optional
import pandas as pd
import streamlit as st
from utils.formatting import _safe_float
from data.financials import _get_row_series

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=300)
def get_analyst_consensus(ticker: str) -> dict:
    """Fetch analyst consensus from yfinance."""
    out = {"targetMeanPrice": None, "targetHighPrice": None, "targetLowPrice": None, "recommendationKey": "N/A", "revenueGrowth": "N/A", "earningsGrowth": "N/A", "numberOfAnalystOpinions": "N/A", "currentPrice": None}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        for key in ("targetMeanPrice", "targetHighPrice", "targetLowPrice"):
            v = info.get(key)
            if v is not None:
                try:
                    out[key] = float(v)
                except (TypeError, ValueError):
                    pass
        out["currentPrice"] = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        out["numberOfAnalystOpinions"] = info.get("numberOfAnalystOpinions") or "N/A"
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


@st.cache_data(ttl=300)
def get_dcf_smart_defaults(ticker: str) -> dict:
    """Smart default assumptions: WACC from CAPM (Beta), Terminal Growth = 2.5%, FCF Growth from revenueGrowth/earningsGrowth or 8%."""
    out = {"wacc_pct": 10.0, "term_growth_pct": 2.5, "fcf_growth_pct": 8.0}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        beta = info.get("beta")
        if beta is None:
            beta = 1.0
        else:
            try:
                beta = float(beta)
            except (TypeError, ValueError):
                beta = 1.0
        risk_free = 4.0
        market_risk_premium = 5.0
        calculated_wacc = risk_free + (beta * market_risk_premium)
        out["wacc_pct"] = round(min(20.0, max(4.0, calculated_wacc)), 1)
        out["term_growth_pct"] = 2.5
        rev_growth = info.get("revenueGrowth") or info.get("earningsGrowth")
        if rev_growth is not None:
            try:
                g = float(rev_growth)
                out["fcf_growth_pct"] = round(min(30.0, max(-10.0, g * 100)), 1)
            except (TypeError, ValueError):
                pass
        return out
    except Exception:
        return out


@st.cache_data(ttl=300)
def get_fcff_fcfe_valuation(ticker: str) -> dict:
    """FCFF/FCFE two-stage valuation model. Returns dict with fcff, fcfe, and per-share values."""
    if not yf:
        return {}
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        fin = t.financials
        bal = t.balance_sheet
        cf = t.cashflow
        if fin is None or fin.empty:
            return {}
        # Get latest year data
        rev = _get_row_series(fin, "Total Revenue", "Revenue")
        ebit = _get_row_series(fin, "EBIT", "Operating Income")
        ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
        ocf = _get_row_series(cf, "Operating Cash Flow", "Cash From Operating Activities") if cf is not None else None
        capx = _get_row_series(cf, "Capital Expenditure", "Capital Expenditures") if cf is not None else None
        dep = _get_row_series(cf, "Depreciation And Amortization", "Depreciation & Amortization") if cf is not None else None

        r0 = _safe_float(rev.iloc[0]) if rev is not None and len(rev) > 0 else None
        ebit0 = _safe_float(ebit.iloc[0]) if ebit is not None and len(ebit) > 0 else None
        ni0 = _safe_float(ni.iloc[0]) if ni is not None and len(ni) > 0 else None
        ocf0 = _safe_float(ocf.iloc[0]) if ocf is not None and len(ocf) > 0 else None
        capx0 = abs(_safe_float(capx.iloc[0]) or 0) if capx is not None and len(capx) > 0 else 0
        dep0 = _safe_float(dep.iloc[0]) if dep is not None and len(dep) > 0 else 0

        # Tax rate estimation
        tax_expense = _get_row_series(fin, "Tax Provision", "Income Tax Expense")
        pretax = _get_row_series(fin, "Pretax Income", "Income Before Tax")
        tax_rate = 0.21  # default US corporate
        if tax_expense is not None and pretax is not None and len(tax_expense) > 0 and len(pretax) > 0:
            te = _safe_float(tax_expense.iloc[0])
            pt = _safe_float(pretax.iloc[0])
            if pt and pt > 0 and te is not None:
                tax_rate = min(max(te / pt, 0.05), 0.40)

        # Balance sheet items
        total_debt_series = _get_row_series(bal, "Total Debt") if bal is not None else None
        cash_series = _get_row_series(bal, "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments") if bal is not None else None
        equity_series = _get_row_series(bal, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest") if bal is not None else None

        total_debt = _safe_float(total_debt_series.iloc[0]) if total_debt_series is not None and len(total_debt_series) > 0 else 0
        cash_val = _safe_float(cash_series.iloc[0]) if cash_series is not None and len(cash_series) > 0 else 0
        equity_val = _safe_float(equity_series.iloc[0]) if equity_series is not None and len(equity_series) > 0 else 0

        shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding") or 1
        beta = info.get("beta") or 1.0

        # FCFF = EBIT(1-t) + D&A - CapEx - delta WC (approximate)
        fcff = None
        if ebit0 is not None:
            fcff = ebit0 * (1 - tax_rate) + (dep0 or 0) - capx0

        # FCFE = Net Income + D&A - CapEx - delta WC + Net Borrowing (approximate as NI + D&A - CapEx)
        fcfe = None
        if ni0 is not None:
            fcfe = ni0 + (dep0 or 0) - capx0

        # WACC components
        rf = 0.045  # risk-free rate
        erp = 0.055  # equity risk premium
        cost_of_equity = rf + beta * erp
        cost_of_debt = 0.05  # approximate
        if total_debt and equity_val and (total_debt + equity_val) > 0:
            debt_weight = total_debt / (total_debt + equity_val)
            equity_weight = equity_val / (total_debt + equity_val)
        else:
            debt_weight, equity_weight = 0.2, 0.8

        wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)

        # Margins
        fcff_margin = (fcff / r0 * 100) if fcff and r0 and r0 > 0 else None
        fcfe_margin = (fcfe / r0 * 100) if fcfe and r0 and r0 > 0 else None

        return {
            "fcff": fcff, "fcfe": fcfe, "fcff_margin": fcff_margin, "fcfe_margin": fcfe_margin,
            "ebit": ebit0, "net_income": ni0, "revenue": r0,
            "tax_rate": tax_rate * 100, "depreciation": dep0, "capex": capx0,
            "total_debt": total_debt, "cash": cash_val, "equity": equity_val,
            "shares": shares, "beta": beta,
            "wacc": wacc * 100, "cost_of_equity": cost_of_equity * 100, "cost_of_debt": cost_of_debt * 100,
            "debt_weight": debt_weight * 100, "equity_weight": equity_weight * 100,
        }
    except Exception:
        return {}
