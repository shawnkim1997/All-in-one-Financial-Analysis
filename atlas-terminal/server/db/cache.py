"""Two-tier caching system for ATLAS Terminal.

Tier 1 – ``MemoryCache``: fast in-process dict with per-key TTL.
Tier 2 – ``DBCache``: durable SQLite-backed cache with per-key TTL.
``CacheManager`` orchestrates both tiers (memory-first, DB-second).
"""

import json
import time
from typing import Any, Dict, Optional

import aiosqlite

from server.db.database import get_db

# ---------------------------------------------------------------------------
# Tier 1: In-memory cache
# ---------------------------------------------------------------------------

_DEFAULT_MEMORY_TTL: int = 300  # 5 minutes


class MemoryCache:
    """Thread-*unsafe* in-memory cache backed by a plain dict.

    Each entry stores ``(value, expiry_timestamp)``.  Expired entries are
    lazily evicted on ``get()``.
    """

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for *key*, or ``None`` if missing/expired.

        Args:
            key: Cache key.

        Returns:
            The stored value, or ``None``.
        """
        entry = self._store.get(key)
        if entry is None:
            return None

        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int = _DEFAULT_MEMORY_TTL) -> None:
        """Store *value* under *key* with the given TTL in seconds.

        Args:
            key: Cache key.
            value: Arbitrary Python object to cache.
            ttl: Time-to-live in seconds (default 300).
        """
        self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        """Remove *key* from the cache (no-op if absent).

        Args:
            key: Cache key.
        """
        self._store.pop(key, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._store.clear()


# ---------------------------------------------------------------------------
# Tier 2: SQLite-backed cache
# ---------------------------------------------------------------------------

_DEFAULT_DB_TTL: int = 86400  # 1 day


class DBCache:
    """Durable cache that persists entries in the ``cache`` SQLite table.

    Values are stored as JSON-encoded text so that structured data survives
    a round-trip.
    """

    async def get(self, key: str) -> Optional[str]:
        """Return the cached value for *key*, or ``None`` if missing/expired.

        Args:
            key: Cache key.

        Returns:
            The stored value string, or ``None``.
        """
        db: aiosqlite.Connection = await get_db()
        cursor = await db.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?",
            (key,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        value: str = row[0]
        expires_at: float = row[1]

        if time.time() > expires_at:
            await db.execute("DELETE FROM cache WHERE key = ?", (key,))
            await db.commit()
            return None

        return value

    async def set(self, key: str, value: str, ttl: int = _DEFAULT_DB_TTL) -> None:
        """Store *value* under *key* with the given TTL in seconds.

        Uses ``INSERT OR REPLACE`` so existing entries are overwritten.

        Args:
            key: Cache key.
            value: String value to persist.
            ttl: Time-to-live in seconds (default 86400).
        """
        db: aiosqlite.Connection = await get_db()
        expires_at = time.time() + ttl
        await db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, value, expires_at),
        )
        await db.commit()

    async def cleanup(self) -> None:
        """Delete all expired entries from the cache table."""
        db: aiosqlite.Connection = await get_db()
        await db.execute(
            "DELETE FROM cache WHERE expires_at < ?",
            (time.time(),),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class CacheManager:
    """Two-tier cache that checks memory first, then SQLite.

    Usage::

        value = await cache_manager.get("key")
        await cache_manager.set("key", payload, memory_ttl=60, db_ttl=3600)
    """

    def __init__(self) -> None:
        self.memory = MemoryCache()
        self.db = DBCache()

    async def get(self, key: str) -> Optional[Any]:
        """Look up *key* in memory, then in the DB cache.

        If the value is found only in the DB tier it is promoted back into
        memory with the default memory TTL.

        Args:
            key: Cache key.

        Returns:
            The cached value (deserialized from JSON when coming from DB),
            or ``None``.
        """
        # Tier 1
        mem_value = self.memory.get(key)
        if mem_value is not None:
            return mem_value

        # Tier 2
        db_value = await self.db.get(key)
        if db_value is not None:
            try:
                deserialized = json.loads(db_value)
            except (json.JSONDecodeError, TypeError):
                deserialized = db_value

            # Promote to memory for faster subsequent access
            self.memory.set(key, deserialized)
            return deserialized

        return None

    async def set(
        self,
        key: str,
        value: Any,
        memory_ttl: int = _DEFAULT_MEMORY_TTL,
        db_ttl: int = _DEFAULT_DB_TTL,
    ) -> None:
        """Write *value* to both cache tiers.

        The value is JSON-serialized before writing to the DB tier.

        Args:
            key: Cache key.
            value: Arbitrary Python object to cache.
            memory_ttl: TTL for the in-memory tier (default 300s).
            db_ttl: TTL for the SQLite tier (default 86400s).
        """
        self.memory.set(key, value, ttl=memory_ttl)

        serialized = json.dumps(value, default=str)
        await self.db.set(key, serialized, ttl=db_ttl)


# Module-level singleton
cache_manager: CacheManager = CacheManager()
