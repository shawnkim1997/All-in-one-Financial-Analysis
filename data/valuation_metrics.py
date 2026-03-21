"""
Valuation metrics — PER, PBR, PSR, P/OCF, EV/EBITDA with historical & industry comparison.
"""
import streamlit as st
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from yahooquery import Ticker as YQTicker
except ImportError:
    YQTicker = None


@st.cache_data(ttl=300)
def get_valuation_multiples(ticker: str) -> dict:
    """Fetch current valuation multiples for a ticker."""
    if not yf or not ticker:
        return {}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        mcap = info.get("marketCap") or 0
        # P/OCF calculation
        ocf = info.get("operatingCashflow")
        shares = info.get("sharesOutstanding") or 1
        p_ocf = (price / (ocf / shares)) if ocf and shares and ocf > 0 else None

        return {
            "PER": info.get("trailingPE"),
            "Forward PER": info.get("forwardPE"),
            "PBR": info.get("priceToBook"),
            "PSR": info.get("priceToSalesTrailing12Months"),
            "P/OCF": round(p_ocf, 2) if p_ocf else None,
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "EV/Revenue": info.get("enterpriseToRevenue"),
            "PEG": info.get("pegRatio"),
            "Dividend Yield": info.get("dividendYield"),
            "Price": price,
            "Market Cap": mcap,
            "52W High": info.get("fiftyTwoWeekHigh"),
            "52W Low": info.get("fiftyTwoWeekLow"),
            "Beta": info.get("beta"),
        }
    except Exception:
        return {}


@st.cache_data(ttl=600)
def get_historical_multiples(ticker: str) -> dict:
    """Calculate 5Y average PE, PB, PS from historical data."""
    if not yf or not ticker:
        return {}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="5y", interval="1mo")
        if hist is None or hist.empty:
            return {}
        eps = info.get("trailingEps")
        bvps = info.get("bookValue")

        result = {}
        if eps and eps > 0:
            pe_series = hist["Close"] / eps
            result["5Y Avg PER"] = round(pe_series.mean(), 2)
            result["5Y High PER"] = round(pe_series.max(), 2)
            result["5Y Low PER"] = round(pe_series.min(), 2)
        if bvps and bvps > 0:
            pb_series = hist["Close"] / bvps
            result["5Y Avg PBR"] = round(pb_series.mean(), 2)
        return result
    except Exception:
        return {}


@st.cache_data(ttl=600)
def get_industry_avg_multiples(ticker: str) -> dict:
    """Get industry peer average multiples for comparison."""
    if not yf or not ticker:
        return {}
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        industry = info.get("industry", "")
        sector = info.get("sector", "")
        if not industry:
            return {"industry": "N/A"}

        # Use sector-based peer mapping
        from config.constants import SECTORS
        peers = []
        sector_lower = sector.lower() if sector else ""
        for sec_name, tickers_list in SECTORS.items():
            if any(k in sector_lower for k in sec_name.lower().split()):
                peers = [p for p in tickers_list if p != ticker.upper()][:4]
                break
        if not peers:
            return {"industry": industry}

        pe_vals, pb_vals, ps_vals = [], [], []
        for p in peers:
            try:
                pi = yf.Ticker(p).info or {}
                if pi.get("trailingPE") and pi["trailingPE"] > 0:
                    pe_vals.append(pi["trailingPE"])
                if pi.get("priceToBook") and pi["priceToBook"] > 0:
                    pb_vals.append(pi["priceToBook"])
                if pi.get("priceToSalesTrailing12Months"):
                    ps_vals.append(pi["priceToSalesTrailing12Months"])
            except Exception:
                continue

        result = {"industry": industry, "peers": peers}
        if pe_vals:
            result["Industry Avg PER"] = round(sum(pe_vals) / len(pe_vals), 2)
        if pb_vals:
            result["Industry Avg PBR"] = round(sum(pb_vals) / len(pb_vals), 2)
        if ps_vals:
            result["Industry Avg PSR"] = round(sum(ps_vals) / len(ps_vals), 2)
        return result
    except Exception:
        return {}


@st.cache_data(ttl=300)
def get_pe_history_chart_data(ticker: str) -> pd.DataFrame:
    """Return monthly close prices for 5Y PE chart overlay."""
    if not yf or not ticker:
        return pd.DataFrame()
    try:
        hist = yf.Ticker(ticker).history(period="5y", interval="1mo")
        if hist is not None and not hist.empty:
            return hist[["Close"]].reset_index()
    except Exception:
        pass
    return pd.DataFrame()
