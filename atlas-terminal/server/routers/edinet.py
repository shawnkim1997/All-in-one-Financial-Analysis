"""EDINET Japan — optional annual report (有価証券報告書) + link fallbacks."""

from fastapi import APIRouter, HTTPException, Query

from server.models.schemas import EdgarSectionsResponse
from server.services.edinet_filing_service import (
    edinet_is_configured,
    get_edinet_links,
    get_edinet_sections,
)

router = APIRouter()


@router.get("/links/{ticker}", summary="EDINET portal links (no API key required)")
async def edinet_links(ticker: str):
    return get_edinet_links(ticker)


@router.get(
    "/sections/{ticker}",
    response_model=EdgarSectionsResponse,
    summary="Japanese 有価証券報告書 sections (EDINET API v2)",
)
async def edinet_sections(
    ticker: str,
    include_html: bool = Query(
        False,
        description="Include HTML fragment for in-app viewer",
    ),
):
    try:
        sections, status, html_frag, meta = get_edinet_sections(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"EDINET failed: {exc}") from exc

    links = meta.get("links") if isinstance(meta.get("links"), dict) else None
    configured = bool(meta.get("configured", edinet_is_configured()))
    message = None
    if not configured:
        message = "Set EDINET_SUBSCRIPTION_KEY for in-app download; links are provided below."

    html_payload = html_frag if include_html else ""
    return EdgarSectionsResponse(
        source="edinet",
        configured=configured,
        message=message,
        links=links,
        status=status,
        item1a=sections.get("item1a", ""),
        item3=sections.get("item3", ""),
        item7=sections.get("item7", ""),
        item8=sections.get("item8", ""),
        item9a=sections.get("item9a", ""),
        html=html_payload,
    )
