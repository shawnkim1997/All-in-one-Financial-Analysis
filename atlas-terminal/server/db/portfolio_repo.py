"""Portfolio CRUD operations backed by SQLite.

All functions operate on the ``portfolio_positions`` table and return plain
dicts so they can be serialized directly by FastAPI.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from server.db.database import get_db


def _row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    """Convert an ``aiosqlite.Row`` to a plain dict.

    Args:
        row: A database row returned with ``row_factory = aiosqlite.Row``.

    Returns:
        A dict keyed by column name.
    """
    return dict(row)


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        e.g. ``'2026-03-20T12:34:56'``
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


async def get_all_positions() -> List[Dict[str, Any]]:
    """Return every row in ``portfolio_positions`` ordered by id.

    Returns:
        A list of position dicts.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "SELECT * FROM portfolio_positions ORDER BY id"
    )
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def add_position(
    ticker: str,
    name: str,
    shares: float,
    avg_cost: float,
    currency: str = "USD",
    broker: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a new portfolio position.

    Args:
        ticker: Stock ticker symbol (e.g. ``'AAPL'``).
        name: Human-readable security name.
        shares: Number of shares held.
        avg_cost: Average cost basis per share.
        currency: ISO currency code (default ``'USD'``).
        broker: Optional broker name.

    Returns:
        The newly created position as a dict (including generated id).
    """
    db: aiosqlite.Connection = await get_db()
    now = _now_iso()

    cursor = await db.execute(
        """
        INSERT INTO portfolio_positions
            (ticker, name, shares, avg_cost, currency, broker, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticker, name, shares, avg_cost, currency, broker, now, now),
    )
    await db.commit()

    new_id = cursor.lastrowid
    result_cursor = await db.execute(
        "SELECT * FROM portfolio_positions WHERE id = ?", (new_id,)
    )
    row = await result_cursor.fetchone()
    return _row_to_dict(row)  # type: ignore[arg-type]


async def update_position(position_id: int, **kwargs: Any) -> Dict[str, Any]:
    """Update an existing portfolio position.

    Only the supplied keyword arguments are modified; all others remain
    unchanged.  ``updated_at`` is set automatically.

    Args:
        position_id: The primary-key id of the position to update.
        **kwargs: Column names and their new values.

    Returns:
        The updated position dict.

    Raises:
        ValueError: If *position_id* does not exist or no fields are given.
    """
    if not kwargs:
        raise ValueError("No fields provided for update")

    allowed_fields = {"ticker", "name", "shares", "avg_cost", "currency", "broker"}
    fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not fields:
        raise ValueError(
            f"No valid fields to update. Allowed: {allowed_fields}"
        )

    fields["updated_at"] = _now_iso()

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [position_id]

    db: aiosqlite.Connection = await get_db()
    await db.execute(
        f"UPDATE portfolio_positions SET {set_clause} WHERE id = ?",  # noqa: S608
        values,
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM portfolio_positions WHERE id = ?", (position_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError(f"Position with id={position_id} not found")
    return _row_to_dict(row)


async def delete_position(position_id: int) -> bool:
    """Delete a portfolio position by id.

    Args:
        position_id: The primary-key id to delete.

    Returns:
        ``True`` if a row was deleted, ``False`` if no matching row existed.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "DELETE FROM portfolio_positions WHERE id = ?", (position_id,)
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_position_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Look up a position by ticker symbol.

    If multiple positions share the same ticker (e.g. different brokers),
    the first one (lowest id) is returned.

    Args:
        ticker: The ticker to search for (case-sensitive).

    Returns:
        A position dict, or ``None`` if not found.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "SELECT * FROM portfolio_positions WHERE ticker = ? ORDER BY id LIMIT 1",
        (ticker,),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def bulk_add_positions(
    positions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Insert multiple positions in a single transaction.

    Each dict in *positions* must contain at least ``ticker``, ``name``,
    ``shares``, and ``avg_cost``.  Optional keys: ``currency``, ``broker``.

    Args:
        positions: A list of position dicts.

    Returns:
        A list of the newly created position dicts.
    """
    db: aiosqlite.Connection = await get_db()
    now = _now_iso()
    created: List[Dict[str, Any]] = []

    for pos in positions:
        cursor = await db.execute(
            """
            INSERT INTO portfolio_positions
                (ticker, name, shares, avg_cost, currency, broker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pos["ticker"],
                pos["name"],
                pos["shares"],
                pos["avg_cost"],
                pos.get("currency", "USD"),
                pos.get("broker"),
                now,
                now,
            ),
        )
        new_id = cursor.lastrowid
        result_cursor = await db.execute(
            "SELECT * FROM portfolio_positions WHERE id = ?", (new_id,)
        )
        row = await result_cursor.fetchone()
        created.append(_row_to_dict(row))  # type: ignore[arg-type]

    await db.commit()
    return created
