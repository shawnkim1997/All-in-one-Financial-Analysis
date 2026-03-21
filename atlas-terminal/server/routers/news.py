"""News router -- aggregated financial news from Finviz and Google News RSS."""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from server.models.schemas import NewsItem

router = APIRouter()


def _fetch_finviz_news(ticker: str) -> List[dict]:
    """Scrape recent headlines from Finviz news table for *ticker*."""
    import requests
    from bs4 import BeautifulSoup

    url = f"https://finviz.com/quote.ashx?t={ticker.upper()}&ty=c&p=d&b=1"
    headers = {"User-Agent": "ATLAS-Terminal/1.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    news_table = soup.find(id="news-table")
    if not news_table:
        return []

    items: List[dict] = []
    current_date = ""
    for row in news_table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        date_cell = cells[0].get_text(strip=True)
        if len(date_cell) > 8:
            # Contains date + time, e.g. "Mar-18-26 08:30AM"
            current_date = date_cell
        else:
            # Time only -- reuse last date
            current_date = current_date.split(" ")[0] + " " + date_cell if current_date else date_cell

        link_tag = cells[1].find("a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href", "")
        source_span = cells[1].find("span")
        source = source_span.get_text(strip=True) if source_span else ""

        items.append({
            "title": title,
            "source": source,
            "url": href,
            "published_at": current_date,
            "summary": "",
        })
    return items[:20]


def _fetch_google_news_rss(ticker: str) -> List[dict]:
    """Fetch recent headlines from Google News RSS for *ticker*."""
    import requests
    from xml.etree import ElementTree

    url = f"https://news.google.com/rss/search?q={ticker.upper()}+stock&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception:
        return []

    items: List[dict] = []
    try:
        root = ElementTree.fromstring(resp.content)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text.strip() if source_el is not None and source_el.text else ""
            items.append({
                "title": title,
                "source": source,
                "url": link,
                "published_at": pub_date,
                "summary": "",
            })
    except Exception:
        pass
    return items[:20]


@router.get(
    "/{ticker}",
    response_model=List[NewsItem],
    summary="Aggregated news (Finviz + Google News)",
)
async def get_news(ticker: str):
    """Return up to 40 recent news articles for *ticker*, merged from
    Finviz and Google News RSS feeds.  Duplicates are removed by title.
    """
    try:
        finviz = _fetch_finviz_news(ticker.upper())
        google = _fetch_google_news_rss(ticker.upper())

        seen_titles: set = set()
        merged: List[dict] = []
        for item in finviz + google:
            t = item.get("title", "").strip().lower()
            if t and t not in seen_titles:
                seen_titles.add(t)
                merged.append(item)

        return [NewsItem(**item) for item in merged[:40]]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"News fetch failed: {exc}") from exc


@router.get(
    "/{ticker}/ai-summary",
    summary="AI-summarized news (optional)",
)
async def ai_news_summary(
    ticker: str,
    api_key: str = Query("", description="Google Gemini API key (optional)"),
):
    """Fetch news and optionally generate an AI summary of the top headlines.

    If *api_key* is provided, Gemini produces a short executive summary.
    Otherwise, the raw headlines are returned.
    """
    try:
        finviz = _fetch_finviz_news(ticker.upper())
        google = _fetch_google_news_rss(ticker.upper())

        seen_titles: set = set()
        headlines: List[str] = []
        all_items: List[dict] = []
        for item in finviz + google:
            t = item.get("title", "").strip()
            tl = t.lower()
            if tl and tl not in seen_titles:
                seen_titles.add(tl)
                headlines.append(t)
                all_items.append(item)

        headlines = headlines[:20]
        all_items = all_items[:20]

        if not api_key or not api_key.strip():
            return {
                "ticker": ticker.upper(),
                "summary": None,
                "headlines": headlines,
                "items": all_items,
            }

        # AI summary via Gemini
        from app import get_gemini_model, _generate_with_retry  # type: ignore[import-untyped]

        model = get_gemini_model(api_key)
        headline_text = "\n".join(f"- {h}" for h in headlines)
        prompt = f"""You are a financial news analyst. Below are the latest headlines for {ticker.upper()}.
Provide a concise 3-5 sentence executive summary of the overall sentiment and key themes.

Headlines:
{headline_text}"""
        response = _generate_with_retry(model, prompt, {"temperature": 0.2, "max_output_tokens": 512})
        summary = (response.text or "").strip() if response else ""

        return {
            "ticker": ticker.upper(),
            "summary": summary,
            "headlines": headlines,
            "items": all_items,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI news summary failed: {exc}") from exc
