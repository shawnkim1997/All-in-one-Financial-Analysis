"""Copper/Gold ratio and RORO-style risk composite (VIX + bond vol proxy)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from server.services.cache import cached

_TICK_VIX = "^VIX"
_TICK_MOVE = "^MOVE"
_TICK_TLT = "TLT"
_TICK_HG = "HG=F"
_TICK_GC = "GC=F"
_ROLL_Z = 252
_MA20 = 20


def _yf_close(ticker: str, period: str = "2y") -> pd.Series:
    try:
        import yfinance as yf

        t = yf.Ticker(ticker)
        hist = t.history(period=period, auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            return pd.Series(dtype=float)
        s = hist["Close"].astype(float)
        s.index = pd.to_datetime(s.index).tz_localize(None)
        return s.sort_index()
    except Exception:
        return pd.Series(dtype=float)


def _rolling_zscore_last(s: pd.Series, window: int = _ROLL_Z) -> Optional[float]:
    if s.empty or len(s) < window:
        return None
    tail = s.iloc[-window:]
    last = float(tail.iloc[-1])
    mu = float(tail.mean())
    sigma = float(tail.std())
    if sigma == 0 or np.isnan(sigma):
        return 0.0
    z = (last - mu) / sigma
    return float(z)


def _tlt_realized_vol_z() -> Optional[float]:
    px = _yf_close(_TICK_TLT)
    if px.empty or len(px) < _ROLL_Z + 5:
        return None
    ret = px.pct_change().dropna()
    rv = ret.rolling(20).std() * (252 ** 0.5) * 100.0
    rv = rv.dropna()
    return _rolling_zscore_last(rv)


def _roro_label(z: float) -> str:
    z = max(-3.0, min(3.0, z))
    if z <= -1.5:
        return "Extreme Fear"
    if z <= -0.5:
        return "Fear"
    if z <= 0.5:
        return "Neutral"
    if z <= 1.5:
        return "Greed"
    return "Extreme Greed"


@cached("smart_money_snapshot", ttl_seconds=900)
def get_smart_money_snapshot() -> Dict[str, Any]:
    """Copper/Gold trend + RORO Z from VIX and MOVE (or TLT vol Z)."""
    out: Dict[str, Any] = {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "roro_z": None,
        "roro_label": None,
        "copper_gold": [],
        "components": {"vix_z": None, "bond_vol_z": None, "bond_source": None},
        "error": None,
    }

    vix = _yf_close(_TICK_VIX)
    move = _yf_close(_TICK_MOVE)

    vix_z = _rolling_zscore_last(vix) if not vix.empty else None
    bond_z: Optional[float] = None
    bond_src = None

    if not move.empty and len(move) >= _ROLL_Z:
        bond_z = _rolling_zscore_last(move)
        bond_src = "MOVE"
    if bond_z is None:
        bond_z = _tlt_realized_vol_z()
        bond_src = "TLT_RV"

    out["components"]["vix_z"] = round(vix_z, 4) if vix_z is not None else None
    out["components"]["bond_vol_z"] = round(bond_z, 4) if bond_z is not None else None
    out["components"]["bond_source"] = bond_src

    if vix_z is not None and bond_z is not None:
        roro = (vix_z + bond_z) / 2.0
    elif vix_z is not None:
        roro = vix_z
    elif bond_z is not None:
        roro = bond_z
    else:
        out["error"] = "insufficient_data"
        return out

    out["roro_z"] = round(float(roro), 4)
    out["roro_label"] = _roro_label(float(roro))

    hg = _yf_close(_TICK_HG)
    gc = _yf_close(_TICK_GC)
    if hg.empty or gc.empty:
        return out

    df = pd.DataFrame({"hg": hg, "gc": gc}).dropna()
    if df.empty:
        return out
    df["ratio"] = df["hg"] / df["gc"]
    df["ratio_ma20"] = df["ratio"].rolling(_MA20).mean()

    cg: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        if pd.isna(row["ratio"]):
            continue
        item: Dict[str, Any] = {
            "date": idx.strftime("%Y-%m-%d"),
            "ratio": round(float(row["ratio"]), 6),
        }
        if not pd.isna(row.get("ratio_ma20")):
            item["ratio_ma20"] = round(float(row["ratio_ma20"]), 6)
        cg.append(item)

    out["copper_gold"] = cg[-520:] if len(cg) > 520 else cg
    return out
