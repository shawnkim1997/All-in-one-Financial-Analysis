"""Analyst estimates router -- earnings, revenue, EPS, growth, and price targets."""

from typing import Any, Dict, List, Optional

import logging
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_df_to_dict(df: Any) -> List[Dict[str, Any]]:
    """Convert a pandas DataFrame to a list of dicts, handling NaN safely.

    Returns an empty list when the input is ``None`` or not a DataFrame.
    """
    try:
        import pandas as pd

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return []
        return df.fillna(0).reset_index().to_dict(orient="records")
    except Exception:
        logger.exception("estimates endpoint failed")
        return []


def _safe_value(val: Any, default: Any = None) -> Any:
    """Return *val* unless it is NaN / None, in which case return *default*."""
    import math

    if val is None:
        return default
    try:
        if math.isnan(val):
            return default
    except (TypeError, ValueError):
        pass
    return val


@router.get(
    "/{ticker}",
    summary="Full analyst estimates bundle",
)
async def full_estimates(ticker: str) -> Dict[str, Any]:
    """Return a comprehensive estimates bundle for *ticker*.

    Includes earnings estimate, revenue estimate, EPS trend, growth
    estimates, and price targets sourced from yfinance.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        info: Dict[str, Any] = t.info or {}

        earnings_estimate = _safe_df_to_dict(
            getattr(t, "earnings_estimate", None),
        )
        revenue_estimate = _safe_df_to_dict(
            getattr(t, "revenue_estimate", None),
        )
        eps_trend = _safe_df_to_dict(
            getattr(t, "eps_trend", None),
        )
        growth_estimates = _safe_df_to_dict(
            getattr(t, "growth_estimates", None),
        )

        price_targets: Dict[str, Any] = {
            "current": _safe_value(info.get("currentPrice")),
            "mean": _safe_value(info.get("targetMeanPrice")),
            "high": _safe_value(info.get("targetHighPrice")),
            "low": _safe_value(info.get("targetLowPrice")),
            "median": _safe_value(info.get("targetMedianPrice")),
            "recommendation": info.get("recommendationKey", ""),
            "num_analysts": _safe_value(info.get("numberOfAnalystOpinions"), 0),
        }

        return {
            "ticker": ticker.upper(),
            "earnings_estimate": earnings_estimate,
            "revenue_estimate": revenue_estimate,
            "eps_trend": eps_trend,
            "growth_estimates": growth_estimates,
            "price_targets": price_targets,
        }
    except Exception:
        logger.exception("estimates endpoint failed")
        return {
            "ticker": ticker.upper(),
            "earnings_estimate": [],
            "revenue_estimate": [],
            "eps_trend": [],
            "growth_estimates": [],
            "price_targets": {"current": None, "mean": None, "high": None, "low": None, "median": None, "recommendation": "", "num_analysts": 0},
        }


@router.get(
    "/{ticker}/earnings-dates",
    summary="Upcoming and past earnings dates",
)
async def earnings_dates(ticker: str) -> Dict[str, Any]:
    """Return upcoming and past earnings dates with surprise data.

    Uses ``yfinance.Ticker.earnings_dates`` and ``earnings_history``.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())

        dates_df = getattr(t, "earnings_dates", None)
        dates_records = _safe_df_to_dict(dates_df)

        history_df = getattr(t, "earnings_history", None)
        history_records = _safe_df_to_dict(history_df)

        return {
            "ticker": ticker.upper(),
            "earnings_dates": dates_records,
            "earnings_history": history_records,
        }
    except Exception:
        logger.exception("estimates endpoint failed")
        return {
            "ticker": ticker.upper(),
            "earnings_dates": [],
            "earnings_history": [],
        }


@router.get(
    "/{ticker}/growth",
    summary="Growth estimates comparison",
)
async def growth_estimates(ticker: str) -> Dict[str, Any]:
    """Return growth estimates with current-quarter, next-quarter,
    current-year, and next-year comparisons.
    """
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())

        growth_df = getattr(t, "growth_estimates", None)
        growth_records = _safe_df_to_dict(growth_df)

        eps_trend_df = getattr(t, "eps_trend", None)
        eps_records = _safe_df_to_dict(eps_trend_df)

        return {
            "ticker": ticker.upper(),
            "growth_estimates": growth_records,
            "eps_trend": eps_records,
        }
    except Exception:
        logger.exception("estimates endpoint failed")
        return {
            "ticker": ticker.upper(),
            "growth_estimates": [],
            "eps_trend": [],
        }
