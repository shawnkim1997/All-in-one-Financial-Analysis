"""
AI-derived score/chart helper functions: build Sankey, Piotroski, Radar data from Gemini-extracted financials.
"""
from utils.charts import _radar_norm


def sankey_data_from_ai(ai_dict: dict) -> dict:
    """Build Sankey input dict from get_sec_financials_llm result (current_yr). Gross Profit = Revenue - CostOfRevenue; Operating Income = Gross Profit - OperatingExpenses."""
    out = {"revenue": 0, "cogs": 0, "gross_profit": 0, "opex": 0, "operating_income": 0, "tax_interest_other": 0, "net_income": 0}
    cur = (ai_dict or {}).get("current_yr") or {}
    revenue = max(0, (cur.get("Revenue") or 0))
    cogs = max(0, min(cur.get("CostOfRevenue") or 0, revenue - 1e-6))
    gross_profit = revenue - cogs
    opex = max(0, cur.get("OperatingExpenses") or 0)
    operating_income = gross_profit - opex
    net_income = cur.get("NetIncome") or 0
    tax_interest_other = max(0, operating_income - net_income) if operating_income > net_income else abs(min(0, operating_income - net_income))
    out["revenue"] = max(revenue, 1)
    out["cogs"] = cogs
    out["gross_profit"] = gross_profit
    out["opex"] = opex
    out["operating_income"] = operating_income
    out["tax_interest_other"] = tax_interest_other
    out["net_income"] = net_income
    return out


def piotroski_from_ai(ai_dict: dict) -> dict:
    """Piotroski F-Score (0-9) from AI-extracted current_yr vs previous_yr. Returns {score, criteria, used_ttm: True}."""
    out = {"score": 0, "criteria": [], "used_ttm": True}
    cur = (ai_dict or {}).get("current_yr") or {}
    prev = (ai_dict or {}).get("previous_yr") or {}
    if not cur:
        return out
    def v(d, k): return (d.get(k) or 0)
    ni0, ni1 = v(cur, "NetIncome"), v(prev, "NetIncome")
    ocf0 = v(cur, "OperatingCashFlow")
    ta0, ta1 = v(cur, "TotalAssets"), v(prev, "TotalAssets")
    roa0 = (ni0 / ta0 * 100) if ta0 and ta0 != 0 else None
    roa1 = (ni1 / ta1 * 100) if ta1 and ta1 != 0 else None
    c1 = ni0 > 0
    c2 = ocf0 > 0
    c3 = (roa0 is not None and roa1 is not None and roa0 > roa1)
    c4 = ocf0 > ni0
    lt0, lt1 = v(cur, "LongTermDebt"), v(prev, "LongTermDebt")
    c5 = (ta0 and ta1 and (lt0 / ta0) < (lt1 / ta1)) if ta0 and ta1 else False
    ca0, ca1 = v(cur, "CurrentAssets"), v(prev, "CurrentAssets")
    cl0, cl1 = v(cur, "CurrentLiabilities"), v(prev, "CurrentLiabilities")
    cr0 = (ca0 / cl0) if cl0 and cl0 != 0 else None
    cr1 = (ca1 / cl1) if cl1 and cl1 != 0 else None
    c6 = (cr0 is not None and cr1 is not None and cr0 > cr1)
    sh0, sh1 = v(cur, "SharesOutstanding"), v(prev, "SharesOutstanding")
    c7 = (sh0 <= sh1) if (sh0 and sh1) else True
    rev0, rev1 = v(cur, "Revenue"), v(prev, "Revenue")
    gm0 = ((rev0 - v(cur, "CostOfRevenue")) / rev0 * 100) if rev0 and rev0 != 0 else None
    gm1 = ((rev1 - v(prev, "CostOfRevenue")) / rev1 * 100) if rev1 and rev1 != 0 else None
    c8 = (gm0 is not None and gm1 is not None and gm0 > gm1)
    at0 = (rev0 / ta0) if rev0 and ta0 and ta0 != 0 else None
    at1 = (rev1 / ta1) if rev1 and ta1 and ta1 != 0 else None
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
    out["score"] = sum(1 for _, p in criteria if p)
    out["criteria"] = criteria
    return out


def radar_metrics_from_ai(ai_dict: dict) -> dict:
    """ROE, Current Ratio, Asset Turnover, Equity Mult, Revenue YoY from AI dict; normalized 0-100 for radar. Equity proxy: TotalAssets - CurrentLiabilities - LongTermDebt."""
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
    return {
        "theta": ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"],
        "r": _radar_norm(roe, current_ratio, asset_turnover, equity_mult, rev_yoy),
        "labels": ["Profitability (ROE)", "Liquidity (Curr.Ratio)", "Efficiency (Asset Turn.)", "Solvency (Equity Mult.)", "Growth (Rev YoY)"],
    }
