"""News aggregation from Finviz RSS and Google News RSS.

Fetches, deduplicates, and sorts financial news articles for a given
ticker/company combination.  No API keys required -- uses public RSS feeds.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError
from email.utils import parsedate_to_datetime


_USER_AGENT = "ATLAS-Terminal/1.0 (news aggregator)"
_TIMEOUT_SEC = 10


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_xml(url: str) -> Optional[str]:
    """Fetch a URL and return its body as a string, or ``None`` on error."""
    try:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, Exception):
        return None


def _parse_rss_items(xml_text: str) -> List[Dict[str, Any]]:
    """Parse standard RSS 2.0 ``<item>`` elements into dicts."""
    items: List[Dict[str, Any]] = []
    if not xml_text:
        return items
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date_str = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()
        source = (item.findtext("source") or "").strip()

        pub_dt: Optional[datetime] = None
        if pub_date_str:
            try:
                pub_dt = parsedate_to_datetime(pub_date_str)
            except (ValueError, TypeError):
                pass

        if title and link:
            items.append({
                "title": title,
                "link": link,
                "published": pub_dt.isoformat() if pub_dt else pub_date_str,
                "published_dt": pub_dt,
                "description": description[:500] if description else "",
                "source": source,
            })
    return items


def _dedup_by_title(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate articles based on normalised title."""
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for art in articles:
        key = re.sub(r"\s+", " ", art["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique.append(art)
    return unique


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_finviz_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetch recent news for *ticker* from the Finviz RSS feed.

    Parameters
    ----------
    ticker:
        Stock ticker symbol (e.g. ``'AAPL'``).

    Returns
    -------
    list[dict]
        Each dict has keys: ``title``, ``link``, ``published``,
        ``description``, ``source``.
    """
    if not ticker or not ticker.strip():
        return []
    url = f"https://finviz.com/quote.ashx?t={ticker.strip().upper()}&ty=c&p=d&b=1"
    # Finviz RSS endpoint
    rss_url = f"https://finviz.com/news_export.ashx?t={ticker.strip().upper()}"
    xml = _fetch_xml(rss_url)
    if not xml:
        return []
    items = _parse_rss_items(xml)
    for item in items:
        if not item.get("source"):
            item["source"] = "Finviz"
    return items


def fetch_google_news(company_name: str) -> List[Dict[str, Any]]:
    """Fetch recent news for *company_name* from Google News RSS.

    Parameters
    ----------
    company_name:
        Full company name (e.g. ``'Apple Inc.'``).

    Returns
    -------
    list[dict]
        Same structure as :func:`fetch_finviz_news`.
    """
    if not company_name or not company_name.strip():
        return []
    # URL-encode the query
    query = company_name.strip().replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}+stock&hl=en-US&gl=US&ceid=US:en"
    xml = _fetch_xml(rss_url)
    if not xml:
        return []
    items = _parse_rss_items(xml)
    for item in items:
        if not item.get("source"):
            item["source"] = "Google News"
    return items


def aggregate_news(
    ticker: str,
    company_name: str,
    max_articles: int = 30,
) -> List[Dict[str, Any]]:
    """Aggregate news from Finviz and Google News, deduplicated and sorted.

    Parameters
    ----------
    ticker:
        Stock ticker symbol.
    company_name:
        Full company name for broader search coverage.
    max_articles:
        Maximum number of articles to return (default 30).

    Returns
    -------
    list[dict]
        Deduplicated articles sorted by publication time (newest first).
        Each dict has: ``title``, ``link``, ``published``, ``description``,
        ``source``.
    """
    finviz_articles = fetch_finviz_news(ticker)
    google_articles = fetch_google_news(company_name)

    all_articles = finviz_articles + google_articles
    unique = _dedup_by_title(all_articles)

    # Sort by datetime (newest first); articles without a parseable date go last
    def sort_key(art: Dict[str, Any]) -> float:
        dt = art.get("published_dt")
        if dt is not None:
            return -dt.timestamp()
        return float("inf")

    unique.sort(key=sort_key)

    # Strip internal datetime field before returning
    for art in unique:
        art.pop("published_dt", None)

    return unique[:max_articles]
