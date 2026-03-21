"""Market overview service: indices, commodities, bonds, crypto, FX."""

from __future__ import annotations


INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "KOSPI": "^KS11",
    "Nikkei 225": "^N225",
    "FTSE 100": "^FTSE",
    "DAX": "^GDAXI",
    "Hang Seng": "^HSI",
}
COMMODITIES = {"Gold": "GC=F", "Oil (WTI)": "CL=F", "Silver": "SI=F", "Nat Gas": "NG=F"}
BONDS = {"US 10Y": "^TNX", "US 2Y": "^IRX"}
CRYPTO = {"Bitcoin": "BTC-USD", "Ethereum": "ETH-USD"}
FX = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "USD/KRW": "USDKRW=X"}
POPULAR_ETFS = {"SPY": "SPY", "QQQ": "QQQ", "GLD": "GLD", "TLT": "TLT", "EEM": "EEM"}


async def get_market_overview() -> dict:
    """Fetch concise multi-asset market overview from yfinance."""
    import yfinance as yf

    results = {}
    for category, tickers in [
        ("indices", INDICES),
        ("commodities", COMMODITIES),
        ("bonds", BONDS),
        ("crypto", CRYPTO),
        ("fx", FX),
        ("popular_etfs", POPULAR_ETFS),
    ]:
        cat_data = []
        for name, symbol in tickers.items():
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="5d")
                if hist is None or hist.empty:
                    continue
                current = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
                change_pct = ((current - prev) / prev * 100) if prev else 0.0
                cat_data.append(
                    {
                        "name": name,
                        "symbol": symbol,
                        "price": round(current, 2),
                        "change_pct": round(change_pct, 2),
                    }
                )
            except Exception:
                continue
        results[category] = cat_data
    return results
