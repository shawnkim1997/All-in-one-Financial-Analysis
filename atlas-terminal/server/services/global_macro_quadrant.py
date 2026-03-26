"""Global macro quadrant: growth vs inflation momentum (Z-scores) for major economies."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from server.services.macro_fetcher import fetch_fred_series
from server.services.oecd_cycle import _fetch_cli

_LOOKBACK_MOM = 60
_MIN_MOMENTS = 6


@dataclass(frozen=True)
class _GrowthSource:
    kind: str  # "fred_level" | "oecd_cli"
    fred_id: Optional[str] = None
    oecd_iso: Optional[str] = None


@dataclass(frozen=True)
class _InflationSource:
    fred_id: str
    is_index: bool


# US, Eurozone, Japan, China, South Korea — FRED where available; OECD CLI fallback for growth.
_COUNTRY_SPECS: List[Dict[str, Any]] = [
    {
        "id": "US",
        "label": "United States",
        "growth": _GrowthSource("fred_level", fred_id="ISM/MAN_PMI"),
        "inflation": _InflationSource("CPIAUCSL", True),
    },
    {
        "id": "EU",
        "label": "Eurozone",
        "growth": _GrowthSource("fred_level", fred_id="EMUSTRM"),
        "inflation": _InflationSource("CP0000EZ19M086NEST", True),
    },
    {
        "id": "JP",
        "label": "Japan",
        "growth": _GrowthSource("fred_level", fred_id="JPNPMIMA", oecd_iso="JPN"),
        "inflation": _InflationSource("JPNCPIALLMINMEI", True),
    },
    {
        "id": "CN",
        "label": "China",
        "growth": _GrowthSource("oecd_cli", oecd_iso="CHN"),
        "inflation": _InflationSource("CHNCPIALLMINMEI", True),
    },
    {
        "id": "KR",
        "label": "South Korea",
        "growth": _GrowthSource("oecd_cli", oecd_iso="KOR"),
        "inflation": _InflationSource("KORCPIALLMINMEI", True),
    },
]


def _fred_to_series(rows: List[Dict[str, Any]]) -> pd.Series:
    if not rows:
        return pd.Series(dtype=float)
    df = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["date"])
    df = df.sort_values("dt").drop_duplicates("dt", keep="last")
    s = pd.Series(df["value"].astype(float).values, index=df["dt"])
    return s.sort_index()


def _pct_yoy_monthly(s: pd.Series) -> pd.Series:
    if s.empty or len(s) < 13:
        return pd.Series(dtype=float)
    return s.pct_change(12) * 100.0


def _oecd_cli_series(iso: str, limit: int = 120) -> pd.Series:
    raw = _fetch_cli(iso, limit=limit)
    if not raw:
        return pd.Series(dtype=float)
    recs = []
    for r in raw:
        p = str(r.get("date", ""))[:7]
        if len(p) < 7:
            continue
        dt = pd.Timestamp(p + "-01")
        v = r.get("value")
        if v is None:
            continue
        try:
            recs.append((dt, float(v)))
        except (TypeError, ValueError):
            continue
    if not recs:
        return pd.Series(dtype=float)
    recs.sort(key=lambda x: x[0])
    idx = [x[0] for x in recs]
    vals = [x[1] for x in recs]
    return pd.Series(vals, index=idx).sort_index()


def _three_month_momentum(s: pd.Series) -> pd.Series:
    if s.empty or len(s) < 4:
        return pd.Series(dtype=float)
    return s - s.shift(3)


def _zscore_last(momentum: pd.Series, lookback: int = _LOOKBACK_MOM) -> Tuple[Optional[float], Optional[float]]:
    """Return (z-score of last momentum, last momentum value)."""
    mom = momentum.dropna()
    if len(mom) < _MIN_MOMENTS:
        return None, None
    tail = mom.iloc[-lookback:]
    last = float(tail.iloc[-1])
    arr = tail.values.astype(float)
    mean = float(np.mean(arr))
    std = float(np.std(arr))
    if std == 0 or np.isnan(std):
        return 0.0, last
    z = float((last - mean) / std)
    return z, last


def _quadrant_label(gz: float, iz: float) -> str:
    gpos = gz > 0
    ipos = iz > 0
    if gpos and ipos:
        return "Reflation"
    if gpos and not ipos:
        return "Recovery"
    if not gpos and ipos:
        return "Stagflation"
    return "Overheat"


def _growth_series_resolved(spec: _GrowthSource) -> pd.Series:
    if spec.kind == "fred_level" and spec.fred_id:
        s = _fred_to_series(fetch_fred_series(spec.fred_id))
        if not s.empty:
            return s
    if spec.kind == "oecd_cli" and spec.oecd_iso:
        return _oecd_cli_series(spec.oecd_iso)
    if spec.oecd_iso:
        return _oecd_cli_series(spec.oecd_iso)
    return pd.Series(dtype=float)


def _inflation_series(src: _InflationSource) -> pd.Series:
    rows = fetch_fred_series(src.fred_id)
    s = _fred_to_series(rows)
    if s.empty:
        return pd.Series(dtype=float)
    if src.is_index:
        return _pct_yoy_monthly(s)
    return s


def _compute_country_point(spec_row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    gspec: _GrowthSource = spec_row["growth"]
    ispec: _InflationSource = spec_row["inflation"]

    g = _growth_series_resolved(gspec)
    inf = _inflation_series(ispec)
    if g.empty or inf.empty:
        return None

    g_mom = _three_month_momentum(g)
    i_mom = _three_month_momentum(inf)

    gz, g_last = _zscore_last(g_mom)
    iz, i_last = _zscore_last(i_mom)
    if gz is None or iz is None:
        return None

    return {
        "id": spec_row["id"],
        "label": spec_row["label"],
        "growth_z": round(gz, 4),
        "inflation_z": round(iz, 4),
        "growth_momentum": round(g_last, 4) if g_last is not None else None,
        "inflation_momentum": round(i_last, 4) if i_last is not None else None,
        "quadrant": _quadrant_label(gz, iz),
    }


def get_global_macro_quadrant() -> Dict[str, Any]:
    """Return scatter payload for global growth/inflation quadrant."""
    points: List[Dict[str, Any]] = []
    order = {row["id"]: i for i, row in enumerate(_COUNTRY_SPECS)}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_compute_country_point, row): row for row in _COUNTRY_SPECS}
        for fut in as_completed(futures):
            try:
                p = fut.result()
                if p:
                    points.append(p)
            except Exception:
                continue
    points.sort(key=lambda x: order.get(x.get("id", ""), 99))
    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "points": points,
    }
