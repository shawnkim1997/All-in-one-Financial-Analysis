"""Korea Bank (ECOS) economic data fetcher."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from server.services.cache import cached

ECOS_BASE = "https://ecos.bok.or.kr/api"

KOREA_INDICATORS = [
    {
        "key": "policy_rate",
        "label": "\ud55c\uad6d\uc740\ud589 \uae30\uc900\uae08\ub9ac",
        "table": "722Y001",
        "item": "0101000",
        "cycle": "M",
        "unit": "%",
    },
    {
        "key": "cpi_yoy",
        "label": "\uc18c\ube44\uc790\ubb3c\uac00 \uc0c1\uc2b9\ub960",
        "table": "901Y009",
        "item": "0",
        "cycle": "M",
        "unit": "%",
    },
    {
        "key": "gdp_growth",
        "label": "\uc2e4\uc9c8 GDP \uc131\uc7a5\ub960",
        "table": "200Y002",
        "item": "10111",
        "cycle": "Q",
        "unit": "%",
    },
    {
        "key": "exports_yoy",
        "label": "\uc218\ucd9c \uc99d\uac10\ub960",
        "table": "403Y001",
        "item": "1",
        "cycle": "M",
        "unit": "%",
    },
    {
        "key": "usd_krw",
        "label": "\uc6d0/\ub2ec\ub7ec \ud658\uc728",
        "table": "731Y003",
        "item": "0000001",
        "cycle": "M",
        "unit": "\u20a9",
    },
    {
        "key": "cli",
        "label": "\uacbd\uae30\uc120\ud589\uc9c0\uc218",
        "table": "101Y018",
        "item": "I16A",
        "cycle": "M",
        "unit": "pt",
    },
]


def _fetch_ecos_indicator(
    api_key: str,
    table_code: str,
    item_code: str,
    cycle: str,
    count: int = 3,
) -> List[Dict[str, Any]]:
    """Fetch the latest values from ECOS API."""
    import requests

    now = datetime.utcnow()
    if cycle == "Q":
        end_date = now.strftime("%Y%m")
        start_date = (now - timedelta(days=365 * 2)).strftime("%Y%m")
        freq = "Q"
    else:
        end_date = now.strftime("%Y%m")
        start_date = (now - timedelta(days=365)).strftime("%Y%m")
        freq = "M"

    url = (
        f"{ECOS_BASE}/StatisticSearch/{api_key}/json/kr/1/{count * 4}"
        f"/{table_code}/{freq}/{start_date}/{end_date}/{item_code}"
    )

    try:
        resp = requests.get(url, timeout=12)
        data = resp.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        result = []
        for row in rows[-count:]:
            val = row.get("DATA_VALUE")
            time_str = row.get("TIME", "")
            try:
                result.append({"date": time_str, "value": float(val)})
            except (TypeError, ValueError):
                continue
        return result
    except Exception:
        return []


def _ecos_fallback_yfinance() -> Dict[str, Any]:
    """Minimal fallback using yfinance for USD/KRW and KOSPI."""
    import yfinance as yf

    indicators: List[Dict[str, Any]] = []
    try:
        krw = yf.Ticker("KRW=X")
        hist = krw.history(period="5d")
        if hist is not None and not hist.empty:
            rate = float(hist["Close"].iloc[-1])
            indicators.append({
                "key": "usd_krw",
                "label": "\uc6d0/\ub2ec\ub7ec \ud658\uc728",
                "value": round(rate, 2),
                "unit": "\u20a9",
                "prev": None,
                "direction": None,
            })
    except Exception:
        pass

    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "indicators": indicators,
        "source": "yfinance_fallback",
    }


@cached("korea_ecos_snapshot", ttl_seconds=3600)
def _fetch_korea_cached(api_key: str) -> Dict[str, Any]:
    indicators: List[Dict[str, Any]] = []

    for spec in KOREA_INDICATORS:
        values = _fetch_ecos_indicator(
            api_key, spec["table"], spec["item"], spec["cycle"], count=3,
        )
        if not values:
            continue

        latest = values[-1]
        prev = values[-2] if len(values) >= 2 else None

        direction = None
        if prev is not None:
            if latest["value"] > prev["value"]:
                direction = "up"
            elif latest["value"] < prev["value"]:
                direction = "down"
            else:
                direction = "flat"

        indicators.append({
            "key": spec["key"],
            "label": spec["label"],
            "value": round(latest["value"], 2),
            "unit": spec["unit"],
            "prev": round(prev["value"], 2) if prev else None,
            "direction": direction,
        })

    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "indicators": indicators,
        "source": "ecos",
    }


def get_korea_snapshot(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Return Korean economic indicators from ECOS, or yfinance fallback."""
    if not api_key:
        return _ecos_fallback_yfinance()
    return _fetch_korea_cached(api_key)
