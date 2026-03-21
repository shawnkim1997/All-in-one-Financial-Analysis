"""Stock screener service."""

from __future__ import annotations


async def run_screener(filters: dict, universe: str = "sp500") -> list[dict]:
    """Run simple screening against S&P 500 universe."""
    import pandas as pd
    import yfinance as yf

    try:
        table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
        tickers = table["Symbol"].astype(str).tolist()
    except Exception:
        tickers = []

    results = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info or {}
            pe = info.get("forwardPE")
            mcap = info.get("marketCap")
            sector = info.get("sector")
            div = info.get("dividendYield")
            if filters.get("pe_max") and ((pe or 9999) > filters["pe_max"]):
                continue
            if filters.get("sector") and sector != filters["sector"]:
                continue
            if filters.get("market_cap_min") and ((mcap or 0) < filters["market_cap_min"]):
                continue
            if filters.get("div_yield_min") and (((div or 0) * 100) < filters["div_yield_min"]):
                continue
            results.append(
                {
                    "ticker": ticker,
                    "name": info.get("shortName", ""),
                    "sector": sector or "",
                    "market_cap": mcap,
                    "pe": pe,
                    "div_yield": (div * 100) if div is not None else None,
                    "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "change_pct": info.get("regularMarketChangePercent"),
                }
            )
        except Exception:
            continue
    return results
