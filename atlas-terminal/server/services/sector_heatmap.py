"""Sector performance heatmap service."""

from __future__ import annotations


SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Disc.": "XLY",
    "Industrials": "XLI",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Comm. Services": "XLC",
    "Consumer Staples": "XLP",
}


async def get_sector_heatmap() -> list[dict]:
    """Return daily percent change for major US sector ETFs."""
    import yfinance as yf

    results = []
    for sector, etf in SECTOR_ETFS.items():
        try:
            hist = yf.Ticker(etf).history(period="2d")
            if hist is None or len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            cur = float(hist["Close"].iloc[-1])
            change = ((cur - prev) / prev * 100) if prev else 0.0
            results.append({"sector": sector, "etf": etf, "change_pct": round(change, 2)})
        except Exception:
            continue
    return results
