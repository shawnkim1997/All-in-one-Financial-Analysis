from typing import Optional
import pandas as pd
import streamlit as st
from utils.formatting import _safe_float
from data.financials import _get_row_series, _get_annual_financials_balance_cashflow
from data.ratios import get_dupont_altman_redflags_yoy

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=300)
def get_income_statement_sankey_data(ticker: str) -> dict:
    """Latest year (or TTM): Revenue, COGS, Gross Profit, OpEx, Operating Income, Tax/Interest/Other, Net Income. Uses yahooquery then yfinance."""
    out = {"revenue": 0, "cogs": 0, "gross_profit": 0, "opex": 0, "operating_income": 0, "tax_interest_other": 0, "net_income": 0}
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
        if gross_val is None and revenue and cogs_val is not None:
            gross_val = revenue - cogs_val
        elif gross_val is None:
            gross_val = revenue
        gross_val = abs(gross_val) if gross_val is not None else 0
        op_inc_val = _safe_float(op_inc.get(d)) if op_inc is not None and d in op_inc.index else None
        op_inc_val = op_inc_val if op_inc_val is not None else 0
        ni_val = _safe_float(ni.get(d)) if ni is not None and d in ni.index else None
        ni_val = ni_val if ni_val is not None else 0
        opex_val = max(0, gross_val - op_inc_val) if (gross_val >= op_inc_val) else 0
        tax_interest_other = max(0, op_inc_val - ni_val) if (op_inc_val - ni_val) > 0 else abs(min(0, op_inc_val - ni_val))
        out["revenue"] = max(revenue, 1)
        out["cogs"] = min(cogs_val, revenue - 1e-6)
        out["gross_profit"] = gross_val
        out["opex"] = opex_val
        out["operating_income"] = op_inc_val
        out["tax_interest_other"] = tax_interest_other
        out["net_income"] = ni_val
        return out
    except Exception:
        return out


# sankey_data_from_ai, piotroski_from_ai, radar_metrics_from_ai → data/scores_ai.py


@st.cache_data(ttl=300)
def get_radar_metrics_normalized(ticker: str) -> dict:
    """ROE, Current Ratio, Asset Turnover, Equity Mult, Revenue YoY. Normalized to 0-100 for radar. Returns {theta: [...], r: [...], labels: [...]} or empty."""
    if not ticker:
        return {}
    q = get_dupont_altman_redflags_yoy(ticker)
    if not q:
        return {}
    dupont_df = q.get("dupont")
    if dupont_df is None or dupont_df.empty or len(dupont_df) < 2:
        return {}
    row0 = dupont_df.iloc[0]
    row1 = dupont_df.iloc[1]
    roe = row0.get("ROE %") or 0
    cr = row0.get("Current Ratio") or 0
    at = row0.get("Asset Turnover") or 0
    em = row0.get("Equity Mult.") or 0
    rev0 = dupont_df["Revenue"].iloc[0] if "Revenue" in dupont_df.columns else None
    rev1 = dupont_df["Revenue"].iloc[1] if "Revenue" in dupont_df.columns else None
    rev_yoy = ((rev0 - rev1) / rev1 * 100) if (rev0 and rev1 and rev1 != 0) else 0
    def norm_roe(x):
        if x is None: return 50
        return min(100, max(0, (x + 10) / 40 * 100))
    def norm_cr(x):
        if x is None: return 50
        return min(100, max(0, x / 3 * 100))
    def norm_at(x):
        if x is None: return 50
        return min(100, max(0, x * 50))
    def norm_em(x):
        if x is None: return 50
        return min(100, max(0, (x - 0.5) / 2.5 * 100))
    def norm_yoy(x):
        if x is None: return 50
        return min(100, max(0, (x + 20) / 50 * 100))
    return {
        "theta": ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"],
        "r": [norm_roe(roe), norm_cr(cr), norm_at(at), norm_em(em), norm_yoy(rev_yoy)],
        "labels": ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"],
    }


def _build_radar_figure(ticker: str) -> "go.Figure":
    """Plotly radar chart from ticker data."""
    from utils.charts import _build_radar_common
    data = get_radar_metrics_normalized(ticker)
    if not data or not data.get("r"):
        return None
    return _build_radar_common(data["theta"], data["r"])


@st.cache_data(ttl=300)
def get_piotroski_fscore(ticker: str) -> dict:
    """Piotroski F-Score (0-9) from last 2 periods. Uses yahooquery then yfinance with TTM fallback. Returns score + criteria + used_ttm."""
    out = {"score": 0, "criteria": [], "used_ttm": False}
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
            t = yf.Ticker(ticker.upper())
            info = getattr(t, "info", None) or {}
            sh_info = info.get("sharesOutstanding") or info.get("Shares Outstanding")
            if sh_info is not None:
                try:
                    sh_float = float(sh_info)
                    shares = pd.Series([sh_float] * ncol, index=fin.columns[:ncol])
                except (TypeError, ValueError):
                    pass
        def v0(s):
            if s is None or len(s) == 0:
                return None
            x = _safe_float(s.iloc[0])
            return x if (x is not None and x == x and not (isinstance(x, float) and pd.isna(x))) else None
        def v1(s):
            if s is None or len(s) < 2:
                return None
            x = _safe_float(s.iloc[1])
            return x if (x is not None and x == x and not (isinstance(x, float) and pd.isna(x))) else None
        ni0, ni1 = v0(ni), v1(ni)
        ocf0 = v0(ocf) if ocf is not None else None
        ta0, ta1 = v0(ta), v1(ta)
        roa0 = (ni0 / ta0 * 100) if (ni0 is not None and ta0 is not None and ta0 != 0) else None
        roa1 = (ni1 / ta1 * 100) if (ni1 is not None and ta1 is not None and ta1 != 0) else None
        c1 = (ni0 is not None and ni0 > 0)
        c2 = (ocf0 is not None and ocf0 > 0)
        c3 = (roa0 is not None and roa1 is not None and roa0 > roa1)
        c4 = (ocf0 is not None and ni0 is not None and ocf0 > ni0)
        lt0 = v0(lt_debt) or 0
        lt1 = v1(lt_debt) or 0
        c5 = (ta0 is not None and ta0 != 0 and ta1 is not None and ta1 != 0 and (lt0 / ta0) < (lt1 / ta1))
        cl0, cl1 = v0(cl), v1(cl)
        ca0, ca1 = v0(ca), v1(ca)
        cr0 = (ca0 / cl0) if (ca0 is not None and cl0 is not None and cl0 != 0) else None
        cr1 = (ca1 / cl1) if (ca1 is not None and cl1 is not None and cl1 != 0) else None
        c6 = (cr0 is not None and cr1 is not None and cr0 > cr1)
        sh0, sh1 = v0(shares), v1(shares)
        c7 = (sh0 is not None and sh1 is not None and sh0 <= sh1) if (sh0 is not None and sh1 is not None) else True
        rev0, rev1 = v0(rev), v1(rev)
        gm0 = (v0(gross) / rev0 * 100) if (gross is not None and rev0 is not None and rev0 != 0) else None
        gm1 = (v1(gross) / rev1 * 100) if (gross is not None and rev1 is not None and rev1 != 0) else None
        c8 = (gm0 is not None and gm1 is not None and gm0 > gm1)
        at0 = (rev0 / ta0) if (rev0 is not None and ta0 is not None and ta0 != 0) else None
        at1 = (rev1 / ta1) if (rev1 is not None and ta1 is not None and ta1 != 0) else None
        c9 = (at0 is not None and at1 is not None and at0 > at1)
        criteria = [
            ("Net Income > 0 (profitability)", c1),
            ("Operating Cash Flow > 0 (cash generative)", c2),
            ("ROA increased vs prior period (improving returns)", c3),
            ("OCF > Net Income (earnings quality, less accruals)", c4),
            ("Leverage decreased: LT Debt/Assets lower (less debt)", c5),
            ("Current Ratio improved (better liquidity)", c6),
            ("No dilution: shares unchanged or lower (no equity raise)", c7),
            ("Gross Margin improved (pricing power)", c8),
            ("Asset Turnover improved (efficiency)", c9),
        ]
        score = sum(1 for _, p in criteria if p)
        out["score"] = score
        out["criteria"] = criteria
        out["used_ttm"] = bool(fin is not None and hasattr(fin, "columns") and len(fin.columns) > 0 and any(str(c).startswith("TTM") for c in fin.columns))
        return out
    except Exception:
        out["used_ttm"] = False
        return out


@st.cache_data(ttl=300)
def get_sector_specific_metrics(ticker: str, sector: str) -> dict:
    """Technology: Rule of 40, R&D % revenue. Retail/Consumer: Inventory Turnover, Operating Margin. Financials: ROE, ROA."""
    if not yf:
        return {}
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        fin = t.financials
        bal = t.balance_sheet
        if fin is None or fin.empty:
            fin = getattr(t, "quarterly_financials", None)
            if fin is not None and not fin.empty:
                fin = fin.iloc[:, :4].sum(axis=1).to_frame()
        if bal is None or bal.empty:
            bal = getattr(t, "quarterly_balance_sheet", None)
        out = {}
        sector_lower = (sector or "").lower()
        if "technology" in sector_lower or "software" in sector_lower or "tech" in sector_lower:
            rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
            ocf = _get_row_series(t.cashflow or getattr(t, "quarterly_cashflow", None), "Operating Cash Flow", "Cash From Operating Activities")
            capx = _get_row_series(t.cashflow or getattr(t, "quarterly_cashflow", None), "Capital Expenditure", "Capital Expenditures")
            rd = _get_row_series(fin, "Research And Development", "Research And Development Expense")
            if rev is not None and len(rev) > 0:
                r0 = _safe_float(rev.iloc[0])
                if ocf is not None and len(ocf) > 0 and capx is not None and len(capx) > 0:
                    fcf = _safe_float(ocf.iloc[0]) - _safe_float(capx.iloc[0])
                    out["FCF Margin %"] = round(fcf / r0 * 100, 2) if r0 and fcf is not None else None
                if rd is not None and len(rd) > 0:
                    out["R&D % of Revenue"] = round(_safe_float(rd.iloc[0]) / r0 * 100, 2) if r0 else None
                rev_growth = None
                if rev is not None and len(rev) >= 2:
                    cur, prev = _safe_float(rev.iloc[0]), _safe_float(rev.iloc[1])
                    if prev and prev != 0:
                        rev_growth = (cur - prev) / prev * 100
                if rev_growth is not None and "FCF Margin %" in out and out["FCF Margin %"] is not None:
                    out["Rule of 40 (Rev Growth + FCF Margin)"] = round(rev_growth + out["FCF Margin %"], 1)
        if "consumer" in sector_lower or "retail" in sector_lower or "cyclical" in sector_lower:
            inv = _get_row_series(bal, "Inventory", "Total Inventory")
            cogs = _get_row_series(fin, "Cost Of Revenue", "Cost Of Goods Sold", "Cost of Goods Sold")
            rev = _get_row_series(fin, "Total Revenue", "Revenue", "Net Revenue")
            op_inc = _get_row_series(fin, "Operating Income", "EBIT")
            if inv is not None and len(inv) > 0 and cogs is not None and len(cogs) > 0:
                inv0 = _safe_float(inv.iloc[0])
                cogs0 = _safe_float(cogs.iloc[0])
                out["Inventory Turnover"] = round(cogs0 / inv0, 2) if inv0 else None
            if rev is not None and len(rev) > 0 and op_inc is not None and len(op_inc) > 0:
                r0 = _safe_float(rev.iloc[0])
                op0 = _safe_float(op_inc.iloc[0])
                out["Operating Margin %"] = round(op0 / r0 * 100, 2) if r0 else None
        if "financial" in sector_lower or "bank" in sector_lower or "insurance" in sector_lower:
            ni = _get_row_series(fin, "Net Income", "Net Income Common Stockholders")
            te = _get_row_series(bal, "Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest")
            ta = _get_row_series(bal, "Total Assets")
            if ni is not None and te is not None and len(ni) > 0 and len(te) > 0:
                te0 = _safe_float(te.iloc[0])
                ni0 = _safe_float(ni.iloc[0])
                out["ROE %"] = round(ni0 / te0 * 100, 2) if te0 else None
            if ni is not None and ta is not None and len(ni) > 0 and len(ta) > 0:
                ta0 = _safe_float(ta.iloc[0])
                ni0 = _safe_float(ni.iloc[0])
                out["ROA %"] = round(ni0 / ta0 * 100, 2) if ta0 else None
        return out
    except Exception:
        return {}
