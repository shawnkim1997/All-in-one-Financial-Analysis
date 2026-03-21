"""
Unified repository — routes operations to PostgreSQL or SQLite
based on DATABASE_URL environment variable.

Usage:
    from server.db.unified_repo import repo
    positions = await repo.get_all_positions()
"""
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def _use_postgres() -> bool:
    """Check if PostgreSQL should be used."""
    return bool(os.getenv("DATABASE_URL", ""))


class UnifiedRepo:
    """Routes database operations to the appropriate backend."""

    async def get_all_positions(self) -> list[dict]:
        if _use_postgres():
            from server.db.pg_portfolio_repo import pg_get_all_positions
            return await pg_get_all_positions()
        from server.db.portfolio_repo import get_all_positions
        return await get_all_positions()

    async def add_position(self, **kwargs) -> Optional[dict]:
        if _use_postgres():
            from server.db.pg_portfolio_repo import pg_add_position
            return await pg_add_position(**kwargs)
        from server.db.portfolio_repo import add_position
        return await add_position(**kwargs)

    async def update_position(self, position_id: int, **kwargs) -> Optional[dict]:
        if _use_postgres():
            from server.db.pg_portfolio_repo import pg_update_position
            return await pg_update_position(position_id, **kwargs)
        from server.db.portfolio_repo import update_position
        return await update_position(position_id, **kwargs)

    async def delete_position(self, position_id: int) -> bool:
        if _use_postgres():
            from server.db.pg_portfolio_repo import pg_delete_position
            return await pg_delete_position(position_id)
        from server.db.portfolio_repo import delete_position
        return await delete_position(position_id)

    async def bulk_add_positions(self, positions: list[dict]) -> list[dict]:
        if _use_postgres():
            from server.db.pg_portfolio_repo import pg_bulk_add_positions
            return await pg_bulk_add_positions(positions)
        from server.db.portfolio_repo import bulk_add_positions
        return await bulk_add_positions(positions)

    async def cache_get(self, key: str) -> Optional[Any]:
        if _use_postgres():
            from server.db.pg_cache_repo import pg_cache_get
            return await pg_cache_get(key)
        from server.db.cache import cache_manager
        return await cache_manager.get(key)

    async def cache_set(self, key: str, value: Any, ttl: int = 86400) -> None:
        if _use_postgres():
            from server.db.pg_cache_repo import pg_cache_set
            return await pg_cache_set(key, value, ttl)
        from server.db.cache import cache_manager
        await cache_manager.set(key, value, ttl)

    async def init_db(self) -> None:
        """Initialize the appropriate database."""
        if _use_postgres():
            from server.db.pg_database import init_pg_tables
            await init_pg_tables()
            logger.info("Using PostgreSQL backend.")
        else:
            from server.db.database import init_db
            await init_db()
            logger.info("Using SQLite backend.")

    async def close_db(self) -> None:
        """Close database connections."""
        if _use_postgres():
            from server.db.pg_database import close_pg_pool
            await close_pg_pool()
        else:
            from server.db.database import close_db
            await close_db()


# Singleton
repo = UnifiedRepo()
