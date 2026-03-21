"""Extended financial metrics: Piotroski F-Score, Sankey, radar, sector-specific, quarterly.

Complements :mod:`server.services.financial_metrics` with scoring models,
income-statement flow data, and quarterly momentum indicators.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from server.utils.safe_float import _safe_float
from server.services.market_fetcher import (
    _get_annual_financials_balance_cashflow,
    _get_row_series,
)
from server.services.financial_metrics import (
    _radar_norm,
    get_dupont_altman_redflags_yoy,
)

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Income Statement Sankey
# ---------------------------------------------------------------------------

def get_income_statement_sankey_data(ticker: str) -> Dict[str, float]:
    """Revenue -> COGS -> Gross Profit -> OpEx -> OpIncome -> Net Income."""
    out: Dict[str, float] = {"revenue": 0, "cogs": 0, "gross_profit": 0, "opex": 0, "operating_income": 0, "tax_interest_other": 0, "net_income": 0}
    fin, _, _ = _get_annual_financials_balance_cashflow(ticker)
    if fin is None or fin.empty:
        return out
    try:
        rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
        cogs = _get_row_series(fin, "Cost Of Revenue", "Cost Of Goods Sold")
        gross = _get_row_series(fin, "Gross Profit")
        op_inc = _get_row_series(fin, "Operating Income", "EBIT")
        ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
        if rev is None or len(rev) == 0:
            return out
        d = rev.index[0]
        revenue = abs(_safe_float(rev.get(d)) or 0)
        cogs_val = abs(_safe_float(cogs.get(d)) if cogs is not None and d in cogs.index else 0) or 0
        gross_val = _safe_float(gross.get(d)) if gross is not None and d in gross.index else None
        if gross_val is None:
            gross_val = (revenue - cogs_val) if revenue and cogs_val is not None else revenue
        gross_val = abs(gross_val) if gross_val is not None else 0
        op_inc_val = _safe_float(op_inc.get(d)) if op_inc is not None and d in op_inc.index else 0
        ni_val = _safe_float(ni.get(d)) if ni is not None and d in ni.index else 0
        opex_val = max(0, gross_val - op_inc_val) if gross_val >= op_inc_val else 0
        tax_interest_other = max(0, op_inc_val - ni_val) if (op_inc_val - ni_val) > 0 else abs(min(0, op_inc_val - ni_val))
        return {"revenue": max(revenue, 1), "cogs": min(cogs_val, revenue - 1e-6), "gross_profit": gross_val,
                "opex": opex_val, "operating_income": op_inc_val, "tax_interest_other": tax_interest_other, "net_income": ni_val}
    except Exception:
        return out


def sankey_data_from_ai(ai_dict: Dict[str, Any]) -> Dict[str, float]:
    """Build Sankey input from ``get_sec_financials_llm`` result."""
    cur = (ai_dict or {}).get("current_yr") or {}
    revenue = max(0, (cur.get("Revenue") or 0))
    cogs = max(0, min(cur.get("CostOfRevenue") or 0, revenue - 1e-6))
    gross_profit = revenue - cogs
    opex = max(0, cur.get("OperatingExpenses") or 0)
    operating_income = gross_profit - opex
    net_income = cur.get("NetIncome") or 0
    tax_interest_other = max(0, operating_income - net_income) if operating_income > net_income else abs(min(0, operating_income - net_income))
    return {"revenue": max(revenue, 1), "cogs": cogs, "gross_profit": gross_profit, "opex": opex,
            "operating_income": operating_income, "tax_interest_other": tax_interest_other, "net_income": net_income}


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

def piotroski_from_ai(ai_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Piotroski F-Score (0-9) from AI-extracted current/previous year."""
    out: Dict[str, Any] = {"score": 0, "criteria": [], "used_ttm": True}
    cur = (ai_dict or {}).get("current_yr") or {}
    prev = (ai_dict or {}).get("previous_yr") or {}
    if not cur:
        return out
    def v(d: dict, k: str) -> float:
        return d.get(k) or 0
    ni0, ni1 = v(cur, "NetIncome"), v(prev, "NetIncome")
    ocf0 = v(cur, "OperatingCashFlow")
    ta0, ta1 = v(cur, "TotalAssets"), v(prev, "TotalAssets")
    roa0 = (ni0 / ta0 * 100) if ta0 and ta0 != 0 else None
    roa1 = (ni1 / ta1 * 100) if ta1 and ta1 != 0 else None
    lt0, lt1 = v(cur, "LongTermDebt"), v(prev, "LongTermDebt")
    ca0, cl0 = v(cur, "CurrentAssets"), v(cur, "CurrentLiabilities")
    ca1, cl1 = v(prev, "CurrentAssets"), v(prev, "CurrentLiabilities")
    cr0 = (ca0 / cl0) if cl0 and cl0 != 0 else None
    cr1 = (ca1 / cl1) if cl1 and cl1 != 0 else None
    sh0, sh1 = v(cur, "SharesOutstanding"), v(prev, "SharesOutstanding")
    rev0, rev1 = v(cur, "Revenue"), v(prev, "Revenue")
    gm0 = ((rev0 - v(cur, "CostOfRevenue")) / rev0 * 100) if rev0 and rev0 != 0 else None
    gm1 = ((rev1 - v(prev, "CostOfRevenue")) / rev1 * 100) if rev1 and rev1 != 0 else None
    at0 = (rev0 / ta0) if rev0 and ta0 and ta0 != 0 else None
    at1 = (rev1 / ta1) if rev1 and ta1 and ta1 != 0 else None
    criteria: List[tuple] = [
        ("Net Income > 0 (profitability)", ni0 > 0),
        ("Operating Cash Flow > 0 (cash generative)", ocf0 > 0),
        ("ROA increased vs prior period (improving returns)", roa0 is not None and roa1 is not None and roa0 > roa1),
        ("OCF > Net Income (earnings quality, less accruals)", ocf0 > ni0),
        ("Leverage decreased: LT Debt/Assets lower (less debt)", ta0 and ta1 and (lt0 / ta0) < (lt1 / ta1) if ta0 and ta1 else False),
        ("Current Ratio improved (better liquidity)", cr0 is not None and cr1 is not None and cr0 > cr1),
        ("No dilution: shares unchanged or lower (no equity raise)", (sh0 <= sh1) if (sh0 and sh1) else True),
        ("Gross Margin improved (pricing power)", gm0 is not None and gm1 is not None and gm0 > gm1),
        ("Asset Turnover improved (efficiency)", at0 is not None and at1 is not None and at0 > at1),
    ]
    out["score"] = sum(1 for _, p in criteria if p)
    out["criteria"] = criteria
    return out


def get_piotroski_fscore(ticker: str) -> Dict[str, Any]:
    """Piotroski F-Score from yahooquery/yfinance data."""
    out: Dict[str, Any] = {"score": 0, "criteria": [], "used_ttm": False}
    fin, bal, cf = _get_annual_financials_balance_cashflow(ticker)
    if fin is None or fin.empty or bal is None or bal.empty:
        return out
    if cf is None or cf.empty:
        cf = pd.DataFrame()
    try:
        ncol = min(2, len(fin.columns))
        rev = _get_row_series(fin, "Total Revenue", "Revenue")
        ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
        gross = _get_row_series(fin, "Gross Profit")
        ta = _get_row_series(bal, "Total Assets")
        lt_debt = _get_row_series(bal, "Long Term Debt")
        ca = _get_row_series(bal, "Current Assets")
        cl = _get_row_series(bal, "Current Liabilities")
        ocf = _get_row_series(cf, "Operating Cash Flow", "Cash From Operating Activities") if not cf.empty else None
        shares = _get_row_series(bal, "Share Issued") or _get_row_series(bal, "Ordinary Shares Number")
        if shares is None and yf:
            ti = yf.Ticker(ticker.upper())
            info = getattr(ti, "info", None) or {}
            sh_info = info.get("sharesOutstanding") or info.get("Shares Outstanding")
            if sh_info is not None:
                try:
                    shares = pd.Series([float(sh_info)] * ncol, index=fin.columns[:ncol])
                except (TypeError, ValueError):
                    pass
        def v0(s: Optional[pd.Series]) -> Optional[float]:
            if s is None or len(s) == 0:
                return None
            x = _safe_float(s.iloc[0])
            return x if (x is not None and x == x and not pd.isna(x)) else None
        def v1(s: Optional[pd.Series]) -> Optional[float]:
            if s is None or len(s) < 2:
                return None
            x = _safe_float(s.iloc[1])
            return x if (x is not None and x == x and not pd.isna(x)) else None
        ni0, ni1 = v0(ni), v1(ni)
        ocf0 = v0(ocf) if ocf is not None else None
        ta0, ta1 = v0(ta), v1(ta)
        roa0 = (ni0 / ta0 * 100) if (ni0 is not None and ta0 and ta0 != 0) else None
        roa1 = (ni1 / ta1 * 100) if (ni1 is not None and ta1 and ta1 != 0) else None
        lt0 = v0(lt_debt) or 0
        lt1 = v1(lt_debt) or 0
        cl0, cl1 = v0(cl), v1(cl)
        ca0, ca1 = v0(ca), v1(ca)
        cr0 = (ca0 / cl0) if (ca0 is not None and cl0 and cl0 != 0) else None
        cr1 = (ca1 / cl1) if (ca1 is not None and cl1 and cl1 != 0) else None
        sh0, sh1 = v0(shares), v1(shares)
        rev0, rev1 = v0(rev), v1(rev)
        gm0 = (v0(gross) / rev0 * 100) if (gross is not None and rev0 and rev0 != 0) else None
        gm1 = (v1(gross) / rev1 * 100) if (gross is not None and rev1 and rev1 != 0) else None
        at0 = (rev0 / ta0) if (rev0 and ta0 and ta0 != 0) else None
        at1 = (rev1 / ta1) if (rev1 and ta1 and ta1 != 0) else None
        criteria = [
            ("Net Income > 0 (profitability)", ni0 is not None and ni0 > 0),
            ("Operating Cash Flow > 0 (cash generative)", ocf0 is not None and ocf0 > 0),
            ("ROA increased vs prior period (improving returns)", roa0 is not None and roa1 is not None and roa0 > roa1),
            ("OCF > Net Income (earnings quality, less accruals)", ocf0 is not None and ni0 is not None and ocf0 > ni0),
            ("Leverage decreased: LT Debt/Assets lower (less debt)", ta0 and ta0 != 0 and ta1 and ta1 != 0 and (lt0 / ta0) < (lt1 / ta1)),
            ("Current Ratio improved (better liquidity)", cr0 is not None and cr1 is not None and cr0 > cr1),
            ("No dilution: shares unchanged or lower (no equity raise)", (sh0 is not None and sh1 is not None and sh0 <= sh1) if (sh0 is not None and sh1 is not None) else True),
            ("Gross Margin improved (pricing power)", gm0 is not None and gm1 is not None and gm0 > gm1),
            ("Asset Turnover improved (efficiency)", at0 is not None and at1 is not None and at0 > at1),
        ]
        out["score"] = sum(1 for _, p in criteria if p)
        out["criteria"] = criteria
        out["used_ttm"] = bool(any(str(c).startswith("TTM") for c in fin.columns))
        return out
    except Exception:
        return out


# ---------------------------------------------------------------------------
# Radar metrics
# ---------------------------------------------------------------------------

def radar_metrics_from_ai(ai_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Build radar chart data from AI-extracted financials."""
    cur = (ai_dict or {}).get("current_yr") or {}
    prev = (ai_dict or {}).get("previous_yr") or {}
    if not cur:
        return {}
    eq0 = (cur.get("TotalAssets") or 0) - (cur.get("CurrentLiabilities") or 0) - (cur.get("LongTermDebt") or 0)
    if eq0 <= 0:
        eq0 = (cur.get("TotalAssets") or 0) * 0.5
    roe = (cur.get("NetIncome") or 0) / eq0 * 100 if eq0 else 0
    ca, cl = cur.get("CurrentAssets") or 0, cur.get("CurrentLiabilities") or 0
    current_ratio = (ca / cl) if cl and cl != 0 else 0
    ta = cur.get("TotalAssets") or 1
    asset_turnover = (cur.get("Revenue") or 0) / ta
    equity_mult = (cur.get("TotalAssets") or 0) / eq0 if eq0 else 0
    rev0, rev1 = cur.get("Revenue") or 0, prev.get("Revenue") or 0
    rev_yoy = ((rev0 - rev1) / rev1 * 100) if rev1 and rev1 != 0 else 0
    theta = ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"]
    return {"theta": theta, "r": _radar_norm(roe, current_ratio, asset_turnover, equity_mult, rev_yoy), "labels": theta}


def get_radar_metrics_normalized(ticker: str) -> Dict[str, Any]:
    """ROE, Current Ratio, Asset Turnover, Equity Mult, Revenue YoY normalised 0-100."""
    if not ticker:
        return {}
    q = get_dupont_altman_redflags_yoy(ticker)
    if not q:
        return {}
    dupont_df = q.get("dupont")
    if dupont_df is None or dupont_df.empty or len(dupont_df) < 2:
        return {}
    row0 = dupont_df.iloc[0]
    roe = row0.get("ROE %") or 0
    cr = row0.get("Current Ratio") or 0
    at = row0.get("Asset Turnover") or 0
    em = row0.get("Equity Mult.") or 0
    rev0 = dupont_df["Revenue"].iloc[0] if "Revenue" in dupont_df.columns else None
    rev1 = dupont_df["Revenue"].iloc[1] if "Revenue" in dupont_df.columns else None
    rev_yoy = ((rev0 - rev1) / rev1 * 100) if (rev0 and rev1 and rev1 != 0) else 0
    theta = ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"]
    return {"theta": theta, "r": _radar_norm(roe, cr, at, em, rev_yoy), "labels": theta}


# ---------------------------------------------------------------------------
# Sector-specific metrics
# ---------------------------------------------------------------------------

def get_sector_specific_metrics(ticker: str, sector: str) -> Dict[str, Any]:
    """Technology: Rule of 40, R&D %. Retail: Inventory Turnover. Financials: ROE/ROA."""
    if not yf:
        return {}
    try:
        t = yf.Ticker(ticker.upper())
        fin = t.financials
        bal = t.balance_sheet
        if fin is None or fin.empty:
            fin = getattr(t, "quarterly_financials", None)
            if fin is not None and not fin.empty:
                fin = fin.iloc[:, :4].sum(axis=1).to_frame()
        if bal is None or bal.empty:
            bal = getattr(t, "quarterly_balance_sheet", None)
        out: Dict[str, Any] = {}
        sector_lower = (sector or "").lower()
        if "technology" in sector_lower or "software" in sector_lower or "tech" in sector_lower:
            rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
            cf_source = t.cashflow or getattr(t, "quarterly_cashflow", None)
            ocf = _get_row_series(cf_source, "Operating Cash Flow", "Cash From Operating Activities")
            capx = _get_row_series(cf_source, "Capital Expenditure", "Capital Expenditures")
            rd = _get_row_series(fin, "Research And Development", "Research And Development Expense")
            if rev is not None and len(rev) > 0:
                r0 = _safe_float(rev.iloc[0])
                if ocf is not None and len(ocf) > 0 and capx is not None and len(capx) > 0:
                    fcf = _safe_float(ocf.iloc[0]) - _safe_float(capx.iloc[0])
                    out["FCF Margin %"] = round(fcf / r0 * 100, 2) if r0 and fcf is not None else None
                if rd is not None and len(rd) > 0:
                    out["R&D % of Revenue"] = round(_safe_float(rd.iloc[0]) / r0 * 100, 2) if r0 else None
                if len(rev) >= 2:
                    cur_r, prev_r = _safe_float(rev.iloc[0]), _safe_float(rev.iloc[1])
                    rev_growth = ((cur_r - prev_r) / prev_r * 100) if prev_r and prev_r != 0 else None
                    if rev_growth is not None and "FCF Margin %" in out and out["FCF Margin %"] is not None:
                        out["Rule of 40 (Rev Growth + FCF Margin)"] = round(rev_growth + out["FCF Margin %"], 1)
        if "consumer" in sector_lower or "retail" in sector_lower or "cyclical" in sector_lower:
            inv = _get_row_series(bal, "Inventory", "Total Inventory")
            cogs = _get_row_series(fin, "Cost Of Revenue", "Cost Of Goods Sold")
            rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
            op_inc = _get_row_series(fin, "Operating Income", "EBIT")
            if inv is not None and len(inv) > 0 and cogs is not None and len(cogs) > 0:
                out["Inventory Turnover"] = round(_safe_float(cogs.iloc[0]) / _safe_float(inv.iloc[0]), 2) if _safe_float(inv.iloc[0]) else None
            if rev is not None and len(rev) > 0 and op_inc is not None and len(op_inc) > 0:
                out["Operating Margin %"] = round(_safe_float(op_inc.iloc[0]) / _safe_float(rev.iloc[0]) * 100, 2) if _safe_float(rev.iloc[0]) else None
        if "financial" in sector_lower or "bank" in sector_lower or "insurance" in sector_lower:
            ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
            te = _get_row_series(bal, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")
            ta_s = _get_row_series(bal, "Total Assets")
            if ni is not None and te is not None and len(ni) > 0 and len(te) > 0:
                out["ROE %"] = round(_safe_float(ni.iloc[0]) / _safe_float(te.iloc[0]) * 100, 2) if _safe_float(te.iloc[0]) else None
            if ni is not None and ta_s is not None and len(ni) > 0 and len(ta_s) > 0:
                out["ROA %"] = round(_safe_float(ni.iloc[0]) / _safe_float(ta_s.iloc[0]) * 100, 2) if _safe_float(ta_s.iloc[0]) else None
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Quarterly momentum
# ---------------------------------------------------------------------------

def get_quarterly_momentum(ticker: str) -> Dict[str, Any]:
    """Last 4 quarters Revenue/NI with QoQ growth for the most recent."""
    out: Dict[str, Any] = {"df": None, "qoq_revenue_pct": None, "qoq_ni_pct": None}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        qfin = getattr(t, "quarterly_financials", None)
        if qfin is None or qfin.empty or len(qfin.columns) < 2:
            return out
        rev = _get_row_series(qfin, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(qfin, "Net Income", "Net Income Common Stockholders")
        if rev is None and ni is None:
            return out
        cols = list(qfin.columns)[:4]
        rows: List[Dict[str, Any]] = []
        for c in cols:
            try:
                if hasattr(c, "strftime"):
                    q = (c.month - 1) // 3 + 1
                    label = c.strftime("%Y") + f"-Q{q}"
                else:
                    label = str(c)[:12]
            except Exception:
                label = str(c)[:12]
            r_val = _safe_float(rev.loc[c]) if rev is not None and c in rev.index else None
            n_val = _safe_float(ni.loc[c]) if ni is not None and c in ni.index else None
            rows.append({"Quarter": label, "Revenue": r_val, "Net Income": n_val})
        out["df"] = pd.DataFrame(rows)
        if len(rows) >= 2:
            r0, r1 = rows[0].get("Revenue"), rows[1].get("Revenue")
            n0, n1 = rows[0].get("Net Income"), rows[1].get("Net Income")
            if r0 is not None and r1 is not None and r1 != 0:
                out["qoq_revenue_pct"] = round((r0 - r1) / abs(r1) * 100, 1)
            if n0 is not None and n1 is not None and n1 != 0:
                out["qoq_ni_pct"] = round((n0 - n1) / abs(n1) * 100, 1)
        return out
    except Exception:
        return out


def get_quarterly_ratio_changes(ticker: str) -> List[Dict[str, Any]]:
    """QoQ ratio changes for NPM, ROE, Gross/Operating Margin, Current Ratio, Interest Coverage."""
    out: List[Dict[str, Any]] = []
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        qf = getattr(t, "quarterly_financials", None)
        qb = getattr(t, "quarterly_balance_sheet", None)
        if qf is None or qf.empty or qb is None or qb.empty or len(qf.columns) < 2 or len(qb.columns) < 2:
            return out
        rev = _get_row_series(qf, "Total Revenue", "Revenue", "Net Revenue")
        ni = _get_row_series(qf, "Net Income", "Net Income Common Stockholders")
        gross = _get_row_series(qf, "Gross Profit")
        ebit = _get_row_series(qf, "Operating Income", "EBIT")
        interest = _get_row_series(qf, "Interest Expense", "Interest Expense Net")
        ta = _get_row_series(qb, "Total Assets")
        te = _get_row_series(qb, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")
        ca = _get_row_series(qb, "Current Assets")
        cl = _get_row_series(qb, "Current Liabilities")
        def v(s: Optional[pd.Series], col: Any) -> Optional[float]:
            if s is None or col not in s.index:
                return None
            return _safe_float(s.get(col))
        c0, c1 = qf.columns[0], qf.columns[1]
        b0, b1 = qb.columns[0], qb.columns[1]
        r0, r1 = v(rev, c0), v(rev, c1)
        n0, n1 = v(ni, c0), v(ni, c1)
        g0, g1 = v(gross, c0), v(gross, c1)
        e0, e1 = v(ebit, c0), v(ebit, c1)
        i0, i1 = v(interest, c0), v(interest, c1)
        te0, te1 = v(te, b0), v(te, b1)
        ca0, ca1 = v(ca, b0), v(ca, b1)
        cl0, cl1 = v(cl, b0), v(cl, b1)
        npm0 = (n0 / r0 * 100) if (n0 is not None and r0 and r0 != 0) else None
        npm1 = (n1 / r1 * 100) if (n1 is not None and r1 and r1 != 0) else None
        roe0 = (n0 / te0 * 100) if (n0 is not None and te0 and te0 != 0) else None
        roe1 = (n1 / te1 * 100) if (n1 is not None and te1 and te1 != 0) else None
        gm0 = (g0 / r0 * 100) if (g0 is not None and r0 and r0 != 0) else None
        gm1 = (g1 / r1 * 100) if (g1 is not None and r1 and r1 != 0) else None
        om0 = (e0 / r0 * 100) if (e0 is not None and r0 and r0 != 0) else None
        om1 = (e1 / r1 * 100) if (e1 is not None and r1 and r1 != 0) else None
        cr0 = (ca0 / cl0) if (ca0 is not None and cl0 and cl0 != 0) else None
        cr1 = (ca1 / cl1) if (ca1 is not None and cl1 and cl1 != 0) else None
        ic0 = (e0 / i0) if (e0 is not None and i0 and i0 != 0) else None
        ic1 = (e1 / i1) if (e1 is not None and i1 and i1 != 0) else None
        def make_row(metric: str, cur: Optional[float], prev: Optional[float], is_pct_point: bool = False) -> Optional[Dict[str, Any]]:
            if cur is None:
                return None
            if prev is None:
                return {"Metric": metric, "Current Value": round(cur, 2), "Change": "-", "Trend": "-"}
            chg = (cur - prev) if is_pct_point else (((cur - prev) / abs(prev) * 100) if prev != 0 else 0)
            trend = "up" if chg > 0 else ("down" if chg < 0 else "flat")
            chg_str = f"{chg:+.1f}%" if not is_pct_point else f"{chg:+.1f} pp"
            return {"Metric": metric, "Current Value": round(cur, 2), "Change": chg_str, "Trend": trend}
        for name, cur_v, prev_v, is_pp in [
            ("NPM %", npm0, npm1, True), ("ROE %", roe0, roe1, True), ("Gross Margin %", gm0, gm1, True),
            ("Operating Margin %", om0, om1, True), ("Current Ratio", cr0, cr1, False), ("Interest Coverage", ic0, ic1, False),
        ]:
            r = make_row(name, cur_v, prev_v, is_pp)
            if r:
                out.append(r)
        return out
    except Exception:
        return out
