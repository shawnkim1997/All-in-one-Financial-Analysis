import streamlit as st
import pandas as pd
from utils.formatting import _safe_float

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=300)
def get_technical_indicators(ticker: str) -> dict:
    """RSI(14), SMA(50), SMA(200), support/resistance, 52-week range."""
    out = {"rsi_14": None, "sma_50": None, "sma_200": None, "current_price": None, "support": None, "resistance": None, "52w_high": None, "52w_low": None}
    if not yf or not ticker:
        return out
    try:
        t = yf.Ticker(ticker.upper())
        hist = t.history(period="1y")
        if hist is None or hist.empty or len(hist) < 14:
            return out
        close = hist["Close"]
        out["current_price"] = float(close.iloc[-1])
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        out["rsi_14"] = round(float(rsi.iloc[-1]), 1) if not pd.isna(rsi.iloc[-1]) else None
        if len(close) >= 50:
            out["sma_50"] = round(float(close.rolling(50).mean().iloc[-1]), 2)
        if len(close) >= 200:
            out["sma_200"] = round(float(close.rolling(200).mean().iloc[-1]), 2)
        out["52w_high"] = round(float(close.max()), 2)
        out["52w_low"] = round(float(close.min()), 2)
        recent = close.tail(20)
        out["support"] = round(float(recent.min()), 2)
        out["resistance"] = round(float(recent.max()), 2)
        return out
    except Exception:
        return out


@st.cache_data(ttl=600)
def get_risk_analysis(ticker: str) -> list:
    """Risk factors with estimated EPS impact."""
    if not yf or not ticker:
        return []
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info or {}
        eps = info.get("trailingEps") or info.get("forwardEps") or 1.0
        beta = info.get("beta") or 1.0
        debt_equity = info.get("debtToEquity") or 0
        margin = info.get("operatingMargins") or 0
        risks = []
        impact = round(eps * (beta - 1) * 0.1, 2) if beta > 1 else round(eps * 0.05, 2)
        risks.append({"risk": "Market / Macro Risk", "severity": "High" if beta > 1.3 else "Medium", "eps_impact": f"-${abs(impact):.2f}", "description": f"Beta {beta:.2f}"})
        comp_impact = round(eps * 0.08, 2)
        risks.append({"risk": "Competitive Pressure", "severity": "High" if margin < 0.15 else "Medium", "eps_impact": f"-${abs(comp_impact):.2f}", "description": f"Op margin {margin*100:.1f}%"})
        lev_impact = round(eps * 0.06, 2) if debt_equity and debt_equity > 100 else round(eps * 0.03, 2)
        risks.append({"risk": "Financial / Leverage", "severity": "High" if (debt_equity or 0) > 150 else ("Medium" if (debt_equity or 0) > 80 else "Low"), "eps_impact": f"-${abs(lev_impact):.2f}", "description": f"D/E {debt_equity:.0f}%" if debt_equity else "D/E N/A"})
        risks.append({"risk": "Regulatory / Legal", "severity": "Medium", "eps_impact": f"-${abs(round(eps * 0.05, 2)):.2f}", "description": "Regulatory changes"})
        risks.append({"risk": "Currency / FX", "severity": "Medium", "eps_impact": f"-${abs(round(eps * 0.04, 2)):.2f}", "description": "FX exposure"})
        risks.append({"risk": "Supply Chain", "severity": "Medium", "eps_impact": f"-${abs(round(eps * 0.05, 2)):.2f}", "description": "Component/logistics risk"})
        return risks
    except Exception:
        return []


@st.cache_data(ttl=120)
def _get_ticker_bar_data() -> list:
    """Fetch major index/crypto prices for top ticker bar."""
    items = []
    tickers_bar = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "KOSPI": "^KS11", "NIKKEI": "^N225", "BTC": "BTC-USD", "ETH": "ETH-USD"}
    for label, sym in tickers_bar.items():
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            price = info.get("regularMarketPrice") or info.get("previousClose") or 0
            prev = info.get("regularMarketPreviousClose") or info.get("previousClose") or price
            change_pct = ((price - prev) / prev * 100) if prev else 0
            items.append({"label": label, "price": price, "change": change_pct})
        except Exception:
            items.append({"label": label, "price": 0, "change": 0})
    return items


@st.cache_data(ttl=300)
def _fetch_news_rss(ticker_sym: str, company_name: str = "") -> list:
    """Fetch news from Google News RSS. Returns list of {title, source, url, published}."""
    import feedparser
    items = []
    query = ticker_sym if not company_name else company_name
    try:
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={query}+stock&hl=en-US&gl=US&ceid=US:en")
        for entry in (feed.entries or [])[:15]:
            items.append({
                "title": entry.get("title", ""),
                "source": entry.get("source", {}).get("title", "Google News") if hasattr(entry.get("source", ""), "get") else "Google News",
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
    except Exception:
        pass
    return items
