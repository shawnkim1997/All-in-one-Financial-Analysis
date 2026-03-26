"""News aggregation: Finviz (HTML table), Google News RSS, Yahoo Finance RSS.

Single module used by :mod:`server.routers.news` — no duplicated fetch logic.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import quote_plus

_USER_AGENT = "ATLAS-Terminal/1.0 (news aggregator)"


def _dedup_merge(items: List[Dict[str, str]], max_n: int) -> List[Dict[str, str]]:
    seen: set = set()
    out: List[Dict[str, str]] = []
    for it in items:
        t = (it.get("title") or "").strip().lower()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(it)
        if len(out) >= max_n:
            break
    return out


def fetch_finviz_scrape(ticker: str) -> List[Dict[str, str]]:
    """Scrape Finviz quote page news table (BeautifulSoup)."""
    import requests
    from bs4 import BeautifulSoup

    if not ticker or not ticker.strip():
        return []
    url = f"https://finviz.com/quote.ashx?t={ticker.strip().upper()}&ty=c&p=d&b=1"
    headers = {"User-Agent": _USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    news_table = soup.find(id="news-table")
    if not news_table:
        return []

    items: List[Dict[str, str]] = []
    current_date = ""
    for row in news_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_cell = cells[0].get_text(strip=True)
        if len(date_cell) > 8:
            current_date = date_cell
        else:
            current_date = (
                current_date.split(" ")[0] + " " + date_cell if current_date else date_cell
            )

        link_tag = cells[1].find("a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        source_span = cells[1].find("span")
        source = source_span.get_text(strip=True) if source_span else "Finviz"

        items.append({
            "title": title,
            "source": source,
            "url": href,
            "published_at": current_date,
            "summary": "",
        })
    return items[:20]


def _feedparser_entries(url: str, default_source: str) -> List[Dict[str, str]]:
    import feedparser  # noqa: WPS433

    items: List[Dict[str, str]] = []
    try:
        feed = feedparser.parse(url)
    except Exception:
        return items

    for e in getattr(feed, "entries", [])[:25]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or e.get("id") or "").strip()
        pub = (e.get("published") or e.get("updated") or "").strip()
        src = default_source
        so = e.get("source")
        if so:
            if isinstance(so, dict):
                src = (so.get("title") or default_source).strip()
            else:
                src = str(so).strip() or default_source
        if title and link:
            items.append({
                "title": title,
                "source": src,
                "url": link,
                "published_at": pub,
                "summary": (e.get("summary") or "")[:500],
            })
    return items


def fetch_google_news_rss(ticker: str) -> List[Dict[str, str]]:
    """Google News RSS for ``{ticker} stock``."""
    if not ticker or not ticker.strip():
        return []
    q = quote_plus(f"{ticker.strip().upper()} stock")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    return _feedparser_entries(url, "Google News")


def fetch_yahoo_finance_rss(ticker: str) -> List[Dict[str, str]]:
    """Yahoo Finance headline RSS for *ticker*."""
    if not ticker or not ticker.strip():
        return []
    sym = ticker.strip().upper()
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}"
        "&region=US&lang=en-US"
    )
    return _feedparser_entries(url, "Yahoo Finance")


def merge_news_for_router(ticker: str, max_articles: int = 40) -> List[Dict[str, str]]:
    """Finviz (scrape) + Google RSS + Yahoo RSS, title-deduped, Finviz first."""
    t = ticker.strip().upper()
    combined: List[Dict[str, str]] = []
    combined.extend(fetch_finviz_scrape(t))
    combined.extend(fetch_google_news_rss(t))
    combined.extend(fetch_yahoo_finance_rss(t))
    return _dedup_merge(combined, max_articles)


# Legacy names (backward compatibility if imported elsewhere)
def aggregate_news(
    ticker: str,
    company_name: str = "",
    max_articles: int = 30,
) -> List[Dict[str, Any]]:
    """Deprecated path: use :func:`merge_news_for_router`. *company_name* ignored."""
    _ = company_name
    return merge_news_for_router(ticker, max_articles=max_articles)
