"""News router -- Finviz scrape + Google News RSS + Yahoo Finance RSS."""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from server.models.schemas import NewsItem
from server.services.news_aggregator import merge_news_for_router

router = APIRouter()


@router.get(
    "/{ticker}",
    response_model=List[NewsItem],
    summary="Aggregated news (Finviz + Google + Yahoo)",
)
async def get_news(ticker: str):
    """Return recent articles: Finviz table, Google News RSS, Yahoo headline RSS."""
    try:
        merged = merge_news_for_router(ticker.upper(), max_articles=40)
        return [NewsItem(**item) for item in merged]
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
    """Fetch merged news and optionally summarize with Gemini."""
    try:
        all_items = merge_news_for_router(ticker.upper(), max_articles=30)
        headlines: List[str] = []
        for item in all_items:
            title = (item.get("title") or "").strip()
            if title:
                headlines.append(title)

        headlines = headlines[:20]
        all_items = all_items[:20]

        if not api_key or not api_key.strip():
            return {
                "ticker": ticker.upper(),
                "summary": None,
                "headlines": headlines,
                "items": all_items,
            }

        from server.services.gemini_service import get_gemini_model, _generate_with_retry

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
