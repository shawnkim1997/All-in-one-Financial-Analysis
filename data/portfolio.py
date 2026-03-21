"""
Portfolio data layer — fetch current prices, earnings calendar, dividends, sector info, news for portfolio holdings.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    yf = None


@st.cache_data(ttl=120)
def get_portfolio_prices(tickers: tuple) -> dict:
    """Fetch current price, previous close, and day change for each ticker.
    Returns {ticker: {"price": float, "prev_close": float, "change_pct": float}}
    """
    if not yf or not tickers:
        return {}
    result = {}
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            prev = info.get("regularMarketPreviousClose") or info.get("previousClose")
            if price and prev and prev != 0:
                change = (price - prev) / prev * 100
            else:
                change = 0.0
            result[sym] = {"price": price, "prev_close": prev, "change_pct": round(change, 2)}
        except Exception:
            result[sym] = {"price": None, "prev_close": None, "change_pct": 0.0}
    return result


@st.cache_data(ttl=300)
def get_sector_allocation(tickers: tuple) -> dict:
    """Return {ticker: sector} for pie chart. Uses yfinance .info."""
    if not yf or not tickers:
        return {}
    result = {}
    for sym in tickers:
        try:
            info = yf.Ticker(sym).info or {}
            result[sym] = info.get("sector") or info.get("sectorDisp") or "Other"
        except Exception:
            result[sym] = "Other"
    return result


@st.cache_data(ttl=600)
def get_earnings_calendar(tickers: tuple) -> list:
    """Return list of upcoming earnings: [{"ticker", "name", "date", "days_until"}]."""
    if not yf or not tickers:
        return []
    events = []
    now = datetime.now()
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            cal = t.calendar
            if cal is None:
                continue
            # yfinance returns dict or DataFrame
            if isinstance(cal, pd.DataFrame):
                if "Earnings Date" in cal.index:
                    dates = cal.loc["Earnings Date"]
                    ed = pd.Timestamp(dates.iloc[0]) if len(dates) > 0 else None
                else:
                    continue
            elif isinstance(cal, dict):
                ed_val = cal.get("Earnings Date")
                if isinstance(ed_val, list) and ed_val:
                    ed = pd.Timestamp(ed_val[0])
                elif ed_val:
                    ed = pd.Timestamp(ed_val)
                else:
                    continue
            else:
                continue
            if ed and ed >= pd.Timestamp(now):
                delta = (ed - pd.Timestamp(now)).days
                name = (t.info or {}).get("shortName", sym)
                events.append({
                    "ticker": sym, "name": name,
                    "date": ed.strftime("%m/%d"), "days_until": delta,
                })
        except Exception:
            continue
    events.sort(key=lambda x: x["days_until"])
    return events


@st.cache_data(ttl=600)
def get_dividend_schedule(tickers: tuple) -> list:
    """Return upcoming dividend info: [{"ticker", "name", "ex_date", "amount", "yield_pct"}]."""
    if not yf or not tickers:
        return []
    divs = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            div_rate = info.get("dividendRate")
            div_yield = info.get("dividendYield")
            ex_date = info.get("exDividendDate")
            if not div_rate and not div_yield:
                continue
            name = info.get("shortName", sym)
            ex_str = ""
            if ex_date:
                try:
                    ex_dt = datetime.fromtimestamp(ex_date) if isinstance(ex_date, (int, float)) else ex_date
                    ex_str = ex_dt.strftime("%m/%d/%Y") if hasattr(ex_dt, "strftime") else str(ex_date)
                except Exception:
                    ex_str = str(ex_date)
            divs.append({
                "ticker": sym, "name": name, "ex_date": ex_str,
                "amount": f"${div_rate:.2f}" if div_rate else "N/A",
                "yield_pct": f"{div_yield * 100:.2f}%" if div_yield else "N/A",
            })
        except Exception:
            continue
    return divs


@st.cache_data(ttl=300)
def get_portfolio_news(tickers: tuple, max_per_ticker: int = 3) -> list:
    """Fetch recent news for portfolio tickers via yfinance."""
    if not yf or not tickers:
        return []
    all_news = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            news_list = t.news or []
            for n in news_list[:max_per_ticker]:
                all_news.append({
                    "ticker": sym,
                    "title": n.get("title", ""),
                    "publisher": n.get("publisher", ""),
                    "link": n.get("link", ""),
                    "published": n.get("providerPublishTime", 0),
                })
        except Exception:
            continue
    all_news.sort(key=lambda x: x.get("published", 0), reverse=True)
    return all_news[:20]


@st.cache_data(ttl=300)
def get_sparkline_data(ticker: str, period: str = "1y") -> list:
    """Return list of close prices for sparkline chart."""
    if not yf or not ticker:
        return []
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist is not None and not hist.empty and "Close" in hist.columns:
            return hist["Close"].tolist()
    except Exception:
        pass
    return []
