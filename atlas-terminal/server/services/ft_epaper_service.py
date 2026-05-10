"""FT daily news ingestion via public RSS feeds plus cached Korean translation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from server.db.unified_repo import repo
from server.services.gemini_service import generate_text

logger = logging.getLogger(__name__)

RSS_FEEDS: list[tuple[str, str]] = [
    ("Home", "https://www.ft.com/rss/home/uk"),
    ("World", "https://www.ft.com/rss/world"),
    ("Companies", "https://www.ft.com/companies?format=rss"),
    ("Markets", "https://www.ft.com/markets?format=rss"),
]
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-GB,en;q=0.9",
}
HEADLINE_TTL_SECONDS = 86_400
TRANSLATION_TTL_SECONDS = 31_536_000
BATCH_SIZE = 6


def _hash_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:20]


def _date_cache_key(target_date: date, limit: int) -> str:
    return f"ft:daily:{target_date.isoformat()}:{limit}"


def _meta_cache_key(url: str) -> str:
    return f"ft:meta:{_hash_url(url)}"


def _translation_cache_key(url: str) -> str:
    return f"ft_trans:{_hash_url(url)}"


def _clean_json_payload(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\[\s*{.*}\s*\])", text, flags=re.S)
    if match:
        return match.group(1)
    return text


def _entry_datetime(entry: Any) -> datetime | None:
    parsed = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if parsed:
        try:
            return datetime(*parsed[:6], tzinfo=timezone.utc)
        except Exception:
            return None
    published = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if published:
        try:
            dt = parsedate_to_datetime(published)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _entry_section(entry: Any, fallback: str) -> str:
    tags = getattr(entry, "tags", None) or []
    if tags:
        for tag in tags:
            term = getattr(tag, "term", None) or (tag.get("term") if isinstance(tag, dict) else None)
            if term:
                return str(term)
    category = getattr(entry, "category", None)
    return str(category or fallback)


async def _fetch_feed_entries(client: httpx.AsyncClient, section: str, url: str) -> list[dict[str, Any]]:
    response = await client.get(url)
    response.raise_for_status()
    parsed = feedparser.parse(response.text)
    rows: list[dict[str, Any]] = []
    for entry in parsed.entries:
        published_at = _entry_datetime(entry)
        if published_at is None:
            continue
        link = getattr(entry, "link", None)
        title = getattr(entry, "title", None)
        if not link or not title:
            continue
        rows.append(
            {
                "url": str(link),
                "title_en": str(title).strip(),
                "lede_en": getattr(entry, "summary", None),
                "section": _entry_section(entry, section),
                "published_at": published_at.isoformat(),
            }
        )
    return rows


async def _fetch_article_meta(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
    cached = await repo.cache_get(_meta_cache_key(url))
    if isinstance(cached, dict):
        return cached

    try:
        response = await client.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        description = None
        image = None
        for prop in ("og:description", "twitter:description", "description"):
            node = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
            if node and node.get("content"):
                description = str(node["content"]).strip()
                if description:
                    break
        for prop in ("og:image", "twitter:image"):
            node = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
            if node and node.get("content"):
                image = str(node["content"]).strip()
                if image:
                    break
        payload = {"lede_en": description, "image": image}
    except Exception as exc:
        logger.warning("ft_epaper: article meta fetch failed for %s: %s", url, exc)
        payload = {"lede_en": None, "image": None}

    await repo.cache_set(_meta_cache_key(url), payload, ttl=HEADLINE_TTL_SECONDS)
    return payload


async def fetch_headlines(target_date: date, limit: int = 30) -> list[dict[str, Any]]:
    """Fetch FT RSS headlines for a given date, enriched with public og metadata."""

    cache_key = _date_cache_key(target_date, limit)
    cached = await repo.cache_get(cache_key)
    if isinstance(cached, list):
        return cached

    async with httpx.AsyncClient(headers=HEADERS, timeout=15.0, follow_redirects=True) as client:
        feed_rows = await asyncio.gather(
            *[_fetch_feed_entries(client, section, url) for section, url in RSS_FEEDS],
            return_exceptions=True,
        )

        entries: list[dict[str, Any]] = []
        for result in feed_rows:
            if isinstance(result, Exception):
                logger.warning("ft_epaper: RSS fetch failed: %s", result)
                continue
            entries.extend(result)

        seen: set[str] = set()
        filtered: list[dict[str, Any]] = []
        for item in sorted(entries, key=lambda row: row["published_at"], reverse=True):
            published_date = datetime.fromisoformat(item["published_at"]).date()
            if published_date != target_date:
                continue
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            filtered.append(item)
            if len(filtered) >= limit:
                break

        semaphore = asyncio.Semaphore(4)

        async def enrich(item: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                meta = await _fetch_article_meta(client, item["url"])
                return {
                    **item,
                    "lede_en": item.get("lede_en") or meta.get("lede_en"),
                    "image": meta.get("image"),
                    "title_ko": None,
                    "lede_ko": None,
                }

        payload = await asyncio.gather(*[enrich(item) for item in filtered])

    await repo.cache_set(cache_key, payload, ttl=HEADLINE_TTL_SECONDS)
    return payload


async def translate_headlines(items: list[dict[str, Any]], api_key: str | None = None) -> list[dict[str, Any]]:
    """Batch-translate uncached FT items into Korean using Gemini."""

    if not items:
        return []

    hydrated: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    for item in items:
        cached = await repo.cache_get(_translation_cache_key(item["url"]))
        if isinstance(cached, dict):
            hydrated.append({**item, "title_ko": cached.get("title_ko"), "lede_ko": cached.get("lede_ko")})
        else:
            hydrated.append(dict(item))
            pending.append(item)

    if not pending:
        return hydrated

    try:
        translation_map: dict[str, dict[str, Any]] = {}
        for start in range(0, len(pending), BATCH_SIZE):
            batch = pending[start : start + BATCH_SIZE]
            prompt = (
                "Translate the following Financial Times headlines and ledes into Korean. "
                "Use standard financial terminology (for example: Fed -> 연준, yield -> 수익률, "
                "equities -> 주식, bonds -> 채권). Preserve proper nouns and company names. "
                "Return ONLY valid JSON array with objects {\"url\": string, \"title_ko\": string, \"lede_ko\": string|null}.\n\n"
                f"{json.dumps([{'url': row['url'], 'title_en': row['title_en'], 'lede_en': row.get('lede_en')} for row in batch], ensure_ascii=False)}"
            )
            raw = await generate_text(prompt, temperature=0.2, max_tokens=1400, api_key=api_key)
            parsed = json.loads(_clean_json_payload(raw))
            if not isinstance(parsed, list):
                continue
            for row in parsed:
                if not isinstance(row, dict) or not row.get("url"):
                    continue
                translation_map[str(row["url"])] = {
                    "title_ko": row.get("title_ko"),
                    "lede_ko": row.get("lede_ko"),
                }
    except Exception as exc:
        logger.warning("ft_epaper: Gemini translation failed, returning EN-only payload: %s", exc)
        return hydrated

    final_items: list[dict[str, Any]] = []
    for item in hydrated:
        translated = translation_map.get(item["url"])
        if translated:
            merged = {**item, **translated}
            await repo.cache_set(_translation_cache_key(item["url"]), translated, ttl=TRANSLATION_TTL_SECONDS)
            final_items.append(merged)
        else:
            final_items.append(item)
    return final_items
