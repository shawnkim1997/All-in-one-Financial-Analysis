"""OECD leading indicator service via DBnomics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from server.services.cache import cached

OECD_COUNTRIES = {
    "USA": "United States",
    "EA": "Euro Area",
    "GBR": "United Kingdom",
    "DEU": "Germany",
    "FRA": "France",
    "JPN": "Japan",
    "KOR": "South Korea",
    "CHN": "China",
    "IND": "India",
    "BRA": "Brazil",
}

_DATASET = "DSD_STES@DF_CLI"


def _fetch_cli(iso: str, limit: int = 36) -> List[Dict[str, Any]]:
    """Fetch CLI (normalized) for a country from DBnomics."""
    code = f"{iso}.M.LI.IX._Z.NOR.IX._Z.H"
    return _fetch_dbn(_DATASET, code, limit)


def _fetch_bci(iso: str) -> Optional[float]:
    code = f"{iso}.M.BCICP.IX._Z.AA.IX._Z.H"
    series = _fetch_dbn(_DATASET, code, 3)
    return series[-1]["value"] if series else None


def _fetch_cci(iso: str) -> Optional[float]:
    code = f"{iso}.M.CCICP.IX._Z.AA.IX._Z.H"
    series = _fetch_dbn(_DATASET, code, 3)
    return series[-1]["value"] if series else None


def _fetch_dbn(dataset: str, series_code: str, limit: int) -> List[Dict[str, Any]]:
    """Fetch from DBnomics, with REST fallback."""
    try:
        import dbnomics
        df = dbnomics.fetch_series(
            provider_code="OECD", dataset_code=dataset, series_code=series_code,
        )
        if df is None or df.empty:
            return []
        df = df.dropna(subset=["value"]).tail(limit)
        return [
            {"date": str(row["period"])[:7], "value": round(float(row["value"]), 4)}
            for _, row in df.iterrows()
        ]
    except Exception:
        return _fetch_dbn_rest(dataset, series_code, limit)


def _fetch_dbn_rest(dataset: str, series_code: str, limit: int) -> List[Dict[str, Any]]:
    """REST fallback when the dbnomics package fails."""
    import requests
    url = f"https://api.db.nomics.world/v22/series/OECD/{dataset}/{series_code}?observations=1&limit=1"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        docs = data.get("series", {}).get("docs", [])
        if not docs:
            return []
        obs = docs[0]
        periods = obs.get("period", [])
        values = obs.get("value", [])
        result = []
        for p, v in zip(periods[-limit:], values[-limit:]):
            if v is not None and str(v) != "NA":
                try:
                    result.append({"date": str(p)[:7], "value": round(float(v), 4)})
                except (TypeError, ValueError):
                    continue
        return result
    except Exception:
        return []


def _direction(series: List[Dict[str, Any]]) -> str:
    if len(series) < 2:
        return "unknown"
    last = series[-1]["value"]
    prev = series[-2]["value"]
    if last > 100 and last > prev:
        return "expanding"
    if last < 100 and last < prev:
        return "contracting"
    if last > prev:
        return "recovering"
    return "slowing"


@cached("oecd_cli_snapshot", ttl_seconds=21600)
def get_oecd_cli_snapshot() -> Dict[str, Any]:
    """Fetch OECD CLI for major economies via DBnomics."""
    countries: List[Dict[str, Any]] = []

    for iso, name in OECD_COUNTRIES.items():
        series = _fetch_cli(iso, limit=36)
        cli_current = series[-1]["value"] if series else None
        cli_prev = series[-2]["value"] if len(series) >= 2 else None

        bci = _fetch_bci(iso)
        cci = _fetch_cci(iso)

        countries.append({
            "country": name,
            "iso": iso,
            "cli_current": cli_current,
            "cli_prev": cli_prev,
            "direction": _direction(series) if series else "unknown",
            "bci": bci,
            "cci": cci,
            "series": series,
        })

    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "countries": countries,
    }
