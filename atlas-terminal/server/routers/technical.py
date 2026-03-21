"""Technical analysis router -- indicators, chart data, Fibonacci, Ichimoku."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get(
    "/{ticker}/indicators",
    summary="Technical indicators (RSI, SMA, EMA, MACD, BB, ATR)",
)
async def technical_indicators(ticker: str) -> Dict[str, Any]:
    """Calculate and return common technical indicators for *ticker*.

    Returns RSI(14), SMA(20/50/200), EMA(12/26), MACD with signal and
    histogram, Bollinger Bands (20,2), and ATR(14).
    """
    try:
        import yfinance as yf
        import ta  # type: ignore[import-untyped]

        df = yf.download(ticker.upper(), period="1y", interval="1d", progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        # Flatten MultiIndex columns if present
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        # RSI
        rsi_indicator = ta.momentum.RSIIndicator(close=close, window=14)
        rsi_val = rsi_indicator.rsi().iloc[-1]

        # SMA
        sma_20 = close.rolling(window=20).mean().iloc[-1]
        sma_50 = close.rolling(window=50).mean().iloc[-1]
        sma_200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else None

        # EMA
        ema_12 = close.ewm(span=12, adjust=False).mean().iloc[-1]
        ema_26 = close.ewm(span=26, adjust=False).mean().iloc[-1]

        # MACD
        macd_indicator = ta.trend.MACD(close=close)
        macd_line = macd_indicator.macd().iloc[-1]
        macd_signal = macd_indicator.macd_signal().iloc[-1]
        macd_hist = macd_indicator.macd_diff().iloc[-1]

        # Bollinger Bands
        bb = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bb_upper = bb.bollinger_hband().iloc[-1]
        bb_middle = bb.bollinger_mavg().iloc[-1]
        bb_lower = bb.bollinger_lband().iloc[-1]

        # ATR
        atr_indicator = ta.volatility.AverageTrueRange(
            high=high, low=low, close=close, window=14,
        )
        atr_val = atr_indicator.average_true_range().iloc[-1]

        current_price = float(close.iloc[-1])

        return {
            "ticker": ticker.upper(),
            "current_price": current_price,
            "rsi_14": round(float(rsi_val), 2),
            "sma": {
                "sma_20": round(float(sma_20), 2),
                "sma_50": round(float(sma_50), 2),
                "sma_200": round(float(sma_200), 2) if sma_200 is not None else None,
            },
            "ema": {
                "ema_12": round(float(ema_12), 2),
                "ema_26": round(float(ema_26), 2),
            },
            "macd": {
                "macd": round(float(macd_line), 4),
                "signal": round(float(macd_signal), 4),
                "histogram": round(float(macd_hist), 4),
            },
            "bollinger_bands": {
                "upper": round(float(bb_upper), 2),
                "middle": round(float(bb_middle), 2),
                "lower": round(float(bb_lower), 2),
            },
            "atr_14": round(float(atr_val), 2),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Technical indicators failed: {exc}",
        ) from exc


@router.get(
    "/{ticker}/chart-data",
    summary="OHLCV data for charting",
)
async def chart_data(
    ticker: str,
    period: str = Query(
        default="6mo",
        description="Data period: 1d,5d,1mo,3mo,6mo,1y,2y,5y",
    ),
    interval: str = Query(
        default="1d",
        description="Data interval: 1m,5m,15m,1h,1d,1wk",
    ),
) -> Dict[str, Any]:
    """Return OHLCV data formatted for TradingView Lightweight Charts.

    Each bar is ``{time, open, high, low, close, volume}``.
    """
    try:
        import yfinance as yf

        valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"}
        valid_intervals = {"1m", "5m", "15m", "1h", "1d", "1wk"}

        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period '{period}'. Must be one of {valid_periods}",
            )
        if interval not in valid_intervals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid interval '{interval}'. Must be one of {valid_intervals}",
            )

        df = yf.download(
            ticker.upper(),
            period=period,
            interval=interval,
            progress=False,
        )
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        # Flatten MultiIndex columns if present
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        bars: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            time_str = str(idx)[:10] if interval in {"1d", "1wk"} else str(idx)
            bars.append({
                "time": time_str,
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]),
            })

        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "bars": bars,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Chart data fetch failed: {exc}",
        ) from exc


@router.get(
    "/{ticker}/fibonacci",
    summary="Fibonacci retracement levels",
)
async def fibonacci_levels(ticker: str) -> Dict[str, Any]:
    """Return Fibonacci retracement levels based on the 52-week high and low.

    Levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%.
    """
    try:
        import yfinance as yf

        df = yf.download(ticker.upper(), period="1y", interval="1d", progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        # Flatten MultiIndex columns if present
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        high_52w: float = float(df["High"].max())
        low_52w: float = float(df["Low"].min())
        diff: float = high_52w - low_52w

        ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        levels: Dict[str, float] = {}
        for r in ratios:
            label = f"{r * 100:.1f}%"
            levels[label] = round(high_52w - diff * r, 2)

        current_price = float(df["Close"].iloc[-1])

        return {
            "ticker": ticker.upper(),
            "high_52w": round(high_52w, 2),
            "low_52w": round(low_52w, 2),
            "current_price": round(current_price, 2),
            "levels": levels,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Fibonacci levels failed: {exc}",
        ) from exc


@router.get(
    "/{ticker}/ichimoku",
    summary="Ichimoku cloud data",
)
async def ichimoku_cloud(ticker: str) -> Dict[str, Any]:
    """Return Ichimoku cloud components for *ticker*.

    Components: Tenkan-sen (9), Kijun-sen (26), Senkou Span A,
    Senkou Span B (52), and Chikou Span.
    """
    try:
        import yfinance as yf
        import pandas as pd

        df = yf.download(ticker.upper(), period="1y", interval="1d", progress=False)
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {ticker}")

        # Flatten MultiIndex columns if present
        if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
            df.columns = df.columns.get_level_values(0)

        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        nine_high = high.rolling(window=9).max()
        nine_low = low.rolling(window=9).min()
        tenkan = (nine_high + nine_low) / 2

        # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        k_high = high.rolling(window=26).max()
        k_low = low.rolling(window=26).min()
        kijun = (k_high + k_low) / 2

        # Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted 26
        senkou_a = ((tenkan + kijun) / 2).shift(26)

        # Senkou Span B (Leading Span B): (52-period high + low) / 2, shifted 26
        b_high = high.rolling(window=52).max()
        b_low = low.rolling(window=52).min()
        senkou_b = ((b_high + b_low) / 2).shift(26)

        # Chikou Span (Lagging Span): Close shifted back 26 periods
        chikou = close.shift(-26)

        # Take last 100 data points for response
        n = min(100, len(df))
        dates = [str(d)[:10] for d in df.index[-n:]]

        def _to_list(series: pd.Series) -> List[Optional[float]]:
            """Convert the last *n* values of a series to a list of floats."""
            vals = series.iloc[-n:]
            result: List[Optional[float]] = []
            for v in vals:
                try:
                    result.append(round(float(v), 2))
                except (ValueError, TypeError):
                    result.append(None)
            return result

        return {
            "ticker": ticker.upper(),
            "dates": dates,
            "tenkan_sen": _to_list(tenkan),
            "kijun_sen": _to_list(kijun),
            "senkou_span_a": _to_list(senkou_a),
            "senkou_span_b": _to_list(senkou_b),
            "chikou_span": _to_list(chikou),
            "close": _to_list(close),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Ichimoku cloud failed: {exc}",
        ) from exc
