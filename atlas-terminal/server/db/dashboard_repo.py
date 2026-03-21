"""Dashboard layout persistence backed by SQLite.

All functions operate on the ``dashboards`` table and return plain dicts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from server.db.database import get_db


def _row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    """Convert an ``aiosqlite.Row`` to a plain dict.

    Args:
        row: A database row.

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


async def get_all_dashboards() -> List[Dict[str, Any]]:
    """Return all saved dashboards ordered by id.

    Returns:
        A list of dashboard dicts.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute("SELECT * FROM dashboards ORDER BY id")
    rows = await cursor.fetchall()
    return [_row_to_dict(r) for r in rows]


async def get_dashboard(dashboard_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single dashboard by its primary key.

    Args:
        dashboard_id: The id of the dashboard.

    Returns:
        A dashboard dict, or ``None`` if not found.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "SELECT * FROM dashboards WHERE id = ?", (dashboard_id,)
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def save_dashboard(name: str, layout_json: str) -> Dict[str, Any]:
    """Create a new dashboard.

    Args:
        name: Human-readable dashboard name.
        layout_json: JSON string describing the widget layout.

    Returns:
        The newly created dashboard dict.
    """
    db: aiosqlite.Connection = await get_db()
    now = _now_iso()

    cursor = await db.execute(
        """
        INSERT INTO dashboards (name, layout_json, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, layout_json, now, now),
    )
    await db.commit()

    new_id = cursor.lastrowid
    result_cursor = await db.execute(
        "SELECT * FROM dashboards WHERE id = ?", (new_id,)
    )
    row = await result_cursor.fetchone()
    return _row_to_dict(row)  # type: ignore[arg-type]


async def update_dashboard(
    dashboard_id: int,
    name: Optional[str] = None,
    layout_json: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing dashboard's name and/or layout.

    At least one of *name* or *layout_json* must be provided.
    ``updated_at`` is set automatically.

    Args:
        dashboard_id: The id of the dashboard to update.
        name: New dashboard name (or ``None`` to leave unchanged).
        layout_json: New layout JSON (or ``None`` to leave unchanged).

    Returns:
        The updated dashboard dict.

    Raises:
        ValueError: If the dashboard does not exist or no fields given.
    """
    fields: Dict[str, Any] = {}
    if name is not None:
        fields["name"] = name
    if layout_json is not None:
        fields["layout_json"] = layout_json

    if not fields:
        raise ValueError("At least one of 'name' or 'layout_json' must be provided")

    fields["updated_at"] = _now_iso()

    set_clause = ", ".join(f"{col} = ?" for col in fields)
    values = list(fields.values()) + [dashboard_id]

    db: aiosqlite.Connection = await get_db()
    await db.execute(
        f"UPDATE dashboards SET {set_clause} WHERE id = ?",  # noqa: S608
        values,
    )
    await db.commit()

    cursor = await db.execute(
        "SELECT * FROM dashboards WHERE id = ?", (dashboard_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError(f"Dashboard with id={dashboard_id} not found")
    return _row_to_dict(row)


async def delete_dashboard(dashboard_id: int) -> bool:
    """Delete a dashboard by id.

    Args:
        dashboard_id: The id to delete.

    Returns:
        ``True`` if a row was deleted, ``False`` otherwise.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "DELETE FROM dashboards WHERE id = ?", (dashboard_id,)
    )
    await db.commit()
    return cursor.rowcount > 0
