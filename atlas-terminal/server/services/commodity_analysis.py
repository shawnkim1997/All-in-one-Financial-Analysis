"""Commodity future analysis helpers."""

from __future__ import annotations

from typing import Any

from server.utils.ticker_utils import COMMODITY_FUTURES

COMMODITY_RELATED: dict[str, list[str]] = {
    "GC=F": ["GLD", "SI=F", "DX-Y.NYB", "^TNX"],
    "CL=F": ["USO", "BZ=F", "XLE", "^GSPC"],
    "SI=F": ["SLV", "GC=F", "HG=F", "^GSPC"],
    "NG=F": ["UNG", "CL=F", "XLE"],
}


def _get_related_assets(ticker: str) -> list[str]:
    return COMMODITY_RELATED.get(ticker.upper(), [])


async def compute_commodity_correlations(ticker: str, period: str = "1y") -> dict:
    import yfinance as yf

    t = ticker.upper()
    related = _get_related_assets(t)
    if not related:
        return {}
    all_tickers = [t] + related
    data = yf.download(all_tickers, period=period, auto_adjust=True, progress=False)
    if data is None or data.empty:
        return {}
    close = data["Close"] if "Close" in data else data
    returns = close.pct_change().dropna()
    if returns is None or returns.empty or t not in returns.columns:
        return {}
    corr = returns.corr()
    result = {}
    for r in related:
        if r in corr.columns:
            result[r] = round(float(corr.loc[t, r]), 2)
    return result


async def get_commodity_overview(ticker: str) -> dict:
    import yfinance as yf

    t = ticker.upper()
    y = yf.Ticker(t)
    info = y.info or {}
    hist_1y = y.history(period="1y", auto_adjust=True)
    hist_10y = y.history(period="10y", auto_adjust=True)

    seasonal = {}
    if hist_10y is not None and not hist_10y.empty:
        monthly = hist_10y["Close"].resample("ME").last().pct_change().dropna()
        for month in range(1, 13):
            m = monthly[monthly.index.month == month]
            seasonal[month] = round(float(m.mean()) * 100, 2) if len(m) > 0 else 0

    related = _get_related_assets(t)
    related_cards = []
    if related:
        data = yf.download(related, period="5d", auto_adjust=True, progress=False)
        close = data["Close"] if hasattr(data, "columns") and "Close" in data.columns else data
        if close is not None:
            try:
                if hasattr(close, "columns"):
                    for sym in related:
                        if sym not in close.columns:
                            continue
                        s = close[sym].dropna()
                        if len(s) < 1:
                            continue
                        cur = float(s.iloc[-1])
                        prev = float(s.iloc[-2]) if len(s) > 1 else cur
                        pct = ((cur - prev) / prev * 100) if prev else 0
                        related_cards.append({"symbol": sym, "price": round(cur, 2), "change_pct": round(pct, 2)})
                else:
                    s = close.dropna()
                    if len(s) >= 1:
                        cur = float(s.iloc[-1])
                        prev = float(s.iloc[-2]) if len(s) > 1 else cur
                        pct = ((cur - prev) / prev * 100) if prev else 0
                        related_cards.append({"symbol": related[0], "price": round(cur, 2), "change_pct": round(pct, 2)})
            except Exception:
                pass

    return {
        "name": COMMODITY_FUTURES.get(t, info.get("shortName", t)),
        "price": info.get("regularMarketPrice") or info.get("currentPrice"),
        "open_interest": info.get("openInterest"),
        "volume": info.get("volume"),
        "high_52w": info.get("fiftyTwoWeekHigh"),
        "low_52w": info.get("fiftyTwoWeekLow"),
        "seasonal_pattern": seasonal,
        "related_assets": related_cards,
        "correlation_matrix": await compute_commodity_correlations(t),
        "asset_class": "commodity_future",
    }
