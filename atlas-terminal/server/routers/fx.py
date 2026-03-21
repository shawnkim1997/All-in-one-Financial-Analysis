"""FX router -- foreign exchange rates and historical data via yfinance."""

from typing import Dict, List

from fastapi import APIRouter, HTTPException

from server.models.schemas import FXRateResponse, FXHistoryResponse

router = APIRouter()

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
        import yfinance as yf

        symbol = _yf_fx_symbol(pair)
        ticker = yf.Ticker(symbol)
        fast = getattr(ticker, "fast_info", None)
        if fast:
            price = getattr(fast, "last_price", None)
            if price and float(price) > 0:
                return float(price)
        hist = ticker.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


@router.get(
    "/rates",
    response_model=FXRateResponse,
    summary="Major FX rates",
)
async def fx_rates():
    """Return current exchange rates for major currency pairs
    (USD/KRW, USD/JPY, EUR/USD, GBP/USD, etc.).
    """
    try:
        rates: Dict[str, float] = {}
        for pair in MAJOR_PAIRS:
            rate = _fetch_fx_rate(pair)
            if rate is not None:
                rates[pair] = round(rate, 4)
        return FXRateResponse(pair="MAJOR", rates=rates)
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
