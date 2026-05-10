"""SQLite repository for persisted video transcript jobs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from server.db.database import get_db

_SEARCH_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["keywords"] = _coerce_json_list(data.pop("keywords_json", []))
    data["topics"] = _coerce_json_list(data.pop("topics_json", []))
    return data


def _normalise_updates(fields: dict[str, Any]) -> dict[str, Any]:
    alias_map = {
        "keywords": "keywords_json",
        "topics": "topics_json",
    }
    allowed = {
        "source_url",
        "source_type",
        "status",
        "progress",
        "error",
        "title",
        "duration_sec",
        "language",
        "transcript_text",
        "summary",
        "keywords_json",
        "topics_json",
        "sentiment",
        "intent",
        "completed_at",
    }
    normalised: dict[str, Any] = {}
    for key, value in fields.items():
        mapped_key = alias_map.get(key, key)
        if mapped_key not in allowed:
            continue
        if mapped_key in {"keywords_json", "topics_json"}:
            normalised[mapped_key] = json.dumps(_coerce_json_list(value), ensure_ascii=False)
        else:
            normalised[mapped_key] = value
    return normalised


def _build_fts_query(query: str) -> str:
    tokens = [token.lower() for token in _SEARCH_TOKEN_RE.findall(query)]
    if not tokens:
        return ""
    return " AND ".join(f"{token}*" for token in tokens)


async def add_video_job(job_id: str, url: str, source_type: str) -> dict[str, Any] | None:
    db = await get_db()
    created_at = _now_iso()
    await db.execute(
        """
        INSERT INTO video_jobs (
            job_id, source_url, source_type, status, progress, created_at
        ) VALUES (?, ?, ?, 'queued', 0, ?)
        """,
        (job_id, url, source_type, created_at),
    )
    await db.commit()
    return await get_video_job(job_id)


async def update_video_job(job_id: str, **fields: Any) -> dict[str, Any] | None:
    updates = _normalise_updates(fields)
    db = await get_db()
    if updates:
        set_clause = ", ".join(f"{column} = ?" for column in updates)
        values = list(updates.values()) + [job_id]
        await db.execute(
            f"UPDATE video_jobs SET {set_clause} WHERE job_id = ?",  # noqa: S608
            values,
        )
        await db.commit()
    return await get_video_job(job_id)


async def get_video_job(job_id: str) -> dict[str, Any] | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM video_jobs WHERE job_id = ?", (job_id,))
    row = await cursor.fetchone()
    return _row_to_dict(row)


async def list_video_jobs(limit: int = 50) -> list[dict[str, Any]]:
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT
            job_id, source_url, source_type, status, progress, error, title,
            duration_sec, language, created_at, completed_at
        FROM video_jobs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = await cursor.fetchall()
    return [row for row in (_row_to_dict(item) for item in rows) if row is not None]


async def search_videos(query: str, limit: int = 20) -> list[dict[str, Any]]:
    fts_query = _build_fts_query(query)
    if not fts_query:
        return []
    db = await get_db()
    cursor = await db.execute(
        """
        SELECT
            video_jobs.job_id,
            video_jobs.title,
            COALESCE(
                snippet(video_jobs_fts, 2, '[', ']', '...', 16),
                substr(video_jobs.transcript_text, 1, 180)
            ) AS snippet,
            (1.0 / (1.0 + bm25(video_jobs_fts))) AS rank
        FROM video_jobs_fts
        JOIN video_jobs ON video_jobs.rowid = video_jobs_fts.rowid
        WHERE video_jobs_fts MATCH ?
        ORDER BY bm25(video_jobs_fts), video_jobs.created_at DESC
        LIMIT ?
        """,
        (fts_query, limit),
    )
    rows = await cursor.fetchall()
    return [
        {
            "job_id": row["job_id"],
            "title": row["title"],
            "snippet": row["snippet"] or "",
            "rank": float(row["rank"] or 0.0),
        }
        for row in rows
    ]


async def delete_video_job(job_id: str) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM video_jobs WHERE job_id = ?", (job_id,))
    await db.commit()
    return cursor.rowcount > 0
