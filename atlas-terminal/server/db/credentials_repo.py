"""Credential persistence and audit logging."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from server.db.database import get_db


def _use_postgres() -> bool:
    return bool(os.getenv("DATABASE_URL", ""))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row) if row is not None else {}


async def upsert_credential(user_id: str, provider: str, encrypted_blob: bytes) -> None:
    provider_key = provider.lower()
    now = _now_iso()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            raise RuntimeError("PostgreSQL pool is unavailable")
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_credentials (user_id, provider, encrypted_blob, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, provider)
                DO UPDATE SET encrypted_blob = EXCLUDED.encrypted_blob
                """,
                user_id,
                provider_key,
                encrypted_blob,
                now,
            )
        return

    db = await get_db()
    await db.execute(
        """
        INSERT INTO user_credentials (user_id, provider, encrypted_blob, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, provider)
        DO UPDATE SET encrypted_blob = excluded.encrypted_blob
        """,
        (user_id, provider_key, encrypted_blob, now),
    )
    await db.commit()


async def get_credential_blob(user_id: str, provider: str) -> bytes | None:
    provider_key = provider.lower()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT encrypted_blob FROM user_credentials WHERE user_id = $1 AND provider = $2",
                user_id,
                provider_key,
            )
        return bytes(row["encrypted_blob"]) if row else None

    db = await get_db()
    cursor = await db.execute(
        "SELECT encrypted_blob FROM user_credentials WHERE user_id = ? AND provider = ?",
        (user_id, provider_key),
    )
    row = await cursor.fetchone()
    return bytes(row["encrypted_blob"]) if row else None


async def get_credential_status(user_id: str, provider: str) -> dict[str, Any] | None:
    provider_key = provider.lower()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            return None
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, provider, created_at, last_used_at
                FROM user_credentials
                WHERE user_id = $1 AND provider = $2
                """,
                user_id,
                provider_key,
            )
        return dict(row) if row else None

    db = await get_db()
    cursor = await db.execute(
        """
        SELECT user_id, provider, created_at, last_used_at
        FROM user_credentials
        WHERE user_id = ? AND provider = ?
        """,
        (user_id, provider_key),
    )
    row = await cursor.fetchone()
    return _row_to_dict(row) if row else None


async def mark_credential_used(user_id: str, provider: str) -> None:
    provider_key = provider.lower()
    now = _now_iso()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE user_credentials SET last_used_at = $3 WHERE user_id = $1 AND provider = $2",
                user_id,
                provider_key,
                now,
            )
        return

    db = await get_db()
    await db.execute(
        "UPDATE user_credentials SET last_used_at = ? WHERE user_id = ? AND provider = ?",
        (now, user_id, provider_key),
    )
    await db.commit()


async def delete_credential(user_id: str, provider: str) -> bool:
    provider_key = provider.lower()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            return False
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM user_credentials WHERE user_id = $1 AND provider = $2",
                user_id,
                provider_key,
            )
        return result.endswith("1")

    db = await get_db()
    cursor = await db.execute(
        "DELETE FROM user_credentials WHERE user_id = ? AND provider = ?",
        (user_id, provider_key),
    )
    await db.commit()
    return cursor.rowcount > 0


async def log_credential_access(
    user_id: str,
    provider: str,
    action: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    provider_key = provider.lower()
    now = _now_iso()
    if _use_postgres():
        from server.db.pg_database import get_pg_pool

        pool = await get_pg_pool()
        if not pool:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO credential_access_log (user_id, provider, action, ip, ua, at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_id,
                provider_key,
                action,
                ip,
                ua,
                now,
            )
        return

    db = await get_db()
    await db.execute(
        """
        INSERT INTO credential_access_log (user_id, provider, action, ip, ua, at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, provider_key, action, ip, ua, now),
    )
    await db.commit()
