"""Portfolio router -- position management, OCR screenshot upload, summary."""

import json
import os
import uuid
from pathlib import Path
from typing import List

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from pydantic import BaseModel, Field

from server.models.schemas import (
    PortfolioPosition,
    PortfolioPositionCreate,
    PortfolioSummary,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple file-based persistence (production would use Supabase / Postgres)
_PORTFOLIO_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "portfolio.json"


class PositionUpdateRequest(BaseModel):
    quantity: float = Field(..., gt=0)
    avg_price: float = Field(..., ge=0)
    exchange: str = ""


class OcrRecalculateRequest(BaseModel):
    account_currency: str = "USD"
    position: dict
    selected_exchange: str = ""


def _load_positions() -> List[dict]:
    """Load positions from the JSON store."""
    if not _PORTFOLIO_FILE.exists():
        return []
    try:
        with open(_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.exception("portfolio endpoint failed")
        return []


def _save_positions(positions: List[dict]) -> None:
    """Persist positions to the JSON store."""
    _PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=2)


def _get_current_price(ticker: str) -> float | None:
    """Fetch the latest market price for *ticker*."""
    try:
        import yfinance as yf

        t = yf.Ticker(ticker.upper())
        fast = getattr(t, "fast_info", None)
        if fast:
            price = getattr(fast, "last_price", None)
            if price and float(price) > 0:
                return float(price)
        hist = t.history(period="1d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/positions",
    response_model=List[PortfolioPosition],
    summary="List portfolio positions",
)
async def list_positions():
    """Return all portfolio positions (without live pricing)."""
    try:
        positions = _load_positions()
        return [PortfolioPosition(**p) for p in positions]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load positions: {exc}") from exc


@router.post(
    "/positions",
    response_model=PortfolioPosition,
    summary="Add or update a portfolio position",
)
async def add_position(pos: PortfolioPositionCreate):
    """Add a new position. If ticker exists, update quantity/avg/currency."""
    try:
        positions = _load_positions()
        ticker = pos.ticker.upper()
        existing = next((p for p in positions if str(p.get("ticker", "")).upper() == ticker), None)
        if existing is not None:
            existing["company_name"] = pos.company_name or existing.get("company_name", "")
            existing["quantity"] = float(pos.quantity)
            existing["avg_price"] = float(pos.avg_price)
            existing["currency"] = pos.currency or existing.get("currency", "USD")
            existing["exchange"] = pos.exchange or existing.get("exchange", "")
            existing["source"] = pos.source or existing.get("source", "manual")
            saved = existing
        else:
            saved = {
                "id": str(uuid.uuid4()),
                "ticker": ticker,
                "company_name": pos.company_name,
                "quantity": pos.quantity,
                "avg_price": pos.avg_price,
                "currency": pos.currency,
                "exchange": pos.exchange,
                "source": pos.source,
            }
            positions.append(saved)
        _save_positions(positions)
        return PortfolioPosition(**saved)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to add position: {exc}") from exc


@router.delete(
    "/positions/{position_id}",
    summary="Remove a portfolio position",
)
async def remove_position(position_id: str):
    """Delete a position by its unique ID."""
    try:
        positions = _load_positions()
        original_len = len(positions)
        positions = [p for p in positions if p.get("id") != position_id]

        if len(positions) == original_len:
            raise HTTPException(status_code=404, detail=f"Position {position_id} not found.")

        _save_positions(positions)
        return {"deleted": position_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to remove position: {exc}") from exc


@router.put(
    "/positions/{position_id}",
    response_model=PortfolioPosition,
    summary="Update quantity/avg price for a position",
)
async def update_position(position_id: str, body: PositionUpdateRequest):
    """Update an existing position by unique ID."""
    try:
        positions = _load_positions()
        updated = None
        for p in positions:
            if p.get("id") == position_id:
                p["quantity"] = float(body.quantity)
                p["avg_price"] = float(body.avg_price)
                if body.exchange:
                    p["exchange"] = body.exchange
                updated = p
                break
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Position {position_id} not found.")
        _save_positions(positions)
        return PortfolioPosition(**updated)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to update position: {exc}") from exc


@router.post(
    "/ocr",
    summary="OCR screenshot with smart reverse-engineering",
)
async def ocr_screenshot(
    file: UploadFile = File(...),
    x_gemini_api_key: str | None = Header(default=None),
):
    """Screenshot -> OCR extraction -> market-validated reverse-engineered positions."""
    try:
        from server.services.screenshot_ocr import process_portfolio_screenshot

        image_bytes = await file.read()
        api_key = (x_gemini_api_key or "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
        result = await process_portfolio_screenshot(api_key, image_bytes)
        if result.get("error"):
            return {"error": result.get("error"), "positions": [], "count": 0, "warnings": []}
        result["count"] = len(result.get("positions") or [])
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {exc}") from exc


@router.get("/exchange-options/{ticker}", summary="Available exchange options for a ticker")
async def exchange_options(ticker: str):
    from server.services.exchange_resolver import get_exchange_options

    return {"ticker": ticker.upper(), "options": get_exchange_options(ticker)}


@router.post("/ocr/recalculate", summary="Recalculate one OCR row with selected exchange")
async def ocr_recalculate(body: OcrRecalculateRequest):
    from server.services.screenshot_ocr import reverse_engineer_positions

    ticker = str((body.position or {}).get("ticker", "")).upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="position.ticker is required")
    payload = {"account_currency": body.account_currency, "positions": [body.position]}
    overrides = {ticker: body.selected_exchange} if body.selected_exchange else {}
    recalculated = reverse_engineer_positions(payload, overrides)
    if not recalculated:
        raise HTTPException(status_code=400, detail="Failed to recalculate position")
    return {"position": recalculated[0]}


@router.post(
    "/screenshot",
    summary="Upload screenshot for OCR analysis",
)
async def upload_screenshot(file: UploadFile = File(...)):
    """Accept a screenshot image (PNG/JPG) and attempt to extract portfolio
    positions via OCR.  Returns the recognised text and any parsed positions.

    This is a best-effort feature; parsing accuracy depends on the
    screenshot layout.
    """
    try:
        contents = await file.read()

        # Try pytesseract for OCR
        try:
            from PIL import Image
            import pytesseract
            import io

            image = Image.open(io.BytesIO(contents))
            text = pytesseract.image_to_string(image)
        except ImportError:
            text = "(OCR not available -- install pytesseract and Pillow)"
        except Exception as ocr_err:
            text = f"(OCR failed: {ocr_err})"

        return {
            "filename": file.filename,
            "size": len(contents),
            "ocr_text": text,
            "parsed_positions": [],  # Future: parse text into positions
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Screenshot processing failed: {exc}") from exc


@router.get("/risk", summary="Portfolio risk metrics (VaR, Sharpe, MDD)")
async def portfolio_risk():
    """Compute portfolio risk metrics from current positions."""
    try:
        from server.services.risk_metrics import compute_portfolio_risk
        positions = _load_positions()
        if not positions:
            return {"error": "No positions in portfolio"}
        result = compute_portfolio_risk(positions)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Risk metrics failed: {exc}") from exc


@router.get(
    "/summary",
    response_model=PortfolioSummary,
    summary="Portfolio summary with current prices",
)
async def portfolio_summary():
    """Return all positions enriched with current market prices,
    market values, and P&L.
    """
    try:
        positions = _load_positions()
        enriched: List[PortfolioPosition] = []
        total_value = 0.0
        total_cost = 0.0

        for p in positions:
            ticker = p.get("ticker", "")
            quantity = float(p.get("quantity", 0))
            avg_price = float(p.get("avg_price", 0))
            cost = quantity * avg_price
            total_cost += cost

            current_price = _get_current_price(ticker)
            market_value = (quantity * current_price) if current_price else None
            pnl = (market_value - cost) if market_value is not None else None
            pnl_pct = (pnl / cost * 100) if (pnl is not None and cost > 0) else None

            if market_value is not None:
                total_value += market_value

            enriched.append(PortfolioPosition(
                id=p.get("id"),
                ticker=ticker,
                company_name=p.get("company_name", ""),
                quantity=quantity,
                avg_price=avg_price,
                currency=p.get("currency", "USD"),
                exchange=p.get("exchange", ""),
                source=p.get("source", "manual"),
                current_price=current_price,
                market_value=market_value,
                pnl=pnl,
                pnl_pct=round(pnl_pct, 2) if pnl_pct is not None else None,
            ))

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else None

        return PortfolioSummary(
            total_value=round(total_value, 2),
            total_cost=round(total_cost, 2),
            total_pnl=round(total_pnl, 2),
            total_pnl_pct=round(total_pnl_pct, 2) if total_pnl_pct is not None else None,
            positions=enriched,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Portfolio summary failed: {exc}") from exc
