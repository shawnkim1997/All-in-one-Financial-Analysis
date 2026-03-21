"""
Analyst estimates — earnings & revenue forecasts, consensus targets.
"""
import streamlit as st
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=600)
def get_analyst_estimates(ticker: str) -> dict:
    """Fetch analyst earnings and revenue estimates from yfinance."""
    if not yf or not ticker:
        return {}
    try:
        t = yf.Ticker(ticker)
        result = {}

        # Earnings estimates
        ee = getattr(t, "earnings_estimate", None)
        if ee is not None and not ee.empty:
            result["earnings_estimate"] = ee

        # Revenue estimates
        re = getattr(t, "revenue_estimate", None)
        if re is not None and not re.empty:
            result["revenue_estimate"] = re

        # EPS trend
        et = getattr(t, "eps_trend", None)
        if et is not None and not et.empty:
            result["eps_trend"] = et

        # Earnings history
        eh = getattr(t, "earnings_history", None)
        if eh is not None and not eh.empty:
            result["earnings_history"] = eh

        # Growth estimates
        ge = getattr(t, "growth_estimates", None)
        if ge is not None and not ge.empty:
            result["growth_estimates"] = ge

        # Price targets
        info = t.info or {}
        result["targets"] = {
            "current": info.get("currentPrice") or info.get("regularMarketPrice"),
            "mean": info.get("targetMeanPrice"),
            "high": info.get("targetHighPrice"),
            "low": info.get("targetLowPrice"),
            "median": info.get("targetMedianPrice"),
            "recommendation": info.get("recommendationKey", "N/A"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
        }

        return result
    except Exception:
        return {}


@st.cache_data(ttl=600)
def get_earnings_dates(ticker: str) -> pd.DataFrame:
    """Fetch historical and upcoming earnings dates with surprise data."""
    if not yf or not ticker:
        return pd.DataFrame()
    try:
        t = yf.Ticker(ticker)
        dates = t.earnings_dates
        if dates is not None and not dates.empty:
            return dates.head(12)
    except Exception:
        pass
    return pd.DataFrame()


def format_estimate_table(df: pd.DataFrame) -> pd.DataFrame:
    """Format estimate DataFrame for display with proper number formatting."""
    if df is None or df.empty:
        return pd.DataFrame()
    display = df.copy()
    for col in display.columns:
        display[col] = display[col].apply(
            lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) and v == v else "N/A"
        )
    return display
