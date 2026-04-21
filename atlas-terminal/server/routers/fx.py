"""FX router -- foreign exchange rates and historical data via yfinance."""

import asyncio
import time
from threading import Lock
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from server.models.schemas import FXRateResponse, FXHistoryResponse

router = APIRouter()
_FX_RATE_CACHE_TTL_SECONDS = 300
_FX_RATE_CACHE: dict[str, tuple[float, float]] = {}
_FX_RATE_CACHE_LOCK = Lock()

# Major FX pairs tracked by default (Yahoo Finance format: XXXYYY=X)
MAJOR_PAIRS = [
    "USDKRW", "USDJPY", "EURUSD", "GBPUSD", "USDCNY",
    "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP",
]


def _yf_fx_symbol(pair: str) -> str:
    """Convert a pair like 'USDKRW' to the Yahoo Finance symbol 'USDKRW=X'."""
    p = pair.upper().replace("=X", "").replace("/", "")
    return f"{p}=X"


def _fetch_fx_rate(pair: str) -> float | None:
    """Fetch the latest FX rate for a single pair via yfinance."""
    try:
        cache_key = pair.upper().replace("=X", "").replace("/", "")
        now = time.monotonic()
        with _FX_RATE_CACHE_LOCK:
            cached = _FX_RATE_CACHE.get(cache_key)
            if cached and now - cached[0] < _FX_RATE_CACHE_TTL_SECONDS:
                return cached[1]

        import yfinance as yf

        symbol = _yf_fx_symbol(pair)
        ticker = yf.Ticker(symbol)
        rate = None
        fast = getattr(ticker, "fast_info", None)
        if fast:
            price = getattr(fast, "last_price", None)
            if price and float(price) > 0:
                rate = float(price)
        if rate is None:
            hist = ticker.history(period="1d")
            if hist is not None and not hist.empty:
                rate = float(hist["Close"].iloc[-1])
        if rate is not None:
            with _FX_RATE_CACHE_LOCK:
                _FX_RATE_CACHE[cache_key] = (now, rate)
            return rate
    except Exception:
        pass
    return None


@router.get(
    "/rates",
    response_model=FXRateResponse,
    summary="FX conversion matrix for major currencies",
)
async def fx_rates():
    """Return conversion matrix for portfolio display currencies."""
    try:
        gbp_usd, eur_usd, usd_jpy, usd_krw, usd_dkk = await asyncio.gather(
            asyncio.to_thread(_fetch_fx_rate, "GBPUSD"),
            asyncio.to_thread(_fetch_fx_rate, "EURUSD"),
            asyncio.to_thread(_fetch_fx_rate, "USDJPY"),
            asyncio.to_thread(_fetch_fx_rate, "USDKRW"),
            asyncio.to_thread(_fetch_fx_rate, "USDDKK"),
        )
        usd_value = {
            "USD": 1.0,
            "GBP": gbp_usd or 1.27,
            "EUR": eur_usd or 1.08,
            "JPY": 1 / (usd_jpy or 149.5),
            "KRW": 1 / (usd_krw or 1370.0),
            "DKK": 1 / (usd_dkk or 6.86),
        }
        rates = {
            f"{src}_{dst}": src_usd / dst_usd
            for src, src_usd in usd_value.items()
            for dst, dst_usd in usd_value.items()
        }
        return FXRateResponse(pair="MATRIX", rates=rates)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FX rates failed: {exc}") from exc


@router.get(
    "/history/{pair}",
    response_model=FXHistoryResponse,
    summary="1-year FX history",
)
async def fx_history(pair: str):
    """Return ~1 year of daily closing rates for the given currency pair.

    *pair* should be in the format ``USDKRW``, ``EURUSD``, etc.
    """
    try:
        import yfinance as yf

        symbol = _yf_fx_symbol(pair)
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")

        if hist is None or hist.empty:
            raise HTTPException(status_code=404, detail=f"No history found for pair {pair}")

        dates: List[str] = [d.strftime("%Y-%m-%d") for d in hist.index]
        rates: List[float] = [round(float(v), 4) for v in hist["Close"]]

        return FXHistoryResponse(pair=pair.upper(), dates=dates, rates=rates)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FX history failed: {exc}") from exc
