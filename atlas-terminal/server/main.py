"""
ATLAS Terminal — FastAPI Backend
Unified entry point with PostgreSQL + SQLite support.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from server.routers import edgar, analysis, valuation, market_data, news, crypto, fx, portfolio, technical, financials, estimates, earnings, insider  # noqa: E402

app.include_router(edgar.router, prefix="/api/edgar", tags=["SEC EDGAR"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["AI Analysis"])
app.include_router(valuation.router, prefix="/api/valuation", tags=["Valuation"])
app.include_router(market_data.router, prefix="/api/market", tags=["Market Data"])
app.include_router(financials.router, prefix="/api/financials", tags=["Financials"])
app.include_router(estimates.router, prefix="/api/estimates", tags=["Estimates"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(crypto.router, prefix="/api/crypto", tags=["Crypto"])
app.include_router(fx.router, prefix="/api/fx", tags=["FX"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(technical.router, prefix="/api/technical", tags=["Technical"])
app.include_router(earnings.router, prefix="/api/earnings", tags=["Earnings"])
app.include_router(insider.router, prefix="/api/insider", tags=["Insider Trading"])


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
