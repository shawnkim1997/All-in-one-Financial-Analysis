"""Crypto price fetcher -- Bithumb (KRW) and Binance (USD) public APIs.

Provides standalone fetcher functions that can be used by the crypto router
or any other service that needs cryptocurrency price data.
"""

import time
from typing import Any, Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Top 20 coins
# ---------------------------------------------------------------------------

TOP_20_COINS: List[str] = [
    "BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "DOGE", "AVAX", "DOT", "MATIC",
    "LINK", "SHIB", "TRX", "UNI", "ATOM", "LTC", "ETC", "XLM", "NEAR", "APT",
]

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL = 30  # seconds


def _get_cached(key: str) -> Optional[Any]:
    if key in _cache and (time.time() - _cache_ts.get(key, 0)) < _CACHE_TTL:
        return _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = value
    _cache_ts[key] = time.time()


# ---------------------------------------------------------------------------
# Bithumb (KRW)
# ---------------------------------------------------------------------------

def fetch_bithumb_all_krw(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """Fetch KRW prices from Bithumb ALL_KRW endpoint.

    Uses the bulk endpoint (https://api.bithumb.com/public/ticker/ALL_KRW)
    to avoid per-symbol rate limits.

    Parameters
    ----------
    symbols:
        Coin symbols to include. Defaults to TOP_20_COINS.

    Returns
    -------
    dict
        Mapping of symbol -> KRW price (float).
    """
    cached = _get_cached("bithumb_all_krw")
    if cached is not None:
        return cached

    symbols = symbols or TOP_20_COINS
    url = "https://api.bithumb.com/public/ticker/ALL_KRW"
    prices: Dict[str, float] = {}
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") != "0000":
            return prices
        data = body.get("data", {})
        for sym in symbols:
            coin_data = data.get(sym.upper())
            if coin_data and isinstance(coin_data, dict):
                closing = coin_data.get("closing_price")
                if closing:
                    prices[sym.upper()] = float(closing)
    except Exception:
        pass

    _set_cached("bithumb_all_krw", prices)
    return prices


# ---------------------------------------------------------------------------
# Binance (USD)
# ---------------------------------------------------------------------------

def fetch_binance_prices(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """Fetch USD prices from Binance ticker/price endpoint.

    Parameters
    ----------
    symbols:
        Coin symbols to include. Defaults to TOP_20_COINS.

    Returns
    -------
    dict
        Mapping of symbol -> USD price (float).
    """
    cached = _get_cached("binance_prices")
    if cached is not None:
        return cached

    symbols = symbols or TOP_20_COINS
    url = "https://api.binance.com/api/v3/ticker/price"
    prices: Dict[str, float] = {}
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        lookup = {item["symbol"]: float(item["price"]) for item in data}
        for sym in symbols:
            key = f"{sym.upper()}USDT"
            if key in lookup:
                prices[sym.upper()] = lookup[key]
    except Exception:
        pass

    _set_cached("binance_prices", prices)
    return prices


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

def fetch_top20_prices(
    symbols: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Return top-20 crypto prices with both KRW and USD.

    Each entry contains:
    - symbol: str
    - price_usd: float | None
    - price_krw: float | None

    Parameters
    ----------
    symbols:
        Override default TOP_20_COINS list.
    """
    symbols = symbols or TOP_20_COINS
    usd = fetch_binance_prices(symbols)
    krw = fetch_bithumb_all_krw(symbols)

    results: List[Dict[str, Any]] = []
    for sym in symbols:
        results.append({
            "symbol": sym.upper(),
            "price_usd": usd.get(sym.upper()),
            "price_krw": krw.get(sym.upper()),
        })
    return results
