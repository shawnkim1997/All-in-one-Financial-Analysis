"""Heatmap data service for index constituents."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf


async def get_index_constituents(index_name: str) -> list[str]:
    name = (index_name or "").lower().strip()
    if name == "sp500":
        try:
            table = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
            return table["Symbol"].astype(str).str.replace(".", "-", regex=False).tolist()
        except Exception:
            return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "TSLA", "UNH", "XOM"]
    if name == "nasdaq100":
        try:
            table = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100")[4]
            return table["Ticker"].astype(str).tolist()
        except Exception:
            return ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "NFLX"]
    if name == "kospi":
        return [
            "005930.KS", "000660.KS", "035420.KS", "051910.KS", "006400.KS",
            "035720.KS", "068270.KS", "028260.KS", "105560.KS", "012330.KS",
            "055550.KS", "034730.KS", "003550.KS", "015760.KS", "066570.KS",
            "032830.KS", "096770.KS", "009150.KS", "003670.KS", "018260.KS",
        ]
    if name == "ftse100":
        return ["SHEL.L", "AZN.L", "HSBA.L", "ULVR.L", "BP.L", "GSK.L", "RIO.L", "LSEG.L"]
    return []


def _calc_change_pct(ticker: str) -> float:
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        if hist is not None and len(hist) >= 2:
            prev = float(hist["Close"].iloc[-2])
            cur = float(hist["Close"].iloc[-1])
            if prev != 0:
                return round((cur - prev) / prev * 100, 2)
    except Exception:
        pass
    return 0.0


async def get_heatmap_data(index_name: str, top_n: int = 50) -> list[dict[str, Any]]:
    tickers = (await get_index_constituents(index_name))[: max(top_n, 1)]
    out: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info or {}
            mcap = info.get("marketCap")
            if not mcap or float(mcap) <= 0:
                continue
            out.append(
                {
                    "ticker": ticker.replace(".KS", "").replace(".L", ""),
                    "name": info.get("shortName") or info.get("longName") or ticker,
                    "sector": info.get("sector") or "Other",
                    "market_cap": float(mcap),
                    "change_pct": _calc_change_pct(ticker),
                }
            )
        except Exception:
            continue
    return sorted(out, key=lambda x: x["market_cap"], reverse=True)

