"""Daily FT news endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query

from server.models.schemas import FTHeadline
from server.services.ft_epaper_service import fetch_headlines, translate_headlines

router = APIRouter()

EPAPER_LINKS = {
    "international": "https://www.ft.com/todaysnewspaper/international",
    "uk": "https://www.ft.com/todaysnewspaper/uk",
}


@router.get("/today-link", summary="FT ePaper link for opening in a new tab")
async def ft_today_link(edition: str = Query("international", pattern="^(international|uk)$")) -> dict[str, str]:
    return {"edition": edition, "url": EPAPER_LINKS[edition]}


@router.get("/{target_date}", response_model=list[FTHeadline], summary="FT daily headlines with Korean translation")
async def daily_news_by_date(
    target_date: str,
    x_gemini_api_key: str | None = Header(default=None),
) -> list[FTHeadline]:
    try:
        requested = date.fromisoformat(target_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD.") from exc

    today = date.today()
    if requested > today:
        raise HTTPException(status_code=400, detail="Future dates are not available yet.")
    if (today - requested).days > 7:
        raise HTTPException(
            status_code=400,
            detail="FT RSS currently covers the most recent 7 days. Open the FT archive in a new tab for older dates.",
        )

    items = await fetch_headlines(requested)
    api_key = (x_gemini_api_key or "").strip() or None
    translated = await translate_headlines(items, api_key=api_key)
    return [FTHeadline(**item) for item in translated]
