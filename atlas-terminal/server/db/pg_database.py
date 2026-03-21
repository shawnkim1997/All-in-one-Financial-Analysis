"""
PostgreSQL async connection manager for ATLAS Terminal.
Uses asyncpg for high-performance async PostgreSQL operations.
Configurable via DATABASE_URL environment variable.
"""
import os
import json
import logging
from typing import Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Try to import asyncpg
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    asyncpg = None

_pool: Optional[Any] = None


async def get_pg_pool() -> Optional[Any]:
    """Get or create the PostgreSQL connection pool."""
    global _pool
    if not HAS_ASYNCPG:
        logger.warning("asyncpg not installed. Run: pip install asyncpg")
        return None
    if _pool is not None:
        return _pool

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        logger.info("No DATABASE_URL set, PostgreSQL disabled.")
        return None

    try:
        _pool = await asyncpg.create_pool(
            database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("PostgreSQL connection pool created.")
        return _pool
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL pool: {e}")
        return None


async def init_pg_tables() -> None:
    """Create tables if they don't exist in PostgreSQL."""
    pool = await get_pg_pool()
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_positions (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(20) NOT NULL,
                name VARCHAR(200),
                shares DOUBLE PRECISION NOT NULL DEFAULT 0,
                avg_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
                currency VARCHAR(10) DEFAULT 'USD',
                broker VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(20) NOT NULL UNIQUE,
                added_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                layout_json JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key VARCHAR(500) PRIMARY KEY,
                value JSONB,
                expires_at TIMESTAMPTZ
            );
        """)
        # Index for cache expiry cleanup
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache(expires_at);
        """)
        logger.info("PostgreSQL tables initialized.")


async def close_pg_pool() -> None:
    """Close the PostgreSQL connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed.")
