"""US 10Y minus peer 10Y spread vs FX pairs (yfinance)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from server.services.macro_fetcher import fetch_fred_series

_FRED_US10Y = "DGS10"
_FRED_JP10Y = "IRLTLT01JPM156N"
_FRED_EZ10Y = "IRLTLT01EZM156N"
_FRED_KR10Y = "IRLTLT01KRM156N"

_YF_PAIR = {
    "usdjpy": "USDJPY=X",
    "eurusd": "EURUSD=X",
    "usdkrw": "KRW=X",
}

_PEER_FRED = {
    "usdjpy": _FRED_JP10Y,
    "eurusd": _FRED_EZ10Y,
    "usdkrw": _FRED_KR10Y,
}


def _fred_to_daily_series(series_id: str) -> pd.Series:
    rows = fetch_fred_series(series_id)
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values("dt").drop_duplicates("dt", keep="last")
    s = pd.Series(df["value"].astype(float).values, index=df["dt"])
    return s.sort_index()


def _fred_to_monthly_end(series_id: str) -> pd.Series:
    s = _fred_to_daily_series(series_id)
    if s.empty:
        return pd.Series(dtype=float)
    # Monthly FRED series: normalize to month-end
    m = s.resample("ME").last().dropna()
    return m


def _us10y_monthly() -> pd.Series:
    daily = _fred_to_daily_series(_FRED_US10Y)
    if daily.empty:
        return pd.Series(dtype=float)
    return daily.resample("ME").last().dropna()


def _yf_fx(ticker: str, period: str = "2y") -> pd.Series:
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            return pd.Series(dtype=float)
        s = hist["Close"].astype(float)
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return s.resample("ME").last().dropna()
    except Exception:
        return pd.Series(dtype=float)


def get_yield_fx_pair(pair: str) -> Dict[str, Any]:
    """Return aligned monthly spread (US10Y - peer10Y) vs FX."""
    key = (pair or "").strip().lower()
    out: Dict[str, Any] = {
        "pair": key,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "series": [],
        "error": None,
    }
    if key not in _YF_PAIR:
        out["error"] = "invalid_pair"
        return out

    peer_id = _PEER_FRED.get(key)
    if not peer_id:
        out["error"] = "missing_peer"
        return out

    us_m = _us10y_monthly()
    peer_m = _fred_to_monthly_end(peer_id)
    if us_m.empty or peer_m.empty:
        out["error"] = "fred_empty"
        return out

    spread = us_m.sub(peer_m, fill_value=None)
    spread = spread.dropna()

    fx = _yf_fx(_YF_PAIR[key])
    if fx.empty:
        out["error"] = "fx_empty"
        return out

    df = pd.DataFrame({"spread_pct": spread}).join(
        pd.DataFrame({"fx": fx}), how="inner"
    )
    df = df.dropna()
    df = df.sort_index()

    series: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        series.append({
            "date": idx.strftime("%Y-%m-%d"),
            "spread_pct": round(float(row["spread_pct"]), 4),
            "fx": round(float(row["fx"]), 6),
        })

    out["series"] = series
    return out
