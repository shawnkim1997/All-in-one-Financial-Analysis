"""Research deep-dive dashboard API."""

from __future__ import annotations

from fastapi import APIRouter

from server.services.research_dashboard import build_research_dashboard

router = APIRouter()


@router.get("/dashboard/{ticker}", summary="F-Score history, DuPont tree, Sankey, waterfall, anomalies")
async def research_dashboard(ticker: str):
    """Quant-only payload for Research page widgets."""
    return build_research_dashboard(ticker).model_dump()
