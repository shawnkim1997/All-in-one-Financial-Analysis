"""Macro series: FRED (public CSV), optional ECOS (Bank of Korea).

FRED uses ``https://fred.stlouisfed.org/graph/fredgraph.csv`` (no API key) so we
avoid pandas-datareader / legacy dependencies on Python 3.12+.
"""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen

from server.utils.safe_float import _safe_float

_FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_USER_AGENT = "ATLAS-Terminal/1.0 (macro)"


def _parse_iso(s: Optional[str], default: datetime) -> datetime:
    if not s:
        return default
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except ValueError:
        return default


def fetch_fred_series(
    series_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Download a FRED series via the public graph CSV export."""
    sid = (series_id or "").strip().upper()
    if not sid:
        return []

    end_dt = _parse_iso(end, datetime.utcnow())
    start_dt = _parse_iso(start, end_dt - timedelta(days=365 * 10))

    url = f"{_FRED_CSV}?id={sid}"
    try:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=45) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    value_col = sid
    for rec in reader:
        ds = (rec.get("observation_date") or rec.get("DATE") or "").strip()[:10]
        if not ds:
            continue
        try:
            dt = datetime.strptime(ds, "%Y-%m-%d")
        except ValueError:
            continue
        if dt < start_dt or dt > end_dt:
            continue
        raw = rec.get(value_col) or rec.get(sid) or next(
            (rec[k] for k in rec if k not in ("observation_date", "DATE") and rec.get(k)),
            "",
        )
        fv = _safe_float(str(raw).replace(",", ""))
        if fv is not None:
            rows.append({"date": ds, "value": fv})
    return rows


def fetch_oecd_mei() -> List[Dict[str, Any]]:
    """OECD MEI via pandas-datareader was removed (Py3.13+). Return empty for now."""
    return []


def fetch_ecos_series(
    stat_code: str,
    cycle: str = "M",
    start_ym: str = "201501",
    end_ym: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Bank of Korea ECOS Open API (requires ``ECOS_API_KEY``)."""
    import json
    import urllib.parse
    import urllib.request

    key = (os.getenv("ECOS_API_KEY") or "").strip()
    if not key:
        return []

    code = (stat_code or "").strip()
    if not code:
        return []

    end_m = end_ym or datetime.utcnow().strftime("%Y%m")
    path = (
        f"/api/StatisticSearch/{urllib.parse.quote(key, safe='')}/json/kr/1/1000/"
        f"{code}/{cycle}/{start_ym}/{end_m}/"
    )
    url = "https://ecos.bok.or.kr" + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    row_block = (
        payload.get("StatisticSearch", {}).get("row", [])
    )
    if not isinstance(row_block, list):
        return []

    out: List[Dict[str, Any]] = []
    for r in row_block:
        if not isinstance(r, dict):
            continue
        t = r.get("TIME") or r.get("time")
        v = r.get("DATA_VALUE") or r.get("DATA")
        fv = _safe_float(v)
        if t and fv is not None:
            out.append({"period": str(t), "value": fv})
    return out
