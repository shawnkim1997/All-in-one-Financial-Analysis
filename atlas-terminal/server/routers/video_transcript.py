"""Video transcript endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile

from server.models.schemas import VideoJob, VideoSearchHit, VideoSubmitRequest, VideoTranscript, VideoTranslation
from server.services.video_transcript_service import (
    delete_job,
    get_job_detail,
    list_jobs,
    search_jobs,
    submit_job,
    submit_upload,
    translate_job_content,
)

router = APIRouter()


def _resolve_api_key(header_value: str | None) -> str | None:
    return (header_value or "").strip() or None


@router.post("/submit", response_model=VideoJob, summary="Submit a video or audio transcript job")
async def submit_video_job(
    body: VideoSubmitRequest,
    x_gemini_api_key: str | None = Header(default=None),
) -> VideoJob:
    job_id = await submit_job(
        body.url,
        body.source_type,
        language=body.language,
        api_key=_resolve_api_key(x_gemini_api_key),
    )
    detail = await get_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=500, detail="Failed to create transcript job.")
    return VideoJob(**detail["job"])


@router.post("/upload", response_model=VideoJob, summary="Upload local media and start transcript extraction")
async def upload_video_file(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    x_gemini_api_key: str | None = Header(default=None),
) -> VideoJob:
    job_id = await submit_upload(
        file,
        language=language,
        api_key=_resolve_api_key(x_gemini_api_key),
    )
    detail = await get_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=500, detail="Failed to create transcript job.")
    return VideoJob(**detail["job"])


@router.get("/jobs", response_model=list[VideoJob], summary="List recent transcript jobs")
async def video_jobs(limit: int = Query(50, ge=1, le=200)) -> list[VideoJob]:
    rows = await list_jobs(limit=limit)
    return [VideoJob(**row) for row in rows]


@router.get("/jobs/{job_id}", summary="Get transcript job details")
async def video_job_detail(job_id: str) -> dict[str, VideoJob | VideoTranscript | None]:
    payload = await get_job_detail(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Transcript job not found.")
    transcript = payload["transcript"]
    return {
        "job": VideoJob(**payload["job"]),
        "transcript": None if transcript is None else VideoTranscript(**transcript),
    }


@router.post("/jobs/{job_id}/translate", response_model=VideoTranslation, summary="Translate a stored transcript on demand")
async def translate_video_job(
    job_id: str,
    x_gemini_api_key: str | None = Header(default=None),
    target_language: str = Query("ko", pattern="^[a-z]{2}$"),
) -> VideoTranslation:
    try:
        payload = await translate_job_content(
            job_id,
            target_language=target_language,
            api_key=_resolve_api_key(x_gemini_api_key),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload is None:
        raise HTTPException(status_code=404, detail="Transcript job not found.")
    return VideoTranslation(**payload)


@router.get("/search", response_model=list[VideoSearchHit], summary="Full-text search saved transcripts")
async def search_transcripts(
    q: str = Query(..., min_length=1, description="Query text"),
    limit: int = Query(20, ge=1, le=100),
) -> list[VideoSearchHit]:
    rows = await search_jobs(q, limit=limit)
    return [VideoSearchHit(**row) for row in rows]


@router.delete("/jobs/{job_id}", summary="Delete a transcript job")
async def delete_video_job(job_id: str) -> dict[str, object]:
    deleted = await delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transcript job not found.")
    return {"job_id": job_id, "deleted": True}
