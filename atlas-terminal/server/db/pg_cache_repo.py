"""
PostgreSQL cache repository — persistent cache with TTL.
"""
import json
from typing import Optional, Any
from datetime import datetime, timezone, timedelta
from server.db.pg_database import get_pg_pool


async def pg_cache_get(key: str) -> Optional[Any]:
    """Get a cached value. Returns None if expired or not found."""
    pool = await get_pg_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT value FROM cache WHERE key = $1 AND expires_at > NOW()",
            key,
        )
        if row and row["value"] is not None:
            return row["value"]  # JSONB auto-deserializes
        return None


async def pg_cache_set(key: str, value: Any, ttl_seconds: int = 86400) -> None:
    """Set a cache value with TTL."""
    pool = await get_pg_pool()
    if not pool:
        return
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO cache (key, value, expires_at)
               VALUES ($1, $2::jsonb, $3)
               ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, expires_at = $3""",
            key, json.dumps(value), expires,
        )


async def pg_cache_delete(key: str) -> None:
    """Delete a specific cache entry."""
    pool = await get_pg_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cache WHERE key = $1", key)


async def pg_cache_cleanup() -> int:
    """Remove expired cache entries. Returns count of deleted rows."""
    pool = await get_pg_pool()
    if not pool:
        return 0
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM cache WHERE expires_at < NOW()"
        )
        # Parse "DELETE N" result
        try:
            return int(result.split()[-1])
        except (IndexError, ValueError):
            return 0
