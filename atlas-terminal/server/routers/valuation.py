"""Valuation router -- DCF calculation, smart defaults, analyst consensus,
sensitivity analysis, Monte Carlo simulation, reverse DCF, and tornado charts."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

router = APIRouter()


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        import math
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


class DCFInputsBody(BaseModel):
    ticker: str = ""
    base_fcf: float = 0
    fcf: float = 0  # alias
    shares: float = 0
    shares_outstanding: float = 0  # alias
    total_debt: float = 0
    cash: float = 0
    wacc: float = 0.09
    terminal_growth: float = 0.025
    fcf_growth: float = 0.10
    fcf_growth_rate: float = 0  # alias


@router.get("/dcf-inputs/{ticker}", summary="Auto-fill DCF inputs from market data")
async def dcf_inputs(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        cf = t.cashflow
        bs = t.balance_sheet

        fcf = _safe_float(info.get("freeCashflow"))
        if not fcf and cf is not None and not cf.empty:
            col = cf.columns[0]
            ocf = _safe_float(cf.loc["Operating Cash Flow"][col]) if "Operating Cash Flow" in cf.index else 0
            capex = _safe_float(cf.loc["Capital Expenditure"][col]) if "Capital Expenditure" in cf.index else 0
            fcf = ocf + capex

        total_debt = _safe_float(info.get("totalDebt"))
        cash = _safe_float(info.get("totalCash"))
        shares = _safe_float(info.get("sharesOutstanding"))

        return {"fcf": fcf, "total_debt": total_debt, "cash": cash, "shares": shares}
    except Exception:
        return {"fcf": None, "total_debt": 0, "cash": 0, "shares": None}


@router.post("/dcf", summary="Calculate 3-scenario DCF valuation")
async def calculate_dcf(inputs: DCFInputsBody):
    try:
        import yfinance as yf

        base_fcf = inputs.base_fcf or inputs.fcf
        _shares = inputs.shares or inputs.shares_outstanding
        wacc = inputs.wacc
        tg = inputs.terminal_growth
        fcf_g = inputs.fcf_growth or inputs.fcf_growth_rate or 0.10
        projection_years = 10

        def _dcf(fcf, w, g, tgr):
            if w <= tgr:
                return None
            projected = []
            current = fcf
            for _ in range(projection_years):
                current *= (1 + g)
                projected.append(current)

            terminal = projected[-1] * (1 + tgr) / (w - tgr)
            pv_fcfs = sum(f / (1 + w) ** (i + 1) for i, f in enumerate(projected))
            pv_terminal = terminal / (1 + w) ** projection_years
            ev = pv_fcfs + pv_terminal
            eq = ev - inputs.total_debt + inputs.cash
            per_share = eq / _shares if _shares else None
            return per_share

        base_val = _dcf(base_fcf, wacc, fcf_g, tg)
        bull_val = _dcf(base_fcf, max(wacc - 0.005, tg + 0.005), fcf_g + 0.02, tg)
        bear_val = _dcf(base_fcf, wacc + 0.01, max(fcf_g - 0.03, tg + 0.005), tg)

        # Get current price
        current_price = None
        ticker_sym = inputs.ticker or ""
        if ticker_sym:
            try:
                t = yf.Ticker(ticker_sym.upper())
                current_price = _safe_float(t.info.get("currentPrice") or t.info.get("regularMarketPrice"))
            except Exception:
                pass

        def _upside(val):
            if val is None or current_price is None or current_price == 0:
                return 0
            return round((val / current_price - 1) * 100, 1)

        return {
            "base": round(base_val, 2) if base_val else None,
            "bull": round(bull_val, 2) if bull_val else None,
            "bear": round(bear_val, 2) if bear_val else None,
            "current_price": current_price,
            "scenarios": {
                "bull": {"intrinsic_value": round(bull_val, 2) if bull_val else None, "upside": _upside(bull_val)},
                "base": {"intrinsic_value": round(base_val, 2) if base_val else None, "upside": _upside(base_val)},
                "bear": {"intrinsic_value": round(bear_val, 2) if bear_val else None, "upside": _upside(bear_val)},
            },
        }
    except Exception:
        return {"base": None, "bull": None, "bear": None, "current_price": None}


@router.get("/smart-defaults/{ticker}", summary="Smart DCF defaults")
async def smart_defaults(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}

        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

        # Sector-based WACC heuristics
        wacc_map = {
            "Technology": 10, "Healthcare": 9, "Financial Services": 8,
            "Consumer Cyclical": 9, "Consumer Defensive": 7.5,
            "Industrials": 8.5, "Energy": 10.5, "Utilities": 6.5,
            "Real Estate": 7, "Communication Services": 9, "Basic Materials": 9,
        }
        wacc = wacc_map.get(sector, 9.0)
        rev_growth = _safe_float(info.get("revenueGrowth", 0.1)) * 100
        fcf_growth = min(max(rev_growth, 3), 35)

        return {
            "wacc": wacc, "terminal_growth": 2.5, "fcf_growth": round(fcf_growth, 1),
            "sector": sector, "industry": industry,
        }
    except Exception:
        return {"wacc": 9, "terminal_growth": 2.5, "fcf_growth": 10, "sector": "N/A", "industry": "N/A"}


class SensitivityBody(BaseModel):
    fcf: float = 0
    total_debt: float = 0
    cash: float = 0
    shares: float = 0
    wacc: float = 0.09
    terminal_growth: float = 0.025
    fcf_growth: float = 0.10


class MonteCarloBody(BaseModel):
    ticker: str = ""
    fcf: float = 0
    wacc_mean: float = 0.09
    wacc_std: float = 0.015
    growth_mean: float = 0.10
    growth_std: float = 0.03
    term_growth: float = 0.025
    total_debt: float = 0
    cash: float = 0
    shares: float = 0
    n_simulations: int = 5000


class ReverseDCFBody(BaseModel):
    ticker: str = ""
    fcf: float = 0
    shares: float = 0
    total_debt: float = 0
    cash: float = 0
    wacc: float = 0.09
    terminal_growth: float = 0.025


@router.post("/sensitivity", summary="Sensitivity matrix (WACC vs Terminal Growth)")
async def sensitivity_analysis(body: SensitivityBody):
    try:
        from server.services.sensitivity import build_sensitivity_matrix
        result = build_sensitivity_matrix(
            fcf=body.fcf, total_debt=body.total_debt, cash=body.cash,
            shares=body.shares, base_wacc=body.wacc, base_tg=body.terminal_growth,
            fcf_growth=body.fcf_growth,
        )
        return result
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/tornado", summary="Tornado chart data")
async def tornado_chart(body: SensitivityBody):
    try:
        from server.services.sensitivity import build_tornado_data
        result = build_tornado_data(
            fcf=body.fcf, wacc=body.wacc, tg=body.terminal_growth,
            growth=body.fcf_growth, debt=body.total_debt,
            cash=body.cash, shares=body.shares,
        )
        return {"data": result}
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/monte-carlo", summary="Monte Carlo DCF simulation")
async def monte_carlo_dcf(body: MonteCarloBody):
    try:
        import yfinance as yf
        from server.services.monte_carlo import run_monte_carlo_dcf

        current_price = None
        if body.ticker:
            try:
                t = yf.Ticker(body.ticker.upper())
                current_price = _safe_float(t.info.get("currentPrice") or t.info.get("regularMarketPrice"))
            except Exception:
                pass

        result = run_monte_carlo_dcf(
            fcf=body.fcf, wacc_mean=body.wacc_mean, wacc_std=body.wacc_std,
            growth_mean=body.growth_mean, growth_std=body.growth_std,
            term_growth=body.term_growth, total_debt=body.total_debt,
            cash=body.cash, shares=body.shares, n_simulations=body.n_simulations,
            current_price=current_price,
        )
        values = result.get("values", [])
        if values:
            import numpy as np
            arr = np.array(values)
            counts, bin_edges = np.histogram(arr, bins=50)
            result["histogram"] = {
                "counts": counts.tolist(),
                "bin_edges": [round(b, 2) for b in bin_edges.tolist()],
            }
            result["values"] = []
        return result
    except Exception as exc:
        return {"error": str(exc)}


@router.post("/reverse-dcf", summary="Reverse DCF — implied growth rate")
async def reverse_dcf_endpoint(body: ReverseDCFBody):
    try:
        import yfinance as yf
        from server.services.dcf_engine import reverse_dcf

        current_price = None
        if body.ticker:
            try:
                t = yf.Ticker(body.ticker.upper())
                current_price = _safe_float(t.info.get("currentPrice") or t.info.get("regularMarketPrice"))
            except Exception:
                pass

        if not current_price:
            return {"implied_growth": None, "current_price": None, "error": "No current price"}

        implied = reverse_dcf(
            current_price=current_price, shares=body.shares,
            total_debt=body.total_debt, cash=body.cash,
            wacc=body.wacc, term_growth=body.terminal_growth,
            fcf_base=body.fcf,
        )
        return {
            "implied_growth": round(implied * 100, 2) if implied is not None else None,
            "current_price": current_price,
        }
    except Exception as exc:
        return {"error": str(exc)}


@router.get("/consensus/{ticker}", summary="Analyst consensus data")
async def analyst_consensus(ticker: str):
    try:
        import yfinance as yf
        t = yf.Ticker(ticker.upper())
        info = t.info or {}

        return {
            "target_mean": _safe_float(info.get("targetMeanPrice"), None),
            "target_high": _safe_float(info.get("targetHighPrice"), None),
            "target_low": _safe_float(info.get("targetLowPrice"), None),
            "target_median": _safe_float(info.get("targetMedianPrice"), None),
            "recommendation": info.get("recommendationKey", "N/A"),
            "num_analysts": info.get("numberOfAnalystOpinions", 0),
        }
    except Exception:
        return {"target_mean": None, "target_high": None, "target_low": None, "target_median": None, "recommendation": "N/A", "num_analysts": 0}
