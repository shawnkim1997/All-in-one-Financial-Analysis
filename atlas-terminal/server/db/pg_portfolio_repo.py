"""
PostgreSQL portfolio repository — full CRUD for portfolio positions.
"""
from typing import Optional
from datetime import datetime, timezone
from server.db.pg_database import get_pg_pool


async def pg_get_all_positions() -> list[dict]:
    """Get all portfolio positions from PostgreSQL."""
    pool = await get_pg_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM portfolio_positions ORDER BY updated_at DESC"
        )
        return [dict(r) for r in rows]


async def pg_add_position(
    ticker: str,
    name: str = "",
    shares: float = 0.0,
    avg_cost: float = 0.0,
    currency: str = "USD",
    broker: str = "",
) -> Optional[dict]:
    """Add a new position to PostgreSQL."""
    pool = await get_pg_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO portfolio_positions (ticker, name, shares, avg_cost, currency, broker)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            ticker.upper(), name, shares, avg_cost, currency, broker,
        )
        return dict(row) if row else None


async def pg_update_position(position_id: int, **fields) -> Optional[dict]:
    """Update a position by ID."""
    pool = await get_pg_pool()
    if not pool:
        return None

    allowed = {"ticker", "name", "shares", "avg_cost", "currency", "broker"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None

    updates["updated_at"] = datetime.now(timezone.utc)
    set_clauses = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    values = [position_id] + list(updates.values())

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE portfolio_positions SET {set_clauses} WHERE id = $1 RETURNING *",
            *values,
        )
        return dict(row) if row else None


async def pg_delete_position(position_id: int) -> bool:
    """Delete a position by ID."""
    pool = await get_pg_pool()
    if not pool:
        return False
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM portfolio_positions WHERE id = $1", position_id
        )
        return result == "DELETE 1"


async def pg_get_position_by_ticker(ticker: str) -> Optional[dict]:
    """Get a position by ticker symbol."""
    pool = await get_pg_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM portfolio_positions WHERE ticker = $1", ticker.upper()
        )
        return dict(row) if row else None


async def pg_bulk_add_positions(positions: list[dict]) -> list[dict]:
    """Bulk add positions (from OCR screenshot)."""
    pool = await get_pg_pool()
    if not pool:
        return []
    results = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            for p in positions:
                row = await conn.fetchrow(
                    """INSERT INTO portfolio_positions (ticker, name, shares, avg_cost, currency, broker)
                       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
                    p.get("ticker", "").upper(),
                    p.get("name", ""),
                    float(p.get("shares", 0)),
                    float(p.get("avg_cost", 0)),
                    p.get("currency", "USD"),
                    p.get("broker", ""),
                )
                if row:
                    results.append(dict(row))
    return results
