"""
DCF valuation models and Damodaran WACC mapping.
"""
from config.constants import DAMODARAN_WACC


def dcf_intrinsic_value(fcf: float, wacc: float, terminal_growth: float, fcf_growth: float, years: int = 5) -> float:
    """5-year DCF: project FCF with fcf_growth, then terminal value; discount at WACC. Returns enterprise value. Robust: avoids div by zero."""
    if fcf is None or fcf <= 0:
        return 0.0
    if wacc <= terminal_growth or wacc <= 0:
        return 0.0
    pv = 0.0
    fcft = float(fcf)
    for t in range(1, years + 1):
        pv += fcft / ((1 + wacc) ** t)
        fcft *= (1 + fcf_growth)
    terminal_fcf = fcft
    tv = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv += tv / ((1 + wacc) ** years)
    return pv


def dcf_10y_2stage(fcf: float, wacc: float, term_growth: float, fcf_growth: float) -> float:
    """10-Year 2-Stage DCF. Stage 1 (Y1-5): FCF grows at fcf_growth. Stage 2 (Y6-10): growth linearly fades from fcf_growth to term_growth by Y10. TV at Y10; discount all to PV."""
    if fcf is None or fcf <= 0:
        return 0.0
    if wacc <= term_growth or wacc <= 0:
        return 0.0
    pv = 0.0
    fcft = float(fcf)
    for t in range(1, 6):
        pv += fcft / ((1 + wacc) ** t)
        fcft *= (1 + fcf_growth)
    for t in range(6, 11):
        fade = (t - 6) / 4.0
        g_t = fcf_growth + fade * (term_growth - fcf_growth)
        fcft *= (1 + g_t)
        pv += fcft / ((1 + wacc) ** t)
    tv = fcft * (1 + term_growth) / (wacc - term_growth)
    pv += tv / ((1 + wacc) ** 10)
    return pv


def excel_style_dcf(fcf_base: float, wacc: float, term_growth: float, fcf_growth: float, total_debt: float, cash: float, shares: float) -> dict:
    """10Y 2-Stage DCF: EV = PV(FCF Y1-10) + PV(TV); Equity = EV - Debt + Cash; Value per share = Equity / Shares."""
    ev = dcf_10y_2stage(fcf_base, wacc, term_growth, fcf_growth)
    equity = ev - total_debt + cash
    shares_safe = float(shares) if (shares is not None and float(shares) > 0) else None
    value_per_share = (equity / shares_safe) if shares_safe else None
    return {"ev": ev, "equity_value": equity, "value_per_share": value_per_share, "shares": shares_safe}


def _damodaran_wacc_for_sector(sector: str) -> float:
    """Map yfinance sector string to closest Damodaran WACC. Default 8.0%."""
    if not sector:
        return 8.0
    s = (sector or "").lower()
    if "software" in s or "technology" in s or "internet" in s:
        return DAMODARAN_WACC.get("Software", 8.5)
    if "hardware" in s or "semiconductor" in s:
        return DAMODARAN_WACC.get("Hardware", 9.0)
    if "retail" in s or "consumer" in s or "cyclical" in s:
        return DAMODARAN_WACC.get("Retail", 7.5)
    if "financial" in s or "bank" in s or "insurance" in s:
        return DAMODARAN_WACC.get("Financials", 8.0)
    if "health" in s or "pharma" in s:
        return DAMODARAN_WACC.get("Healthcare", 7.2)
    if "industrial" in s:
        return DAMODARAN_WACC.get("Industrial", 7.8)
    if "energy" in s or "oil" in s:
        return DAMODARAN_WACC.get("Energy", 8.2)
    if "utilities" in s:
        return DAMODARAN_WACC.get("Utilities", 6.5)
    return 8.0
