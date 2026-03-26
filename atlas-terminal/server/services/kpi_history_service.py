"""Quarterly KPI series for overview sparklines (pandas/yfinance, no LLM)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from server.utils.safe_float import _safe_float


def _get(df: Optional[pd.DataFrame], row_keys: List[str], col) -> Optional[float]:
    if df is None or df.empty:
        return None
    for k in row_keys:
        if k in df.index:
            return _safe_float(df.loc[k, col])
    return None


def build_kpi_history(ticker: str, max_quarters: int = 8) -> Dict[str, Any]:
    """Return payload matching KpiHistoryData on the frontend."""
    sym = ticker.upper().strip()
    try:
        t = yf.Ticker(sym)
        inc = t.quarterly_income_stmt
        bs = t.quarterly_balance_sheet
        cf = t.quarterly_cashflow
    except Exception:
        inc = None

    empty = {
        "ticker": sym,
        "quarters": [],
        "revenue_growth": [],
        "operating_margin": [],
        "net_margin": [],
        "roe": [],
        "fcf": [],
    }

    if inc is None or inc.empty:
        return empty

    cols = sorted(inc.columns, key=lambda c: pd.Timestamp(c))[-max_quarters:]

    rev_keys = ["Total Revenue", "TotalRevenue", "Operating Revenue"]
    oi_keys = ["Operating Income", "OperatingIncome", "EBIT"]
    ni_keys = ["Net Income", "NetIncome"]
    eq_keys = [
        "Stockholders Equity",
        "Total Stockholder Equity",
        "Common Stock Equity",
        "Total Equity Gross Minority Interest",
    ]
    ocf_keys = ["Operating Cash Flow", "OperatingCashFlow", "Cash From Operating Activities"]
    capex_keys = ["Capital Expenditure", "CapitalExpenditure", "Purchase Of PPE"]

    quarters: List[str] = []
    revenue_growth: List[Optional[float]] = []
    operating_margin: List[Optional[float]] = []
    net_margin: List[Optional[float]] = []
    roe: List[Optional[float]] = []
    fcf: List[Optional[float]] = []

    prev_rev: Optional[float] = None

    for col in cols:
        q = pd.Timestamp(col)
        quarters.append(q.strftime("%Y-%m"))

        rev = _get(inc, rev_keys, col)
        oi = _get(inc, oi_keys, col)
        ni = _get(inc, ni_keys, col)

        if prev_rev is not None and rev is not None and prev_rev != 0:
            revenue_growth.append(round((rev - prev_rev) / abs(prev_rev) * 100, 2))
        else:
            revenue_growth.append(None)
        prev_rev = rev

        if rev and oi is not None and rev != 0:
            operating_margin.append(round(oi / rev * 100, 2))
        else:
            operating_margin.append(None)

        if rev and ni is not None and rev != 0:
            net_margin.append(round(ni / rev * 100, 2))
        else:
            net_margin.append(None)

        eq = _get(bs, eq_keys, col) if bs is not None and not bs.empty else None
        if ni is not None and eq and eq != 0:
            roe.append(round(ni / eq * 100, 2))
        else:
            roe.append(None)

        ocf = _get(cf, ocf_keys, col) if cf is not None and not cf.empty else None
        capex = _get(cf, capex_keys, col) if cf is not None and not cf.empty else None
        if ocf is not None:
            cap = capex if capex is not None else 0.0
            fcf.append(ocf + cap)
        else:
            fcf.append(None)

    return {
        "ticker": sym,
        "quarters": quarters,
        "revenue_growth": revenue_growth,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "roe": roe,
        "fcf": fcf,
    }
