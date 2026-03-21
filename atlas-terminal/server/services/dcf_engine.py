"""Discounted Cash Flow (DCF) valuation engine.

Implements multiple DCF model variants:
- Simple 5-year single-stage DCF
- 10-year two-stage DCF (growth fades from Stage 1 to terminal)
- Excel-style full DCF (EV -> Equity -> per-share value)

Also includes Damodaran sector WACC reference data and smart-default
assumption generation from CAPM beta and analyst growth estimates.
"""

from typing import Dict, List, Optional

from server.utils.safe_float import _safe_float

try:
    from scipy.optimize import brentq
except ImportError:
    brentq = None  # type: ignore[assignment]

try:
    import yfinance as yf
except ImportError:
    yf = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Damodaran sector WACC reference (approx. 2024/2025 baseline)
# ---------------------------------------------------------------------------

DAMODARAN_WACC: Dict[str, float] = {
    "Software": 8.5,
    "Retail": 7.5,
    "Hardware": 9.0,
    "Financials": 8.0,
    "Healthcare": 7.2,
    "Consumer": 7.5,
    "Technology": 8.5,
    "Industrial": 7.8,
    "Energy": 8.2,
    "Utilities": 6.5,
}

DAMODARAN_ERP_PCT: float = 4.6
"""US Equity Risk Premium (Damodaran estimate)."""

DAMODARAN_RF_PCT: float = 4.2
"""10-year risk-free rate (Damodaran estimate)."""


# ---------------------------------------------------------------------------
# DCF models
# ---------------------------------------------------------------------------

def dcf_intrinsic_value(
    fcf: float,
    wacc: float,
    terminal_growth: float,
    fcf_growth: float,
    years: int = 5,
) -> float:
    """5-year single-stage DCF returning enterprise value.

    Projects FCF at *fcf_growth* for *years* periods, then computes a
    Gordon Growth terminal value discounted at *wacc*.
    """
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


def dcf_10y_2stage(
    fcf: float,
    wacc: float,
    term_growth: float,
    fcf_growth: float,
) -> float:
    """10-year two-stage DCF.

    Stage 1 (Y1-5): FCF grows at *fcf_growth*.
    Stage 2 (Y6-10): growth linearly fades to *term_growth*.
    Terminal value at Y10 using Gordon Growth.
    """
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


def excel_style_dcf(
    fcf_base: float,
    wacc: float,
    term_growth: float,
    fcf_growth: float,
    total_debt: float,
    cash: float,
    shares: float,
) -> Dict[str, Optional[float]]:
    """Full DCF: EV -> Equity Value -> Value per Share.

    Returns
    -------
    dict
        Keys: ``ev``, ``equity_value``, ``value_per_share``, ``shares``.
    """
    ev = dcf_10y_2stage(fcf_base, wacc, term_growth, fcf_growth)
    equity = ev - total_debt + cash
    shares_safe = float(shares) if (shares is not None and float(shares) > 0) else None
    value_per_share = (equity / shares_safe) if shares_safe else None
    return {
        "ev": ev,
        "equity_value": equity,
        "value_per_share": value_per_share,
        "shares": shares_safe,
    }


# ---------------------------------------------------------------------------
# WACC helpers
# ---------------------------------------------------------------------------

def reverse_dcf(
    current_price: float,
    shares: float,
    total_debt: float,
    cash: float,
    wacc: float,
    term_growth: float,
    fcf_base: float,
    projection_years: int = 10,
) -> Optional[float]:
    """Solve for the implied FCF growth rate that produces the current market price.

    Uses Brent's root-finding method (scipy.optimize.brentq) to find the
    growth rate *g* such that ``excel_style_dcf(..., g)["value_per_share"] == current_price``.

    Returns
    -------
    float | None
        Implied annual FCF growth rate (decimal), or None if no solution is found.
    """
    if brentq is None:
        return None
    if shares <= 0 or current_price <= 0 or wacc <= term_growth:
        return None

    def _objective(g: float) -> float:
        result = excel_style_dcf(fcf_base, wacc, term_growth, g, total_debt, cash, shares)
        vps = result.get("value_per_share")
        if vps is None:
            return -current_price
        return vps - current_price

    try:
        implied_growth = brentq(_objective, -0.50, 1.00, xtol=1e-6, maxiter=200)
        return round(implied_growth, 6)
    except (ValueError, RuntimeError):
        return None


def _damodaran_wacc_for_sector(sector: str) -> float:
    """Map a yfinance sector string to closest Damodaran WACC (default 8.0%)."""
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


# ---------------------------------------------------------------------------
# Smart defaults
# ---------------------------------------------------------------------------

def get_dcf_smart_defaults(ticker: str) -> Dict[str, float]:
    """Auto-generate WACC, Terminal Growth, and FCF Growth from CAPM beta and analyst estimates.

    Returns
    -------
    dict
        Keys: ``wacc_pct``, ``term_growth_pct``, ``fcf_growth_pct``.
    """
    out: Dict[str, float] = {"wacc_pct": 10.0, "term_growth_pct": 2.5, "fcf_growth_pct": 8.0}
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
