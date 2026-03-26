"""SEC EDGAR router -- 10-K section download, cache lookup, and comparison."""

from fastapi import APIRouter, HTTPException, Query

from server.models.schemas import (
    EdgarSectionsResponse,
    Item7Response,
    CompareResponse,
)

router = APIRouter()


@router.get(
    "/sections/{ticker}",
    response_model=EdgarSectionsResponse,
    summary="Get 10-K sections (cached or download)",
)
async def get_sections(
    ticker: str,
    email: str = Query(..., description="SEC EDGAR fair-access email"),
    include_html: bool = Query(
        False,
        description="Include original HTML (with section anchors) for iframe viewing",
    ),
):
    """Return cleaned Item 1A, 3, 7, 8, 9A texts for *ticker*.

    If the sections are already cached locally the download is skipped.
    When *include_html* is true, the response includes ``html`` (wrapped 10-K
    slice with ``id=atlas-item7`` etc. for in-page scrolling).
    """
    try:
        from server.services.sec_parser import (
            download_and_extract_all_items,
            get_10k_sections,
            load_10k_html_slice,
        )

        sections, status = get_10k_sections(ticker.upper(), email)
        html_payload = ""
        if include_html:
            html_payload = load_10k_html_slice(ticker.upper()) or ""
            if not html_payload:
                sections = download_and_extract_all_items(ticker.upper(), email)
                status = "downloaded"
                html_payload = load_10k_html_slice(ticker.upper()) or ""
        return EdgarSectionsResponse(
            status=status,
            item1a=sections.get("item1a", ""),
            item3=sections.get("item3", ""),
            item7=sections.get("item7", ""),
            item8=sections.get("item8", ""),
            item9a=sections.get("item9a", ""),
            html=html_payload,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"EDGAR download failed: {exc}") from exc


@router.get(
    "/item7/{ticker}",
    response_model=Item7Response,
    summary="Get Item 7 (MD&A) text",
)
async def get_item7(
    ticker: str,
    email: str = Query(..., description="SEC EDGAR fair-access email"),
):
    """Return only the Item 7 Management Discussion & Analysis text."""
    try:
        from server.services.sec_parser import download_and_extract_item7_and_1a

        _, _item1a, item7 = download_and_extract_item7_and_1a(ticker.upper(), email)
        return Item7Response(item7=item7)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Item 7 extraction failed: {exc}") from exc


@router.get(
    "/compare/{ticker}",
    response_model=CompareResponse,
    summary="Latest vs 3-year-ago Item 7 comparison",
)
async def compare_item7(
    ticker: str,
    email: str = Query(..., description="SEC EDGAR fair-access email"),
):
    """Download up to 5 10-Ks and return the latest and 3-year-ago Item 7 for
    comparative analysis.  Also returns the latest Item 1A.
    """
    try:
        from server.services.sec_parser import download_item7_latest_and_3y_ago

        item1a, item7_latest, item7_3y_ago, has_comparison = (
            download_item7_latest_and_3y_ago(ticker.upper(), email)
        )
        return CompareResponse(
            item1a_latest=item1a or "",
            item7_latest=item7_latest or "",
            item7_3y_ago=item7_3y_ago,
            has_comparison=has_comparison,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {exc}") from exc
