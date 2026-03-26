"""Economic calendar service — Investing.com AJAX + TradingEconomics fallback."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from server.services.cache import cached

COUNTRY_FLAGS: Dict[str, str] = {
    "US": "\U0001F1FA\U0001F1F8", "GB": "\U0001F1EC\U0001F1E7", "EU": "\U0001F1EA\U0001F1FA",
    "JP": "\U0001F1EF\U0001F1F5", "KR": "\U0001F1F0\U0001F1F7", "CN": "\U0001F1E8\U0001F1F3",
    "DE": "\U0001F1E9\U0001F1EA", "FR": "\U0001F1EB\U0001F1F7", "AU": "\U0001F1E6\U0001F1FA",
    "CA": "\U0001F1E8\U0001F1E6", "BR": "\U0001F1E7\U0001F1F7", "IN": "\U0001F1EE\U0001F1F3",
    "MX": "\U0001F1F2\U0001F1FD", "ID": "\U0001F1EE\U0001F1E9", "TW": "\U0001F1F9\U0001F1FC",
    "NZ": "\U0001F1F3\U0001F1FF", "CH": "\U0001F1E8\U0001F1ED", "SG": "\U0001F1F8\U0001F1EC",
}

COUNTRY_NAME_TO_CODE: Dict[str, str] = {
    "United States": "US", "United Kingdom": "GB", "Euro Zone": "EU", "European Union": "EU",
    "Japan": "JP", "South Korea": "KR", "China": "CN", "Germany": "DE", "France": "FR",
    "Australia": "AU", "Canada": "CA", "Brazil": "BR", "India": "IN", "Mexico": "MX",
    "Indonesia": "ID", "Taiwan": "TW", "New Zealand": "NZ", "Switzerland": "CH",
    "Singapore": "SG", "Saudi Arabia": "SA", "Italy": "IT", "Spain": "ES",
    "Hong Kong": "HK", "Norway": "NO", "Sweden": "SE",
}


def _parse_number(text: str) -> Optional[float]:
    if not text or text.strip() in ("", "&nbsp;", "-", "\xa0"):
        return None
    cleaned = text.strip().replace(",", "").replace("%", "")
    for suffix, mult in [("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)]:
        if cleaned.endswith(suffix):
            cleaned = cleaned[:-1]
            try:
                return float(cleaned) * mult
            except ValueError:
                return None
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _scrape_investing_ajax(days: int = 7) -> List[Dict[str, Any]]:
    """Scrape Investing.com economic calendar via AJAX POST endpoint."""
    import requests
    from bs4 import BeautifulSoup

    start = datetime.utcnow().strftime("%Y-%m-%d")
    end = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")

    url = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.investing.com/economic-calendar/",
    }
    form = {
        "dateFrom": start,
        "dateTo": end,
        "timeZone": 55,
        "timeFilter": "timeRemain",
        "currentTab": "custom",
        "limit_from": 0,
    }

    try:
        resp = requests.post(url, headers=headers, data=form, timeout=15)
        if resp.status_code != 200:
            return []
        html = resp.json().get("data", "")
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    events: List[Dict[str, Any]] = []
    for row in soup.select("tr[id^='eventRowId']"):
        try:
            tds = row.select("td")
            if not tds:
                continue

            event_time = tds[0].get_text(strip=True) if tds else ""

            flag_span = row.select_one("td.flagCur span")
            country_name = flag_span.get("title", "") if flag_span else ""
            country_code = COUNTRY_NAME_TO_CODE.get(country_name, country_name[:2].upper())

            event_el = row.select_one("td.event a") or row.select_one("td.event")
            indicator = event_el.get_text(strip=True) if event_el else ""
            if not indicator:
                continue

            bulls = row.select("td.sentiment i.grayFullBullishIcon")
            importance = "high" if len(bulls) >= 3 else "medium" if len(bulls) >= 2 else "low"

            eid = row.get("id", "").replace("eventRowId_", "")
            actual_td = row.select_one(f"td#eventActual_{eid}")
            forecast_td = row.select_one(f"td#eventForecast_{eid}")
            previous_td = row.select_one(f"td#eventPrevious_{eid}")

            actual = _parse_number(actual_td.get_text(strip=True)) if actual_td else None
            forecast = _parse_number(forecast_td.get_text(strip=True)) if forecast_td else None
            previous = _parse_number(previous_td.get_text(strip=True)) if previous_td else None

            surprise = None
            surprise_label = "pending"
            if actual is not None and forecast is not None and forecast != 0:
                surprise = round((actual - forecast) / abs(forecast), 4)
                surprise_label = "positive" if surprise > 0.01 else "negative" if surprise < -0.01 else "in-line"

            events.append({
                "datetime": event_time,
                "country": country_code,
                "country_flag": COUNTRY_FLAGS.get(country_code, ""),
                "indicator": indicator,
                "importance": importance,
                "previous": previous,
                "forecast": forecast,
                "actual": actual,
                "surprise": surprise,
                "surprise_label": surprise_label,
            })
        except Exception:
            continue

    return events


def _scrape_tradingeconomics() -> List[Dict[str, Any]]:
    """TradingEconomics calendar as fallback."""
    import requests
    from bs4 import BeautifulSoup

    try:
        resp = requests.get("https://tradingeconomics.com/calendar", headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return []

    events: List[Dict[str, Any]] = []
    for row in soup.select("tr[data-event]"):
        try:
            tds = row.select("td")
            if len(tds) < 8:
                continue

            event_time = tds[0].get_text(strip=True)
            country_code = tds[3].get_text(strip=True).upper()[:2] if tds[3] else ""
            indicator = tds[4].get_text(strip=True) if tds[4] else ""
            if not indicator:
                continue

            actual = _parse_number(tds[5].get_text(strip=True)) if tds[5] else None
            previous = _parse_number(tds[6].get_text(strip=True)) if tds[6] else None
            forecast = _parse_number(tds[7].get_text(strip=True)) if tds[7] else None

            importance = "low"
            stars = row.select("i.calendar-date-1-icon")
            if len(stars) >= 3:
                importance = "high"
            elif len(stars) >= 2:
                importance = "medium"

            surprise = None
            surprise_label = "pending"
            if actual is not None and forecast is not None and forecast != 0:
                surprise = round((actual - forecast) / abs(forecast), 4)
                surprise_label = "positive" if surprise > 0.01 else "negative" if surprise < -0.01 else "in-line"

            events.append({
                "datetime": event_time,
                "country": country_code,
                "country_flag": COUNTRY_FLAGS.get(country_code, ""),
                "indicator": indicator,
                "importance": importance,
                "previous": previous,
                "forecast": forecast,
                "actual": actual,
                "surprise": surprise,
                "surprise_label": surprise_label,
            })
        except Exception:
            continue

    return events


@cached("economic_calendar", ttl_seconds=900)
def _fetch_raw_calendar() -> List[Dict[str, Any]]:
    events = _scrape_investing_ajax(days=14)
    if len(events) < 5:
        events = _scrape_tradingeconomics()
    return events


def get_economic_calendar(
    days: int = 7,
    countries: Optional[List[str]] = None,
    importance: Optional[str] = None,
) -> Dict[str, Any]:
    """Return filtered economic calendar events."""
    events = list(_fetch_raw_calendar())

    if countries:
        upper = {c.upper() for c in countries}
        events = [e for e in events if e["country"] in upper]

    if importance:
        events = [e for e in events if e["importance"] == importance.lower()]

    importance_order = {"high": 0, "medium": 1, "low": 2}
    events.sort(key=lambda e: importance_order.get(e["importance"], 3))

    next_high = next((e for e in events if e["importance"] == "high" and e["surprise_label"] == "pending"), None)

    return {
        "events": events[:150],
        "next_high_impact": next_high,
        "total": len(events),
    }
