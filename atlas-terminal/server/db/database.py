"""SQLite database manager for ATLAS Terminal.

Provides async database access via aiosqlite with a singleton connection
pattern. Replaces the previous Supabase dependency with local-first SQLite.
"""

import os
from pathlib import Path
from typing import Optional

import aiosqlite

# Resolve the database file path relative to this module
_DB_DIR: Path = Path(__file__).resolve().parent.parent / "data"
_DB_PATH: str = str(_DB_DIR / "atlas.db")

# Singleton connection holder
_connection: Optional[aiosqlite.Connection] = None


async def get_db() -> aiosqlite.Connection:
    """Return the singleton async SQLite connection.

    Creates the connection (and the data/ directory) on first call.
    Enables WAL mode and foreign keys for better concurrency and integrity.

    Returns:
        An open ``aiosqlite.Connection`` ready for queries.
    """
    global _connection

    if _connection is not None:
        return _connection

    _DB_DIR.mkdir(parents=True, exist_ok=True)

    _connection = await aiosqlite.connect(_DB_PATH)
    _connection.row_factory = aiosqlite.Row
    await _connection.execute("PRAGMA journal_mode=WAL")
    await _connection.execute("PRAGMA foreign_keys=ON")

    return _connection


async def init_db() -> None:
    """Create all application tables if they do not already exist.

    Should be called once during application startup (e.g. in a FastAPI
    ``lifespan`` handler).
    """
    db = await get_db()

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS portfolio_positions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT    NOT NULL,
            name        TEXT    NOT NULL,
            shares      REAL    NOT NULL,
            avg_cost    REAL    NOT NULL,
            currency    TEXT    NOT NULL DEFAULT 'USD',
            broker      TEXT,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS watchlist (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker   TEXT    NOT NULL UNIQUE,
            added_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboards (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            layout_json TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            expires_at REAL NOT NULL
        )
        """
    )

    await db.commit()


async def close_db() -> None:
    """Close the singleton database connection.

    Safe to call even if the connection was never opened.
    """
    global _connection

    if _connection is not None:
        await _connection.close()
        _connection = None
