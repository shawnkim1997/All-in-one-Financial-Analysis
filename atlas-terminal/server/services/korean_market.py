"""Korean market helpers for KOSPI/KOSDAQ universe search and Naver snapshots."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import unicodedata
from typing import Any

import httpx
from bs4 import BeautifulSoup

from server.utils.ticker_utils import korean_stock_code_from_ticker

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_COMMON_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://finance.naver.com/",
}
_KIND_CORP_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
_NAVER_MAIN_URL = "https://finance.naver.com/item/main.naver"
_UNIVERSE_TTL_SECONDS = 60 * 60 * 12
_NAVER_SNAPSHOT_TTL_SECONDS = 20

_UNIVERSE_LOCK = asyncio.Lock()
_UNIVERSE_CACHE: list[dict[str, Any]] | None = None
_UNIVERSE_BY_CODE: dict[str, dict[str, Any]] = {}
_UNIVERSE_TS = 0.0

_DART_LOOKUP_LOCK = asyncio.Lock()
_DART_LOOKUP: dict[str, dict[str, Any]] | None = None

_SNAPSHOT_LOCK = asyncio.Lock()
_SNAPSHOT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

_MANUAL_ALIASES: dict[str, list[str]] = {
    "000660": ["sk hynix", "skhynix", "하이닉스", "sk 하이닉스", "sk하이닉스"],
    "005930": ["samsung electronics", "삼성전자", "삼성 전자", "삼전"],
    "035420": ["naver", "네이버"],
    "035720": ["kakao", "카카오"],
    "373220": ["lg energy solution", "lg엔솔", "lg에너지솔루션"],
    "207940": ["samsung biologics", "삼성바이오로직스", "삼바"],
}

_STATIC_FALLBACK_UNIVERSE: list[dict[str, Any]] = [
    {
        "ticker": "005930.KS",
        "stock_code": "005930",
        "name": "Samsung Electronics Co., Ltd.",
        "name_ko": "삼성전자",
        "exchange": "KOSPI",
        "market": "Korea Main Board",
        "currency": "KRW",
        "country": "KR",
        "asset_type": "Equity",
        "aliases": _MANUAL_ALIASES["005930"],
    },
    {
        "ticker": "000660.KS",
        "stock_code": "000660",
        "name": "SK hynix Inc.",
        "name_ko": "SK하이닉스",
        "exchange": "KOSPI",
        "market": "Korea Main Board",
        "currency": "KRW",
        "country": "KR",
        "asset_type": "Equity",
        "aliases": _MANUAL_ALIASES["000660"],
    },
    {
        "ticker": "035420.KS",
        "stock_code": "035420",
        "name": "NAVER Corporation",
        "name_ko": "네이버",
        "exchange": "KOSPI",
        "market": "Korea Main Board",
        "currency": "KRW",
        "country": "KR",
        "asset_type": "Equity",
        "aliases": _MANUAL_ALIASES["035420"],
    },
    {
        "ticker": "035720.KS",
        "stock_code": "035720",
        "name": "Kakao Corp.",
        "name_ko": "카카오",
        "exchange": "KOSPI",
        "market": "Korea Main Board",
        "currency": "KRW",
        "country": "KR",
        "asset_type": "Equity",
        "aliases": _MANUAL_ALIASES["035720"],
    },
]


def is_korean_equity_ticker(ticker: str) -> bool:
    normalized = (ticker or "").strip().upper()
    return bool(normalized.endswith(".KS") or normalized.endswith(".KQ") or re.fullmatch(r"\d{6}", normalized))


def _stock_code_from_any(value: str) -> str | None:
    raw = (value or "").strip().upper()
    if re.fullmatch(r"\d{6}", raw):
        return raw
    return korean_stock_code_from_ticker(raw)


def _normalize_search_text(value: str) -> str:
    return (
        unicodedata.normalize("NFKC", value.strip())
        .lower()
        .replace("&", " and ")
        .replace("-", " ")
        .replace(".", " ")
        .replace("/", " ")
        .replace("_", " ")
        .replace("(", " ")
        .replace(")", " ")
    )


def _compact_search_text(value: str) -> str:
    return re.sub(r"\s+", "", _normalize_search_text(value))


def _initials(value: str) -> str:
    return "".join(part[:1] for part in _normalize_search_text(value).split() if part)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _selector_text(soup: BeautifulSoup, selectors: list[str]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return None


def _parse_number(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_int(text: str | None) -> int | None:
    value = _parse_number(text)
    if value is None:
        return None
    return int(value)


def _parse_market_cap_krw(text: str | None) -> float | None:
    if not text:
        return None
    compact = text.replace(" ", "").replace(",", "")
    total = 0

    match_jo = re.search(r"(\d+)조", compact)
    if match_jo:
        total += int(match_jo.group(1)) * 1_000_000_000_000

    match_eok = re.search(r"(\d+)억", compact)
    if match_eok:
        total += int(match_eok.group(1)) * 100_000_000

    if total > 0:
        return float(total)

    match_plain_eok = re.search(r"([\d,]+)억원", text)
    if match_plain_eok:
        return float(int(match_plain_eok.group(1).replace(",", "")) * 100_000_000)

    return None


def _normalize_recommendation(label: str | None) -> str | None:
    if not label:
        return None
    raw = label.strip().lower()
    if any(token in raw for token in ("매수", "buy", "outperform", "strong buy")):
        return "buy"
    if any(token in raw for token in ("중립", "hold", "neutral")):
        return "hold"
    if any(token in raw for token in ("매도", "sell", "underperform")):
        return "sell"
    return label.strip()


def _decode_html(content: bytes, encoding_hint: str | None = None) -> str:
    for encoding in [encoding_hint, "euc-kr", "utf-8"]:
        if not encoding:
            continue
        try:
            return content.decode(encoding, errors="replace")
        except LookupError:
            continue
    return content.decode("utf-8", errors="replace")


def _build_dart_lookup_sync() -> dict[str, dict[str, Any]]:
    key = (os.getenv("DART_API_KEY") or "").strip()
    if not key:
        return {}

    try:
        import dart_fss as dart  # noqa: WPS433
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("korean_market: dart_fss import failed: %s", exc)
        return {}

    try:
        dart.set_api_key(key)
        corp_list = dart.get_corp_list()
    except Exception as exc:
        logger.warning("korean_market: DART corp list load failed: %s", exc)
        return {}

    iterable = []
    try:
        iterable = list(corp_list)
    except Exception:
        iterable = list(getattr(corp_list, "corps", []) or [])

    lookup: dict[str, dict[str, Any]] = {}
    for item in iterable:
        stock_code = str(getattr(item, "stock_code", "") or "").strip()
        if not re.fullmatch(r"\d{6}", stock_code):
            continue
        lookup[stock_code] = {
            "corp_code": getattr(item, "corp_code", None),
            "corp_name": getattr(item, "corp_name", None),
            "corp_eng_name": getattr(item, "corp_eng_name", None),
        }
    return lookup


async def _get_dart_lookup() -> dict[str, dict[str, Any]]:
    global _DART_LOOKUP
    if _DART_LOOKUP is not None:
        return _DART_LOOKUP

    async with _DART_LOOKUP_LOCK:
        if _DART_LOOKUP is not None:
            return _DART_LOOKUP
        _DART_LOOKUP = await asyncio.to_thread(_build_dart_lookup_sync)
        return _DART_LOOKUP


async def _fetch_kind_market(market_type: str, exchange: str, market_label: str) -> list[dict[str, Any]]:
    params = {"method": "download", "marketType": market_type}
    async with httpx.AsyncClient(headers=_COMMON_HEADERS, timeout=20.0, follow_redirects=True) as client:
        response = await client.get(_KIND_CORP_LIST_URL, params=params)
        response.raise_for_status()
    html = _decode_html(response.content, response.encoding)
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        raise ValueError(f"KIND table missing for {exchange}")

    header_cells = table.select("tr th")
    headers = [cell.get_text(" ", strip=True) for cell in header_cells]
    if not headers:
        raise ValueError(f"KIND headers missing for {exchange}")

    body_rows = table.select("tr")
    out: list[dict[str, Any]] = []
    for tr in body_rows[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all("td")]
        if not cells or len(cells) != len(headers):
            continue
        row = dict(zip(headers, cells))
        name_ko = row.get("회사명") or row.get("기업명") or cells[0]
        stock_code = re.sub(r"\D", "", row.get("종목코드") or row.get("종목코드(단축코드)") or "")
        if not re.fullmatch(r"\d{6}", stock_code):
            continue
        ticker = f"{stock_code}.KS" if exchange == "KOSPI" else f"{stock_code}.KQ"
        out.append(
            {
                "ticker": ticker,
                "stock_code": stock_code,
                "name": name_ko,
                "name_ko": name_ko,
                "exchange": exchange,
                "market": market_label,
                "currency": "KRW",
                "country": "KR",
                "asset_type": "Equity",
                "aliases": [name_ko, stock_code, ticker, exchange, market_label],
            }
        )
    return out


def _merge_listing(base: dict[str, Any], dart_lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stock_code = base["stock_code"]
    dart = dart_lookup.get(stock_code, {})
    name_ko = str(base.get("name_ko") or "").strip()
    name_en = str(dart.get("corp_eng_name") or "").strip()
    corp_name = str(dart.get("corp_name") or "").strip()
    display_name = name_en or corp_name or name_ko or base["ticker"]
    aliases = _dedupe_strings(
        [
            *list(base.get("aliases", [])),
            name_ko,
            corp_name,
            name_en,
            display_name,
            *(_MANUAL_ALIASES.get(stock_code) or []),
        ]
    )
    return {
        **base,
        "name": display_name,
        "name_ko": name_ko or corp_name or display_name,
        "name_en": name_en or None,
        "corp_code": dart.get("corp_code"),
        "aliases": aliases,
    }


async def get_korean_stock_universe(force_refresh: bool = False) -> list[dict[str, Any]]:
    global _UNIVERSE_CACHE, _UNIVERSE_BY_CODE, _UNIVERSE_TS

    now = time.monotonic()
    async with _UNIVERSE_LOCK:
        if not force_refresh and _UNIVERSE_CACHE and now - _UNIVERSE_TS < _UNIVERSE_TTL_SECONDS:
            return _UNIVERSE_CACHE
        stale_cache = list(_UNIVERSE_CACHE or [])

    try:
        kospi, kosdaq, dart_lookup = await asyncio.gather(
            _fetch_kind_market("stockMkt", "KOSPI", "Korea Main Board"),
            _fetch_kind_market("kosdaqMkt", "KOSDAQ", "Korea Growth Board"),
            _get_dart_lookup(),
        )
        listings = [_merge_listing(item, dart_lookup) for item in [*kospi, *kosdaq]]
        listings.sort(key=lambda row: row["ticker"])
        by_code = {row["stock_code"]: row for row in listings}
    except Exception as exc:
        logger.warning("korean_market: universe refresh failed: %s", exc)
        if stale_cache:
            return stale_cache
        listings = list(_STATIC_FALLBACK_UNIVERSE)
        by_code = {row["stock_code"]: row for row in listings}

    async with _UNIVERSE_LOCK:
        _UNIVERSE_CACHE = listings
        _UNIVERSE_BY_CODE = by_code
        _UNIVERSE_TS = time.monotonic()
        return _UNIVERSE_CACHE


async def get_korean_listing(ticker_or_code: str) -> dict[str, Any] | None:
    code = _stock_code_from_any(ticker_or_code)
    if not code:
        return None
    universe = await get_korean_stock_universe()
    if code in _UNIVERSE_BY_CODE:
        return _UNIVERSE_BY_CODE[code]
    for listing in universe:
        if listing.get("stock_code") == code:
            return listing
    return None


def _listing_terms(listing: dict[str, Any]) -> list[str]:
    aliases = listing.get("aliases")
    return _dedupe_strings(
        [
            str(listing.get("ticker") or ""),
            str(listing.get("stock_code") or ""),
            str(listing.get("name") or ""),
            str(listing.get("name_ko") or ""),
            str(listing.get("name_en") or ""),
            str(listing.get("exchange") or ""),
            str(listing.get("market") or ""),
            *(aliases if isinstance(aliases, list) else []),
        ]
    )


def _score_listing(listing: dict[str, Any], query: str, compact_query: str) -> int:
    if not query:
        return 0

    terms = _listing_terms(listing)
    best = 0
    has_hangul_query = bool(re.search(r"[가-힣]", query))

    for term in terms:
        normalized = _normalize_search_text(term)
        compact = _compact_search_text(term)
        upper_term = term.strip().upper()

        if upper_term == query.upper():
            best = max(best, 1400 if upper_term.endswith((".KS", ".KQ")) else 1350)
        if normalized == query:
            best = max(best, 1200)
        if compact == compact_query:
            best = max(best, 1150)
        if normalized.startswith(query):
            best = max(best, 900)
        if compact.startswith(compact_query):
            best = max(best, 850)
        if normalized.find(query) >= 0:
            best = max(best, 560)
        if compact_query and compact.find(compact_query) >= 0:
            best = max(best, 520)
        if compact_query and len(compact_query) >= 2 and _initials(term) == compact_query:
            best = max(best, 480)

    if has_hangul_query and re.search(r"[가-힣]", str(listing.get("name_ko") or "")):
        best += 60
    if "kospi" in query and listing.get("exchange") == "KOSPI":
        best += 80
    if "kosdaq" in query and listing.get("exchange") == "KOSDAQ":
        best += 80

    return best


async def search_korean_tickers(query: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    compact_query = _compact_search_text(query)
    if not normalized_query:
        return []

    universe = await get_korean_stock_universe()
    ranked = [
        (listing, _score_listing(listing, normalized_query, compact_query))
        for listing in universe
    ]
    ranked = [item for item in ranked if item[1] > 0]
    ranked.sort(key=lambda item: (-item[1], item[0]["ticker"]))
    results: list[dict[str, Any]] = []
    for listing, _score in ranked[:limit]:
        results.append(
            {
                "ticker": listing["ticker"],
                "symbol": listing["ticker"],
                "name": listing["name"],
                "name_ko": listing.get("name_ko"),
                "exchange": listing["exchange"],
                "market": listing.get("market"),
                "currency": listing.get("currency", "KRW"),
                "country": listing.get("country", "KR"),
                "asset_type": listing.get("asset_type", "Equity"),
                "aliases": listing.get("aliases", []),
                "stock_code": listing.get("stock_code"),
            }
        )
    return results


def _parse_naver_snapshot(html: str, stock_code: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text("\n", strip=True)

    title = soup.title.get_text(" ", strip=True) if soup.title else stock_code
    name = title.split(":")[0].strip()

    price_text = _selector_text(
        soup,
        [
            "#chart_area #_nowVal",
            "#middle .today .no_today .blind",
            ".today .no_today .blind",
            "p.no_today span.blind",
        ],
    )
    change_text = _selector_text(
        soup,
        [
            "#chart_area #_diff",
            "#middle .today .no_exday em span.blind",
            ".today .no_exday em span.blind",
        ],
    )
    rate_text = _selector_text(
        soup,
        [
            "#chart_area #_rate",
            "#middle .today .no_exday .blind:last-child",
            ".today .no_exday .blind:last-child",
        ],
    )
    market_sum_text = _selector_text(soup, ["#_market_sum"])

    current_price = _parse_number(price_text)
    if current_price is None:
        current_match = re.search(r"현재가\s+([\d,]+)", text)
        current_price = _parse_number(current_match.group(1) if current_match else None)

    direction_match = re.search(r"전일대비\s+(상승|하락|보합)", text)
    direction = direction_match.group(1) if direction_match else None
    change = _parse_number(change_text)
    if change is None:
        change_match = re.search(r"전일대비\s+(?:상승|하락|보합)\s+([\d,]+)", text)
        change = _parse_number(change_match.group(1) if change_match else None)

    change_pct = _parse_number(rate_text)
    if change_pct is None:
        rate_match = re.search(r"(?:플러스|마이너스)?\s*([\d.]+)\s*퍼센트", text)
        change_pct = _parse_number(rate_match.group(1) if rate_match else None)
    if direction == "하락" and change_pct is not None:
        change_pct *= -1
        if change is not None:
            change *= -1

    market_cap = _parse_market_cap_krw(market_sum_text)
    if market_cap is None:
        market_cap_match = re.search(r"시가총액(?:\s+시가총액)?\s+([0-9,\s조억]+)", text)
        market_cap = _parse_market_cap_krw(market_cap_match.group(1) if market_cap_match else None)

    high_low_match = re.search(r"52주최고\s*[l|I]\s*최저\s+([\d,]+)\s*[l|I]\s*([\d,]+)", text)
    trailing_match = re.search(r"PER/EPS\s+([\d.]+)\s+배\s*[l|I]\s*([\d,]+)\s+원", text)
    forward_match = re.search(r"추정PER\s*[l|I]\s*EPS\s+([\d.]+)\s+배\s*[l|I]\s*([\d,]+)\s+원", text)
    target_match = re.search(r"투자의견\s+투자의견\s*[l|I]\s*목표주가\s+([\d.]+)\s+([가-힣A-Za-z]+)\s*[l|I]\s*([\d,]+)", text)
    dividend_match = re.search(r"배당수익률\s+([\d.]+)%", text)
    shares_match = re.search(r"상장주식수\s+([\d,]+)", text)
    market_match = re.search(r"종목코드\s+\d{6}\s+(코스피|코스닥)", text)
    summary_match = re.search(r"기업개요\s+(.*?)\s+출처\s*:\s*에프앤가이드", text, re.S)

    market_label = market_match.group(1) if market_match else None
    exchange = "KOSDAQ" if market_label == "코스닥" else "KOSPI"

    return {
        "stock_code": stock_code,
        "name": name,
        "current_price": current_price,
        "change": change,
        "change_pct": change_pct,
        "market_cap": market_cap,
        "fifty_two_week_high": _parse_number(high_low_match.group(1) if high_low_match else None),
        "fifty_two_week_low": _parse_number(high_low_match.group(2) if high_low_match else None),
        "pe_ratio": _parse_number(trailing_match.group(1) if trailing_match else None),
        "trailing_eps": _parse_number(trailing_match.group(2) if trailing_match else None),
        "forward_pe": _parse_number(forward_match.group(1) if forward_match else None),
        "forward_eps": _parse_number(forward_match.group(2) if forward_match else None),
        "dividend_yield": _parse_number(dividend_match.group(1) if dividend_match else None),
        "target_mean_price": _parse_number(target_match.group(3) if target_match else None),
        "recommendation": _normalize_recommendation(target_match.group(2) if target_match else None),
        "analyst_score": _parse_number(target_match.group(1) if target_match else None),
        "shares_outstanding": _parse_int(shares_match.group(1) if shares_match else None),
        "exchange": exchange,
        "market_label": market_label,
        "currency": "KRW",
        "country": "KR",
        "description": re.sub(r"\s+", " ", summary_match.group(1)).strip() if summary_match else None,
        "source": "naver_finance",
    }


async def get_naver_stock_snapshot(ticker_or_code: str, force_refresh: bool = False) -> dict[str, Any] | None:
    stock_code = _stock_code_from_any(ticker_or_code)
    if not stock_code:
        return None

    now = time.monotonic()
    async with _SNAPSHOT_LOCK:
        cached = _SNAPSHOT_CACHE.get(stock_code)
        if not force_refresh and cached and now - cached[0] < _NAVER_SNAPSHOT_TTL_SECONDS:
            return cached[1]

    try:
        async with httpx.AsyncClient(headers=_COMMON_HEADERS, timeout=15.0, follow_redirects=True) as client:
            response = await client.get(_NAVER_MAIN_URL, params={"code": stock_code})
            response.raise_for_status()
        html = _decode_html(response.content, response.encoding)
        snapshot = _parse_naver_snapshot(html, stock_code)
        listing = await get_korean_listing(stock_code)
        if listing:
            snapshot["ticker"] = listing["ticker"]
            snapshot["name_ko"] = listing.get("name_ko")
            snapshot["name_en"] = listing.get("name_en")
            snapshot["name"] = listing.get("name_en") or snapshot.get("name") or listing.get("name") or listing.get("name_ko")
            snapshot["exchange"] = listing.get("exchange", snapshot.get("exchange"))
            snapshot["market"] = listing.get("market")
            snapshot["corp_code"] = listing.get("corp_code")
        else:
            snapshot["ticker"] = f"{stock_code}.KS"
            snapshot["market"] = "Korea Main Board" if snapshot.get("exchange") == "KOSPI" else "Korea Growth Board"

        async with _SNAPSHOT_LOCK:
            _SNAPSHOT_CACHE[stock_code] = (time.monotonic(), snapshot)
        return snapshot
    except Exception as exc:
        logger.warning("korean_market: Naver snapshot failed for %s: %s", stock_code, exc)
        async with _SNAPSHOT_LOCK:
            cached = _SNAPSHOT_CACHE.get(stock_code)
            return cached[1] if cached else None
