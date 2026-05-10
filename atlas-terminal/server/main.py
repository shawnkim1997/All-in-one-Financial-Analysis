"""
ATLAS Terminal — FastAPI Backend
Unified entry point with PostgreSQL + SQLite support.
"""
import json
import math
import os
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


class _NanSafeEncoder(json.JSONEncoder):
    """Replace NaN/Inf with None so JSON serialization never crashes."""

    def default(self, o: Any) -> Any:
        return super().default(o)

    def encode(self, o: Any) -> str:
        return super().encode(_sanitize(o))


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj


class NanSafeJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            _sanitize(content),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, close on shutdown."""
    from server.db.unified_repo import repo
    await repo.init_db()
    logger.info("ATLAS Terminal backend started.")
    yield
    await repo.close_db()
    logger.info("ATLAS Terminal backend stopped.")


app = FastAPI(
    title="ATLAS Terminal API",
    description="Personal Bloomberg Terminal — Hybrid AI + Quantitative Analysis",
    version="2.0.0",
    lifespan=lifespan,
    default_response_class=NanSafeJSONResponse,
)

# CORS — allow local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Mount routers ---
from server.routers import edgar, analysis, valuation, market_data, news, crypto, fx, portfolio, technical, financials, estimates, earnings, insider, screener, markets, fmp, macro, dart, edinet, research, chat, copilot, credentials, calendar, tax, video_transcript  # noqa: E402

app.include_router(edgar.router, prefix="/api/edgar", tags=["SEC EDGAR"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI Analysis"])
app.include_router(valuation.router, prefix="/api/valuation", tags=["Valuation"])
app.include_router(market_data.router, prefix="/api/market", tags=["Market Data"])
app.include_router(financials.router, prefix="/api/financials", tags=["Financials"])
app.include_router(estimates.router, prefix="/api/estimates", tags=["Estimates"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(crypto.router, prefix="/api/crypto", tags=["Crypto"])
app.include_router(fx.router, prefix="/api/fx", tags=["FX"])
app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(technical.router, prefix="/api/technical", tags=["Technical"])
app.include_router(earnings.router, prefix="/api/earnings", tags=["Earnings"])
app.include_router(insider.router, prefix="/api/insider", tags=["Insider Trading"])
app.include_router(screener.router, prefix="/api/screener", tags=["Screener"])
app.include_router(fmp.router, prefix="/api/fmp", tags=["FMP"])
app.include_router(macro.router, prefix="/api/macro", tags=["Macro"])
app.include_router(dart.router, prefix="/api/dart", tags=["DART"])
app.include_router(edinet.router, prefix="/api/edinet", tags=["EDINET"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(copilot.router, prefix="/api/copilot", tags=["Copilot"])
app.include_router(credentials.router, prefix="/api/credentials", tags=["Credentials"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Calendar"])
app.include_router(video_transcript.router, prefix="/api/video", tags=["Video Transcript"])
app.include_router(tax.router, prefix="/api/tax", tags=["Tax"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_type = "postgresql" if os.getenv("DATABASE_URL") else "sqlite"
    return {"status": "ok", "db": db_type, "version": "2.0.0"}


@app.get("/api/health")
async def api_health_check():
    """Health check endpoint (via /api prefix for Next.js proxy)."""
    db_type = "postgresql" if os.getenv("DATABASE_URL") else "sqlite"
    return {"status": "ok", "db": db_type, "version": "2.0.0"}
