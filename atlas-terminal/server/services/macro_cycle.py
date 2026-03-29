"""Macro cycle service using FRED, World Bank, and market proxies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO
from typing import Any, Dict, List, Optional

import numpy as np

from server.services.cache import cached

_cached_snapshot = cached("macro_cycle_snapshot", ttl_seconds=3600)


@dataclass(frozen=True)
class MacroSeries:
    key: str
    label: str
    fred_code: str
    frequency: str = "monthly"
    unit: str = ""
    higher_is_better: bool = True
    is_index: bool = False


US_SERIES: List[MacroSeries] = [
    MacroSeries("gdp_growth", "Real GDP Growth", "A191RL1Q225SBEA", "quarterly", "%", True),
    MacroSeries("inflation", "Inflation (CPI YoY)", "CPIAUCSL", "monthly", "%", False, is_index=True),
    MacroSeries("unemployment", "Unemployment Rate", "UNRATE", "monthly", "%", False),
    MacroSeries("fed_funds", "Fed Funds Rate", "FEDFUNDS", "monthly", "%", False),
    MacroSeries("yield_curve", "10Y-2Y Treasury Spread", "T10Y2Y", "daily", "bp", True),
    MacroSeries("industrial_production", "Industrial Production YoY", "INDPRO", "monthly", "%", True, is_index=True),
]


COUNTRY_META: Dict[str, Dict[str, str]] = {
    "United States":  {"iso": "USA", "wb": "USA", "region": "Americas"},
    "Euro Area":      {"iso": "EUU", "wb": "EUU", "region": "Europe"},
    "United Kingdom": {"iso": "GBR", "wb": "GBR", "region": "Europe"},
    "Germany":        {"iso": "DEU", "wb": "DEU", "region": "Europe"},
    "France":         {"iso": "FRA", "wb": "FRA", "region": "Europe"},
    "Japan":          {"iso": "JPN", "wb": "JPN", "region": "Asia-Pacific"},
    "South Korea":    {"iso": "KOR", "wb": "KOR", "region": "Asia-Pacific"},
    "China":          {"iso": "CHN", "wb": "CHN", "region": "Asia-Pacific"},
    "India":          {"iso": "IND", "wb": "IND", "region": "Asia-Pacific"},
    "Australia":      {"iso": "AUS", "wb": "AUS", "region": "Asia-Pacific"},
    "Taiwan":         {"iso": "TWN", "wb": "TWN", "region": "Asia-Pacific"},
    "Canada":         {"iso": "CAN", "wb": "CAN", "region": "Americas"},
    "Brazil":         {"iso": "BRA", "wb": "BRA", "region": "Americas"},
    "Mexico":         {"iso": "MEX", "wb": "MEX", "region": "Americas"},
    "Indonesia":      {"iso": "IDN", "wb": "IDN", "region": "Asia-Pacific"},
}

COUNTRY_SERIES: Dict[str, Dict[str, MacroSeries]] = {
    "United States": {
        "inflation": MacroSeries("inflation", "Inflation", "CPIAUCSL", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "UNRATE", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "FEDFUNDS", "monthly", "%", False),
    },
    "Euro Area": {
        "inflation": MacroSeries("inflation", "Inflation", "CP0000EZ19M086NEST", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTEZM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "ECBDFR", "daily", "%", False),
    },
    "United Kingdom": {
        "inflation": MacroSeries("inflation", "Inflation", "CPGRLE01GBM659N", "monthly", "%", False),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTGBM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "IR3TIB01GBM156N", "monthly", "%", False),
    },
    "Germany": {
        "inflation": MacroSeries("inflation", "Inflation", "DEUCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTDEM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "ECBDFR", "daily", "%", False),
    },
    "France": {
        "inflation": MacroSeries("inflation", "Inflation", "FRACPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTFRM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "ECBDFR", "daily", "%", False),
    },
    "Japan": {
        "inflation": MacroSeries("inflation", "Inflation", "JPNCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTJPM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "IR3TIB01JPM156N", "monthly", "%", False),
    },
    "South Korea": {
        "inflation": MacroSeries("inflation", "Inflation", "KORCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTKRM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "IR3TIB01KRM156N", "monthly", "%", False),
    },
    "China": {
        "inflation": MacroSeries("inflation", "Inflation", "CHNCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTCNQ156S", "quarterly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRCNM193N", "monthly", "%", False),
    },
    "India": {
        "inflation": MacroSeries("inflation", "Inflation", "INDCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTINQ156S", "quarterly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRINM193N", "monthly", "%", False),
    },
    "Australia": {
        "inflation": MacroSeries("inflation", "Inflation", "AUSCPIALLQINMEI", "quarterly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTAUM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "IR3TIB01AUM156N", "monthly", "%", False),
    },
    "Taiwan": {
        "inflation": MacroSeries("inflation", "Inflation", "TWNCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTTWQ156S", "quarterly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRTWM193N", "monthly", "%", False),
    },
    "Canada": {
        "inflation": MacroSeries("inflation", "Inflation", "CANCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRHUTTTTCAM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "IR3TIB01CAM156N", "monthly", "%", False),
    },
    "Brazil": {
        "inflation": MacroSeries("inflation", "Inflation", "BRACPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTBRQ156S", "quarterly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRBRM193N", "monthly", "%", False),
    },
    "Mexico": {
        "inflation": MacroSeries("inflation", "Inflation", "MEXCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTMXM156S", "monthly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRMXM193N", "monthly", "%", False),
    },
    "Indonesia": {
        "inflation": MacroSeries("inflation", "Inflation", "IDNCPIALLMINMEI", "monthly", "%", False, is_index=True),
        "unemployment": MacroSeries("unemployment", "Unemployment", "LRUN64TTIDQ156S", "quarterly", "%", False),
        "policy_rate": MacroSeries("policy_rate", "Policy Rate", "INTDSRIDM193N", "monthly", "%", False),
    },
}

_WB_INDICATORS = {
    "inflation": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",
    "debt_gdp": "GC.DOD.TOTL.GD.ZS",
}

WB_FALLBACK: Dict[tuple[str, str], tuple[str, str]] = {}
for _cname, _meta in COUNTRY_META.items():
    _wb = _meta["wb"]
    for _field, _indicator in _WB_INDICATORS.items():
        WB_FALLBACK[(_cname, _field)] = (_wb, _indicator)

_STALE_MONTHS = 18

ASSET_VALUATION_PROXIES = [
    {"asset": "US Equities", "symbol": "SPY", "lookback": "5y"},
    {"asset": "Tech Growth", "symbol": "QQQ", "lookback": "5y"},
    {"asset": "Gold", "symbol": "GLD", "lookback": "5y"},
    {"asset": "Oil", "symbol": "USO", "lookback": "5y"},
    {"asset": "Long Bonds", "symbol": "TLT", "lookback": "5y"},
    {"asset": "Bitcoin", "symbol": "BTC-USD", "lookback": "5y"},
]


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        if np.isnan(number) or np.isinf(number):
            return None
        return number
    except (TypeError, ValueError):
        return None


def _zscore(values: List[float]) -> Optional[float]:
    if len(values) < 6:
        return None
    std = float(np.std(values))
    if std == 0:
        return 0.0
    return float((values[-1] - np.mean(values)) / std)


def _signal_label(zscore: Optional[float], higher_is_better: bool) -> str:
    if zscore is None:
        return "neutral"
    effective = zscore if higher_is_better else -zscore
    if effective >= 0.75:
        return "bullish"
    if effective <= -0.75:
        return "bearish"
    return "neutral"


def _series_to_pct_change(series) -> Any:
    if series is None or series.empty or len(series) < 13:
        return series
    return series.pct_change(12) * 100


def _fetch_fred_series(fred_code: str):
    import pandas as pd
    import requests
    start = datetime(2014, 1, 1)
    try:
        from pandas_datareader import data as web

        return web.DataReader(fred_code, "fred", start=start).dropna()
    except Exception:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_code}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        df = pd.read_csv(StringIO(response.text))
        date_column = "DATE" if "DATE" in df.columns else "observation_date"
        df[date_column] = pd.to_datetime(df[date_column])
        df = df[df[date_column] >= pd.Timestamp(start)]
        df[fred_code] = pd.to_numeric(df[fred_code], errors="coerce")
        return df.set_index(date_column)[[fred_code]].dropna()


def _fetch_worldbank_latest(country_code: str, indicator: str) -> Optional[float]:
    """Fetch the most recent value from the World Bank API."""
    import requests
    try:
        url = (
            f"https://api.worldbank.org/v2/country/{country_code}"
            f"/indicator/{indicator}?format=json&per_page=5&mrv=3"
        )
        resp = requests.get(url, timeout=12)
        data = resp.json()
        if len(data) > 1 and data[1]:
            for item in data[1]:
                val = item.get("value")
                if val is not None:
                    return round(float(val), 2)
    except Exception:
        pass
    return None


def _is_stale(series) -> bool:
    """Return True if the latest data point is older than _STALE_MONTHS."""
    try:
        import pandas as pd
        latest_date = pd.Timestamp(series.index[-1])
        cutoff = pd.Timestamp(datetime.utcnow() - timedelta(days=_STALE_MONTHS * 30))
        return latest_date < cutoff
    except Exception:
        return True


def _fetch_series_payload(
    series_def: MacroSeries,
    country: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    try:
        series = _fetch_fred_series(series_def.fred_code)
        fred_ok = series is not None and not series.empty
        stale = _is_stale(series) if fred_ok else True

        values = series.iloc[:, 0] if fred_ok else None
        if fred_ok and series_def.is_index:
            values = _series_to_pct_change(values)
            values = values.dropna() if values is not None else None

        latest: Optional[float] = None
        z: Optional[float] = None

        if values is not None and not values.empty:
            latest = _safe_float(values.iloc[-1])
            z = _zscore([float(v) for v in values.tail(60).tolist() if _safe_float(v) is not None])

        if stale and country:
            wb_key = (country, series_def.key)
            if wb_key in WB_FALLBACK:
                wb_country, wb_indicator = WB_FALLBACK[wb_key]
                wb_val = _fetch_worldbank_latest(wb_country, wb_indicator)
                if wb_val is not None:
                    latest = wb_val

        if latest is None and z is None:
            return None

        direction = 0.0 if z is None else (z if series_def.higher_is_better else -z)
        return {
            "key": series_def.key,
            "label": series_def.label,
            "value": round(latest, 2) if latest is not None else None,
            "unit": series_def.unit,
            "zscore": round(z, 2) if z is not None else None,
            "signal": _signal_label(z, series_def.higher_is_better),
            "trend_score": round(direction, 2),
        }
    except Exception:
        return None


def _build_cycle_heatmap() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for series_def in US_SERIES:
        payload = _fetch_series_payload(series_def)
        if payload:
            items.append(payload)
    return items


def _build_country_heatmap() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for country, mappings in COUNTRY_SERIES.items():
        meta = COUNTRY_META.get(country, {})
        metrics: Dict[str, Any] = {
            "country": country,
            "region": meta.get("region", "Other"),
        }
        scores: List[float] = []

        for field_name, series_def in mappings.items():
            payload = _fetch_series_payload(series_def, country=country)
            if payload is None:
                wb_key = (country, field_name)
                if wb_key in WB_FALLBACK:
                    wb_country, wb_indicator = WB_FALLBACK[wb_key]
                    wb_val = _fetch_worldbank_latest(wb_country, wb_indicator)
                    if wb_val is not None:
                        metrics[field_name] = wb_val
                        continue
                metrics[field_name] = None
                continue
            metrics[field_name] = payload["value"]
            if payload["trend_score"] is not None:
                scores.append(float(payload["trend_score"]))

        for extra in ("gdp_growth", "debt_gdp"):
            wb_key = (country, extra)
            if wb_key in WB_FALLBACK:
                wb_country, wb_indicator = WB_FALLBACK[wb_key]
                metrics[extra] = _fetch_worldbank_latest(wb_country, wb_indicator)
            else:
                metrics[extra] = None

        metrics["score"] = round(float(np.mean(scores)), 2) if scores else None
        rows.append(metrics)
    return rows


def _build_asset_valuation() -> List[Dict[str, Any]]:
    import yfinance as yf

    valuation_rows: List[Dict[str, Any]] = []
    for asset in ASSET_VALUATION_PROXIES:
        try:
            hist = yf.Ticker(asset["symbol"]).history(period=asset["lookback"])
            if hist is None or hist.empty or "Close" not in hist:
                continue
            closes = hist["Close"].dropna()
            if closes.empty:
                continue
            latest = float(closes.iloc[-1])
            mean_value = float(closes.mean())
            z = _zscore(closes.tail(252 * 3).astype(float).tolist())
            valuation_rows.append({
                "asset": asset["asset"],
                "symbol": asset["symbol"],
                "price": round(latest, 2),
                "history_mean": round(mean_value, 2),
                "zscore": round(z, 2) if z is not None else None,
                "status": "overvalued" if z is not None and z >= 0.75 else "undervalued" if z is not None and z <= -0.75 else "neutral",
            })
        except Exception:
            continue
    return valuation_rows


@_cached_snapshot
def get_macro_cycle_snapshot() -> Dict[str, Any]:
    """Return macro cycle, country heatmap, and asset valuation snapshot."""
    cycle = _build_cycle_heatmap()
    country_heatmap = _build_country_heatmap()
    asset_valuation = _build_asset_valuation()

    scores = [item["trend_score"] for item in cycle if item.get("trend_score") is not None]
    cycle_score = round(float(np.mean(scores)), 2) if scores else 0.0
    if cycle_score >= 0.5:
        regime = "Expansion"
    elif cycle_score <= -0.5:
        regime = "Contraction"
    else:
        regime = "Transition"

    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "cycle_score": cycle_score,
        "regime": regime,
        "cycle_heatmap": cycle,
        "country_heatmap": country_heatmap,
        "asset_valuation": asset_valuation,
    }


_SUBFACTOR_CATEGORIES: Dict[str, List[MacroSeries]] = {
    "Growth": [
        MacroSeries("gdp_growth", "Real GDP Growth", "A191RL1Q225SBEA", "quarterly", "%", True),
        MacroSeries("ism_pmi", "ISM Manufacturing PMI", "MANEMP", "monthly", "idx", True, is_index=False),
        MacroSeries("industrial_prod", "Industrial Production", "INDPRO", "monthly", "%", True, is_index=True),
        MacroSeries("retail_sales", "Retail Sales", "RSXFS", "monthly", "%", True, is_index=True),
    ],
    "Prices": [
        MacroSeries("cpi_yoy", "CPI YoY", "CPIAUCSL", "monthly", "%", False, is_index=True),
        MacroSeries("core_cpi", "Core CPI", "CPILFESL", "monthly", "%", False, is_index=True),
        MacroSeries("ppi", "PPI", "PPIACO", "monthly", "%", False, is_index=True),
        MacroSeries("pce", "PCE Price Index", "PCEPI", "monthly", "%", False, is_index=True),
    ],
    "Labor": [
        MacroSeries("unemployment", "Unemployment Rate", "UNRATE", "monthly", "%", False),
        MacroSeries("nonfarm", "Nonfarm Payrolls", "PAYEMS", "monthly", "K", True, is_index=False),
        MacroSeries("initial_claims", "Initial Claims", "ICSA", "weekly", "K", False),
        MacroSeries("participation", "Participation Rate", "CIVPART", "monthly", "%", True),
    ],
    "Financial": [
        MacroSeries("yield_spread", "10Y-2Y Spread", "T10Y2Y", "daily", "bp", True),
        MacroSeries("vix", "VIX", "VIXCLS", "daily", "idx", False),
        MacroSeries("credit_spread", "BAA-AAA Spread", "BAAFFM", "monthly", "bp", False),
        MacroSeries("fed_funds", "Fed Funds Rate", "FEDFUNDS", "monthly", "%", False),
    ],
}


def _subfactor_3m_change(series) -> Optional[float]:
    """Compute 3-month change from a pandas Series."""
    if series is None or len(series) < 4:
        return None
    try:
        recent = float(series.iloc[-1])
        past = float(series.iloc[-4]) if len(series) >= 4 else float(series.iloc[0])
        if past == 0:
            return None
        return round((recent - past) / abs(past) * 100, 2)
    except Exception:
        return None


def _subfactor_signal(zscore: Optional[float], change_3m: Optional[float], higher_is_better: bool) -> str:
    """Return improving / neutral / deteriorating."""
    if change_3m is None and zscore is None:
        return "neutral"
    if change_3m is not None:
        effective = change_3m if higher_is_better else -change_3m
        if effective > 1.5:
            return "improving"
        if effective < -1.5:
            return "deteriorating"
    if zscore is not None:
        effective_z = zscore if higher_is_better else -zscore
        if effective_z > 0.5:
            return "improving"
        if effective_z < -0.5:
            return "deteriorating"
    return "neutral"


_cached_subfactors = cached("macro_subfactors", ttl_seconds=3600)


@_cached_subfactors
def get_subfactor_breakdown() -> Dict[str, Any]:
    """Return 4-category × 4-indicator subfactor breakdown with cycle stage."""
    categories: Dict[str, Any] = {}
    all_scores: List[float] = []

    for cat_name, indicators in _SUBFACTOR_CATEGORIES.items():
        items: List[Dict[str, Any]] = []
        cat_scores: List[float] = []

        for s in indicators:
            try:
                raw = _fetch_fred_series(s.fred_code)
                if raw is None or raw.empty:
                    items.append({"key": s.key, "label": s.label, "value": None, "change_3m": None, "zscore": None, "signal": "neutral"})
                    continue
                values = raw.iloc[:, 0]
                if s.is_index:
                    values = _series_to_pct_change(values)
                    values = values.dropna() if values is not None else values
                if values is None or values.empty:
                    items.append({"key": s.key, "label": s.label, "value": None, "change_3m": None, "zscore": None, "signal": "neutral"})
                    continue

                latest = _safe_float(values.iloc[-1])
                z = _zscore([float(v) for v in values.tail(60).tolist() if _safe_float(v) is not None])
                change = _subfactor_3m_change(values)
                signal = _subfactor_signal(z, change, s.higher_is_better)

                if z is not None:
                    effective = z if s.higher_is_better else -z
                    cat_scores.append(effective)
                    all_scores.append(effective)

                items.append({
                    "key": s.key,
                    "label": s.label,
                    "value": round(latest, 2) if latest is not None else None,
                    "unit": s.unit,
                    "change_3m": change,
                    "zscore": round(z, 2) if z is not None else None,
                    "signal": signal,
                })
            except Exception:
                items.append({"key": s.key, "label": s.label, "value": None, "change_3m": None, "zscore": None, "signal": "neutral"})

        cat_score = round(float(np.mean(cat_scores)), 2) if cat_scores else 0.0
        categories[cat_name] = {"score": cat_score, "indicators": items}

    # Determine cycle stage from composite score
    composite = round(float(np.mean(all_scores)), 2) if all_scores else 0.0
    growth_score = categories.get("Growth", {}).get("score", 0)
    price_score = categories.get("Prices", {}).get("score", 0)

    # 4-stage cycle: growth momentum + price momentum
    if growth_score > 0 and price_score <= 0:
        stage = "Early Expansion"
    elif growth_score > 0 and price_score > 0:
        stage = "Late Expansion"
    elif growth_score <= 0 and price_score > 0:
        stage = "Early Contraction"
    else:
        stage = "Late Contraction"

    return {
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "composite_score": composite,
        "cycle_stage": stage,
        "categories": categories,
    }


def get_country_series(country: str, indicator: str, period: str = "5y") -> Dict[str, Any]:
    """Return a time series for a single country/indicator pair."""
    mappings = COUNTRY_SERIES.get(country)
    if not mappings or indicator not in mappings:
        return {"country": country, "indicator": indicator, "series": [], "error": "Not found"}

    series_def = mappings[indicator]
    try:
        raw = _fetch_fred_series(series_def.fred_code)
        if raw is None or raw.empty:
            return {"country": country, "indicator": indicator, "series": []}

        values = raw.iloc[:, 0]
        if series_def.is_index:
            values = _series_to_pct_change(values)
            values = values.dropna() if values is not None else values

        period_map = {"3y": 36, "5y": 60, "10y": 120}
        months = period_map.get(period, 60)
        values = values.tail(months)

        series_data = [
            {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 4)}
            for d, v in values.items()
            if _safe_float(v) is not None
        ]
        return {
            "country": country,
            "indicator": indicator,
            "label": series_def.label,
            "unit": series_def.unit,
            "series": series_data,
        }
    except Exception as e:
        return {"country": country, "indicator": indicator, "series": [], "error": str(e)}
