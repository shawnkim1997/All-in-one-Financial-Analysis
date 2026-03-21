"""User settings persistence backed by SQLite.

Provides a simple key-value store for application settings such as API keys
and user preferences, using the ``settings`` table.
"""

from typing import Dict, Optional

import aiosqlite

from server.db.database import get_db


async def get_setting(key: str) -> Optional[str]:
    """Retrieve a single setting by key.

    Args:
        key: The setting key to look up.

    Returns:
        The setting value, or ``None`` if the key does not exist.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute(
        "SELECT value FROM settings WHERE key = ?", (key,)
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    """Create or update a setting.

    Uses ``INSERT OR REPLACE`` so the call is idempotent.

    Args:
        key: The setting key.
        value: The setting value.
    """
    db: aiosqlite.Connection = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    await db.commit()


async def get_all_settings() -> Dict[str, str]:
    """Return every setting as a ``{key: value}`` dict.

    Returns:
        A dict mapping all stored keys to their values.
    """
    db: aiosqlite.Connection = await get_db()
    cursor = await db.execute("SELECT key, value FROM settings ORDER BY key")
    rows = await cursor.fetchall()
    return {row[0]: row[1] for row in rows}


async def delete_setting(key: str) -> None:
    """Remove a setting by key (no-op if the key does not exist).

    Args:
        key: The setting key to delete.
    """
    db: aiosqlite.Connection = await get_db()
    await db.execute("DELETE FROM settings WHERE key = ?", (key,))
    await db.commit()
