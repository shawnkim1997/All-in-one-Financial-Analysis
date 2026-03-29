"""DART Korea — company search (optional ``DART_API_KEY``) + annual report sections."""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from server.models.schemas import EdgarSectionsResponse
from server.services.dart_fetcher import dart_is_configured, search_corporations
from server.services.dart_filing_service import (
    dart_filing_is_configured,
    get_dart_sections,
)

router = APIRouter()


@router.get("/search", summary="Search DART corporations by name")
async def dart_search(
    q: str = Query(..., min_length=1, description="Company name (KO/EN)"),
    limit: int = Query(20, ge=1, le=50),
) -> Dict[str, Any]:
    if not dart_is_configured():
        return {
            "configured": False,
            "message": "Set DART_API_KEY in the environment.",
            "results": [],
        }
    rows: List[Dict[str, Any]] = search_corporations(q, limit=limit)
    return {"configured": True, "query": q, "count": len(rows), "results": rows}


@router.get(
    "/sections/{ticker}",
    response_model=EdgarSectionsResponse,
    summary="Korean annual report sections (DART Open API)",
)
async def dart_sections(
    ticker: str,
    include_html: bool = Query(
        False,
        description="Include HTML fragment for in-app viewer",
    ),
):
    """Download latest annual report and map to SEC-like section keys."""
    if not dart_filing_is_configured():
        return EdgarSectionsResponse(
            source="dart",
            configured=False,
            message="Set DART_API_KEY in the environment (Open DART).",
            status="unconfigured",
        )
    try:
        sections, status, html_frag, rcept_no = get_dart_sections(ticker)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DART download failed: {exc}") from exc

    html_payload = html_frag if include_html else ""
    links = {"DART 원문 공시": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"} if rcept_no else None
    return EdgarSectionsResponse(
        source="dart",
        configured=True,
        status=status,
        item1a=sections.get("item1a", ""),
        item3=sections.get("item3", ""),
        item7=sections.get("item7", ""),
        item8=sections.get("item8", ""),
        item9a=sections.get("item9a", ""),
        html=html_payload,
        links=links,
    )
