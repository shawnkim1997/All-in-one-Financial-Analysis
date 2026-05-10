"""PostgreSQL repository for persisted video transcript jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from server.db.pg_database import get_pg_pool


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _coerce_datetime(value: Any) -> Any:
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _normalise_row(row: Any) -> dict[str, Any]:
    payload = dict(row)
    payload["keywords"] = _coerce_list(payload.pop("keywords_json", []))
    payload["topics"] = _coerce_list(payload.pop("topics_json", []))
    if payload.get("created_at") is not None:
        payload["created_at"] = payload["created_at"].isoformat()
    if payload.get("completed_at") is not None:
        payload["completed_at"] = payload["completed_at"].isoformat()
    return payload


def _normalise_updates(fields: dict[str, Any]) -> dict[str, Any]:
    alias_map = {"keywords": "keywords_json", "topics": "topics_json"}
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
            normalised[mapped_key] = _coerce_list(value)
        elif mapped_key in {"completed_at"}:
            normalised[mapped_key] = _coerce_datetime(value)
        else:
            normalised[mapped_key] = value
    return normalised


async def pg_add_video_job(job_id: str, url: str, source_type: str) -> dict[str, Any] | None:
    pool = await get_pg_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO video_jobs (job_id, source_url, source_type, status, progress)
            VALUES ($1, $2, $3, 'queued', 0)
            RETURNING *
            """,
            job_id,
            url,
            source_type,
        )
        return _normalise_row(row) if row else None


async def pg_update_video_job(job_id: str, **fields: Any) -> dict[str, Any] | None:
    pool = await get_pg_pool()
    if not pool:
        return None
    updates = _normalise_updates(fields)
    async with pool.acquire() as conn:
        if updates:
            set_clause = ", ".join(f"{column} = ${index + 2}" for index, column in enumerate(updates))
            values = [job_id] + list(updates.values())
            row = await conn.fetchrow(
                f"UPDATE video_jobs SET {set_clause} WHERE job_id = $1 RETURNING *",  # noqa: S608
                *values,
            )
            return _normalise_row(row) if row else None
        row = await conn.fetchrow("SELECT * FROM video_jobs WHERE job_id = $1", job_id)
        return _normalise_row(row) if row else None


async def pg_get_video_job(job_id: str) -> dict[str, Any] | None:
    pool = await get_pg_pool()
    if not pool:
        return None
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM video_jobs WHERE job_id = $1", job_id)
        return _normalise_row(row) if row else None


async def pg_list_video_jobs(limit: int = 50) -> list[dict[str, Any]]:
    pool = await get_pg_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                job_id, source_url, source_type, status, progress, error, title,
                duration_sec, language, created_at, completed_at
            FROM video_jobs
            ORDER BY created_at DESC
            LIMIT $1
            """,
            limit,
        )
        return [_normalise_row(row) for row in rows]


async def pg_search_videos(query: str, limit: int = 20) -> list[dict[str, Any]]:
    pool = await get_pg_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                job_id,
                title,
                ts_headline(
                    'simple',
                    coalesce(transcript_text, ''),
                    plainto_tsquery('simple', $1),
                    'StartSel=[,StopSel=],MaxFragments=1,MaxWords=18,MinWords=6'
                ) AS snippet,
                ts_rank_cd(
                    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(transcript_text, '')),
                    plainto_tsquery('simple', $1)
                ) AS rank
            FROM video_jobs
            WHERE to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(transcript_text, ''))
                  @@ plainto_tsquery('simple', $1)
            ORDER BY rank DESC, created_at DESC
            LIMIT $2
            """,
            query,
            limit,
        )
        return [
            {
                "job_id": row["job_id"],
                "title": row["title"],
                "snippet": row["snippet"] or "",
                "rank": float(row["rank"] or 0.0),
            }
            for row in rows
        ]


async def pg_delete_video_job(job_id: str) -> bool:
    pool = await get_pg_pool()
    if not pool:
        return False
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM video_jobs WHERE job_id = $1", job_id)
        return result == "DELETE 1"
