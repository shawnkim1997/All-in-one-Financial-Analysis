"""Search router for ticker autocomplete."""

from fastapi import APIRouter, Query

from server.services.korean_market import search_korean_tickers

router = APIRouter()


@router.get("/tickers", summary="Ticker autocomplete with full KOSPI/KOSDAQ coverage")
async def ticker_search(
    q: str = Query(..., min_length=1, description="Ticker, company name, or Korean company name"),
    limit: int = Query(8, ge=1, le=20),
):
    suggestions = await search_korean_tickers(q, limit=limit)
    return {
        "query": q,
        "count": len(suggestions),
        "suggestions": suggestions,
    }
