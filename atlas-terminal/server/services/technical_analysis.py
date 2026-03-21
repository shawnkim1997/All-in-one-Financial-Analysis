"""Technical analysis service -- compute indicators and detect signals."""

import math

import pandas as pd
import ta
import yfinance as yf


def _safe(val, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except Exception:
        return default


def _series_to_list(s):
    return [_safe(v) for v in s.tolist()]


def compute_all_indicators(ticker: str, period: str = "1y") -> dict:
    """Fetch OHLCV from yfinance and compute all TA indicators."""
    df = yf.Ticker(ticker).history(period=period)
    if df.empty:
        return {}

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    return {
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "ohlc": {
            "open": _series_to_list(df["Open"]),
            "high": _series_to_list(high),
            "low": _series_to_list(low),
            "close": _series_to_list(close),
        },
        "volume": _series_to_list(volume),
        "sma_20": _series_to_list(ta.trend.sma_indicator(close, window=20)),
        "sma_50": _series_to_list(ta.trend.sma_indicator(close, window=50)),
        "sma_200": _series_to_list(ta.trend.sma_indicator(close, window=200)),
        "ema_12": _series_to_list(ta.trend.ema_indicator(close, window=12)),
        "ema_26": _series_to_list(ta.trend.ema_indicator(close, window=26)),
        "rsi": _series_to_list(ta.momentum.rsi(close, window=14)),
        "macd": _series_to_list(ta.trend.macd(close)),
        "macd_signal": _series_to_list(ta.trend.macd_signal(close)),
        "macd_histogram": _series_to_list(ta.trend.macd_diff(close)),
        "bb_upper": _series_to_list(ta.volatility.bollinger_hband(close)),
        "bb_lower": _series_to_list(ta.volatility.bollinger_lband(close)),
        "bb_middle": _series_to_list(ta.volatility.bollinger_mavg(close)),
        "ichimoku_a": _series_to_list(ta.trend.ichimoku_a(high, low)),
        "ichimoku_b": _series_to_list(ta.trend.ichimoku_b(high, low)),
        "ichimoku_base": _series_to_list(ta.trend.ichimoku_base_line(high, low)),
        "ichimoku_conversion": _series_to_list(
            ta.trend.ichimoku_conversion_line(high, low)
        ),
        "adx": _series_to_list(ta.trend.adx(high, low, close)),
        "signals": detect_signals(df),
    }


def detect_signals(df: pd.DataFrame) -> list:
    """Detect Golden Cross, Death Cross, RSI signals."""
    signals = []
    sma50 = ta.trend.sma_indicator(df["Close"], 50)
    sma200 = ta.trend.sma_indicator(df["Close"], 200)
    rsi = ta.momentum.rsi(df["Close"], 14)

    for i in range(1, len(df)):
        if (
            pd.notna(sma50.iloc[i])
            and pd.notna(sma200.iloc[i])
            and pd.notna(sma50.iloc[i - 1])
            and pd.notna(sma200.iloc[i - 1])
        ):
            if (
                sma50.iloc[i] > sma200.iloc[i]
                and sma50.iloc[i - 1] <= sma200.iloc[i - 1]
            ):
                signals.append(
                    {
                        "date": df.index[i].strftime("%Y-%m-%d"),
                        "type": "golden_cross",
                        "label": "Golden Cross",
                    }
                )
            if (
                sma50.iloc[i] < sma200.iloc[i]
                and sma50.iloc[i - 1] >= sma200.iloc[i - 1]
            ):
                signals.append(
                    {
                        "date": df.index[i].strftime("%Y-%m-%d"),
                        "type": "death_cross",
                        "label": "Death Cross",
                    }
                )
        if pd.notna(rsi.iloc[i]) and pd.notna(rsi.iloc[i - 1]):
            if rsi.iloc[i] > 30 and rsi.iloc[i - 1] <= 30:
                signals.append(
                    {
                        "date": df.index[i].strftime("%Y-%m-%d"),
                        "type": "rsi_oversold_bounce",
                        "label": "RSI Oversold Bounce",
                    }
                )
            if rsi.iloc[i] > 70 and rsi.iloc[i - 1] <= 70:
                signals.append(
                    {
                        "date": df.index[i].strftime("%Y-%m-%d"),
                        "type": "rsi_overbought",
                        "label": "RSI Overbought",
                    }
                )
    return signals


def compute_fibonacci_levels(high_52w: float, recent_low: float) -> dict:
    """Compute Fibonacci retracement levels from 52-week high and recent low."""
    diff = high_52w - recent_low
    return {
        "high": high_52w,
        "low": recent_low,
        "level_236": recent_low + diff * 0.236,
        "level_382": recent_low + diff * 0.382,
        "level_500": recent_low + diff * 0.500,
        "level_618": recent_low + diff * 0.618,
        "level_786": recent_low + diff * 0.786,
    }
