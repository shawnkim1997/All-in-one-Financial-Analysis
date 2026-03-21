"""FX rate fetcher -- yfinance-based with in-memory TTL cache.

Provides current rates and 1-year history for major currency pairs.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# In-memory cache with configurable TTL
# ---------------------------------------------------------------------------

_cache: Dict[str, Any] = {}
_cache_ts: Dict[str, float] = {}
_CACHE_TTL = 60  # seconds

# Default pairs
DEFAULT_PAIRS: List[str] = ["USDKRW=X", "GBPUSD=X", "EURUSD=X", "USDJPY=X"]


def _get_cached(key: str) -> Optional[Any]:
    if key in _cache and (time.time() - _cache_ts.get(key, 0)) < _CACHE_TTL:
        return _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = value
    _cache_ts[key] = time.time()


def _normalise_pair(pair: str) -> str:
    """Ensure pair is in Yahoo Finance format (e.g. 'USDKRW=X')."""
    p = pair.upper().replace("/", "").strip()
    if not p.endswith("=X"):
        p = f"{p}=X"
    return p


# ---------------------------------------------------------------------------
# Current rates
# ---------------------------------------------------------------------------

def fetch_fx_rate(pair: str) -> Optional[float]:
    """Fetch the latest exchange rate for a single currency pair.

    Parameters
    ----------
    pair:
        Currency pair string, e.g. ``"USDKRW"``, ``"USDKRW=X"``, ``"EUR/USD"``.

    Returns
    -------
    float or None
        The latest rate, or None if unavailable.
    """
    symbol = _normalise_pair(pair)
    cache_key = f"fx_rate:{symbol}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        fast = getattr(ticker, "fast_info", None)
        if fast:
            price = getattr(fast, "last_price", None)
            if price and float(price) > 0:
                rate = float(price)
                _set_cached(cache_key, rate)
                return rate
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            rate = float(hist["Close"].iloc[-1])
            _set_cached(cache_key, rate)
            return rate
    except Exception:
        pass
    return None


def fetch_multiple_rates(
    pairs: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Fetch current rates for multiple pairs.

    Parameters
    ----------
    pairs:
        List of pair strings. Defaults to DEFAULT_PAIRS.

    Returns
    -------
    dict
        Mapping of normalised pair symbol -> rate.
    """
    pairs = pairs or DEFAULT_PAIRS
    rates: Dict[str, float] = {}
    for pair in pairs:
        rate = fetch_fx_rate(pair)
        if rate is not None:
            key = _normalise_pair(pair).replace("=X", "")
            rates[key] = round(rate, 4)
    return rates


# ---------------------------------------------------------------------------
# 1-year history
# ---------------------------------------------------------------------------

def fetch_fx_history(
    pair: str,
    period: str = "1y",
) -> Tuple[List[str], List[float]]:
    """Fetch historical daily closing rates for a currency pair.

    Parameters
    ----------
    pair:
        Currency pair string.
    period:
        yfinance period string (default ``"1y"``).

    Returns
    -------
    tuple of (dates, rates)
        dates: list of ISO date strings
        rates: list of float closing prices
    """
    symbol = _normalise_pair(pair)
    cache_key = f"fx_hist:{symbol}:{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist is None or hist.empty:
            return ([], [])
        dates = [d.strftime("%Y-%m-%d") for d in hist.index]
        rates = [round(float(v), 4) for v in hist["Close"]]
        result = (dates, rates)
        _set_cached(cache_key, result)
        return result
    except Exception:
        return ([], [])
