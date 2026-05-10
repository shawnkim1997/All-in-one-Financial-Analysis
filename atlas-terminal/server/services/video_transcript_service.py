"""Video transcript ingestion, transcription, and analysis service."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import UploadFile

from server.db.unified_repo import repo
from server.services.gemini_service import generate_text
from server.services.text_chunker import _split_into_chunks, smart_chunk

try:  # pragma: no cover - optional dependency is exercised in integration use.
    import ffmpeg
except ImportError:  # pragma: no cover - tests run without multimedia stack installed.
    ffmpeg = None

try:  # pragma: no cover - optional dependency is exercised in integration use.
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - tests run without fallback binary installed.
    imageio_ffmpeg = None

try:  # pragma: no cover - optional dependency is exercised in integration use.
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - tests run without Whisper installed.
    WhisperModel = None

try:  # pragma: no cover - optional dependency is exercised in integration use.
    import srt
except ImportError:  # pragma: no cover - tests run without subtitle stack installed.
    srt = None

try:  # pragma: no cover - optional dependency is exercised in integration use.
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover - tests run without downloader installed.
    YoutubeDL = None

logger = logging.getLogger(__name__)

_YOUTUBE_CACHE_TTL = 30 * 24 * 60 * 60
_REMOTE_MAX_BYTES = 500 * 1024 * 1024
_PENDING_STATUSES = {"queued", "fetching", "transcribing", "analyzing"}
_WHISPER_MODEL_LOCK = Lock()
_WHISPER_MODEL: Any | None = None
_TASKS: dict[str, asyncio.Task[None]] = {}

_TEXT_STOPWORDS = {
    "about", "after", "again", "also", "been", "being", "because", "between", "could", "every",
    "from", "have", "into", "just", "like", "more", "most", "only", "other", "over", "should",
    "some", "such", "than", "that", "their", "there", "these", "they", "this", "those", "through",
    "very", "were", "what", "when", "where", "which", "while", "with", "would", "your", "ourselves",
    "ours", "you", "them", "then", "well", "will", "call", "speaker", "question", "answer", "video",
}
_POSITIVE_WORDS = {"growth", "strong", "improve", "upside", "record", "bullish", "accelerate", "opportunity"}
_NEGATIVE_WORDS = {"risk", "weak", "decline", "pressure", "downside", "loss", "uncertain", "headwind"}
_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
}
_VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac", ".webm"}
_CAPTION_EXTENSIONS = {".srt", ".vtt"}


@dataclass
class SourceMaterial:
    """Resolved source asset for one transcript job."""

    title: str | None = None
    duration_sec: int | None = None
    language: str | None = None
    transcript_text: str | None = None
    media_path: Path | None = None
    cleanup_paths: list[Path] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolved_gemini_api_key(api_key: str | None = None) -> str | None:
    resolved = (api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
    return resolved or None


def _cache_key(source_url: str) -> str:
    return f"video-transcript:{source_url.strip()}"


def _display_name_from_source(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.scheme:
        if parsed.path:
            tail = Path(parsed.path).name
            return tail or parsed.netloc or source_url
        return parsed.netloc or source_url
    return Path(source_url).expanduser().name or source_url


def _detect_source_type(url_or_path: str, source_type: Literal["youtube", "url", "local"]) -> Literal["youtube", "url", "local"]:
    candidate = (url_or_path or "").strip()
    if source_type == "youtube":
        return "youtube"
    if source_type == "local":
        return "local"
    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc.lower() in _YOUTUBE_HOSTS:
        return "youtube"
    if parsed.scheme in {"http", "https"}:
        return "url"
    if Path(candidate).expanduser().exists():
        return "local"
    return source_type


def _is_caption_file(path: Path) -> bool:
    return path.suffix.lower() in _CAPTION_EXTENSIONS


def _requires_audio_extraction(path: Path) -> bool:
    return path.suffix.lower() in _VIDEO_EXTENSIONS


def _is_supported_remote_content(content_type: str, suffix: str) -> bool:
    if suffix in _CAPTION_EXTENSIONS | _VIDEO_EXTENSIONS | _AUDIO_EXTENSIONS:
        return True
    if content_type.startswith("video/") or content_type.startswith("audio/"):
        return True
    return content_type in {"text/plain", "text/vtt", "application/x-subrip", "application/octet-stream"}


def _infer_suffix(source_url: str, content_type: str) -> str:
    parsed = urlparse(source_url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix:
        return suffix
    mapping = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "text/plain": ".txt",
        "text/vtt": ".vtt",
        "application/x-subrip": ".srt",
    }
    return mapping.get(content_type, ".bin")


def _cleanup_paths(paths: list[Path]) -> None:
    seen: set[str] = set()
    for path in paths:
        raw = str(path)
        if not raw or raw in seen:
            continue
        seen.add(raw)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            with suppress(FileNotFoundError):
                path.unlink()


def _resolve_ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if binary:
        return binary
    if imageio_ffmpeg is not None:
        return imageio_ffmpeg.get_ffmpeg_exe()
    raise RuntimeError(
        "ffmpeg is not installed. Install Homebrew ffmpeg or add `imageio-ffmpeg` to the Python environment."
    )


def _persist_upload(upload: UploadFile, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    upload.file.seek(0)
    with target_path.open("wb") as handle:
        shutil.copyfileobj(upload.file, handle)


def _pick_caption_file(directory: Path) -> Path | None:
    candidates = [path for path in directory.iterdir() if path.suffix.lower() in _CAPTION_EXTENSIONS]
    if not candidates:
        return None

    def _score(path: Path) -> tuple[int, str]:
        name = path.name.lower()
        if ".ko" in name:
            return (0, name)
        if ".en" in name:
            return (1, name)
        return (2, name)

    return sorted(candidates, key=_score)[0]


def _language_from_filename(path: Path) -> str | None:
    name = path.name.lower()
    if ".ko" in name:
        return "ko"
    if ".en" in name:
        return "en"
    return None


def _parse_vtt_text(vtt_content: str) -> str:
    lines: list[str] = []
    for raw_line in vtt_content.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or "-->" in line:
            continue
        if line.isdigit() or line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _parse_caption_text(content: str, suffix: str) -> str:
    if suffix == ".vtt":
        return _parse_vtt_text(content)
    return _parse_srt_text(content)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text or not text.strip():
        return None
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _top_terms(text: str, limit: int = 6) -> list[str]:
    counter: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text.lower()):
        if token in _TEXT_STOPWORDS:
            continue
        counter[token] = counter.get(token, 0) + 1
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _count in ranked[:limit]]


def _fallback_analysis(text: str) -> dict[str, Any]:
    excerpt = smart_chunk(text.strip(), max_chars=720)
    positives = sum(text.lower().count(word) for word in _POSITIVE_WORDS)
    negatives = sum(text.lower().count(word) for word in _NEGATIVE_WORDS)
    if positives > negatives:
        sentiment = "positive"
    elif negatives > positives:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    keywords = _top_terms(text, limit=6)
    return {
        "summary": excerpt or "Transcript extracted, but AI summary is unavailable.",
        "keywords": keywords,
        "topics": keywords[:4],
        "sentiment": sentiment,
        "intent": "Review transcript manually or add a Gemini API key for richer analysis.",
    }


def _language_display_name(target_language: str) -> str:
    return {
        "ko": "Korean",
        "ja": "Japanese",
        "en": "English",
    }.get(target_language.lower(), target_language.upper())


def _normalise_analysis(payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    keywords = payload.get("keywords")
    topics = payload.get("topics")
    sentiment = str(payload.get("sentiment") or fallback["sentiment"]).strip().lower()
    if sentiment not in {"positive", "neutral", "negative"}:
        sentiment = fallback["sentiment"]
    return {
        "summary": str(payload.get("summary") or fallback["summary"]).strip(),
        "keywords": [str(item).strip() for item in (keywords if isinstance(keywords, list) else fallback["keywords"]) if str(item).strip()],
        "topics": [str(item).strip() for item in (topics if isinstance(topics, list) else fallback["topics"]) if str(item).strip()],
        "sentiment": sentiment,
        "intent": str(payload.get("intent") or fallback["intent"]).strip(),
    }


def _get_whisper_model() -> Any:
    global _WHISPER_MODEL
    if _WHISPER_MODEL is not None:
        return _WHISPER_MODEL
    if WhisperModel is None:
        raise RuntimeError("faster-whisper is not installed. Run `pip install -r requirements.txt`.")
    with _WHISPER_MODEL_LOCK:
        if _WHISPER_MODEL is None:
            _WHISPER_MODEL = WhisperModel(
                os.getenv("WHISPER_MODEL_SIZE", "base"),
                device="cpu",
                compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            )
    return _WHISPER_MODEL


async def submit_job(
    url_or_path: str,
    source_type: Literal["youtube", "url", "local"],
    *,
    language: str | None = None,
    api_key: str | None = None,
    source_label: str | None = None,
    cleanup_source: bool = False,
) -> str:
    """Create a new transcript job and start asynchronous processing."""

    resolved_source_type = _detect_source_type(url_or_path, source_type)
    source_value = url_or_path.strip() if resolved_source_type != "local" else str(Path(url_or_path).expanduser())
    job_id = uuid4().hex
    await repo.add_video_job(job_id, source_value, resolved_source_type)
    if source_label:
        await repo.update_video_job(job_id, title=source_label)

    task = asyncio.create_task(
        _process_job(
            job_id,
            language=language,
            api_key=(api_key or "").strip() or None,
            source_label=source_label,
            cleanup_source=cleanup_source,
        )
    )
    _TASKS[job_id] = task
    task.add_done_callback(lambda _: _TASKS.pop(job_id, None))
    return job_id


async def submit_upload(upload: UploadFile, *, language: str | None = None, api_key: str | None = None) -> str:
    """Persist a multipart upload locally and enqueue it as a transcript job."""

    temp_dir = Path(tempfile.mkdtemp(prefix="atlas-video-upload-"))
    suffix = Path(upload.filename or "upload.bin").suffix
    target_path = temp_dir / f"upload{suffix}"
    await asyncio.to_thread(_persist_upload, upload, target_path)
    await upload.close()
    return await submit_job(
        str(target_path),
        "local",
        language=language,
        api_key=api_key,
        source_label=upload.filename or target_path.name,
        cleanup_source=True,
    )


async def list_jobs(limit: int = 50) -> list[dict[str, Any]]:
    return await repo.list_video_jobs(limit=limit)


async def get_job_detail(job_id: str) -> dict[str, Any] | None:
    row = await repo.get_video_job(job_id)
    if row is None:
        return None
    return {
        "job": {
            "job_id": row["job_id"],
            "status": row["status"],
            "source_url": row["source_url"],
            "source_type": row["source_type"],
            "progress": row.get("progress", 0),
            "error": row.get("error"),
            "title": row.get("title"),
            "duration_sec": row.get("duration_sec"),
            "language": row.get("language"),
            "created_at": row["created_at"],
            "completed_at": row.get("completed_at"),
        },
        "transcript": None if not row.get("transcript_text") else {
            "job_id": row["job_id"],
            "text": row.get("transcript_text", ""),
            "summary": row.get("summary"),
            "keywords": row.get("keywords", []),
            "topics": row.get("topics", []),
            "sentiment": row.get("sentiment"),
            "intent": row.get("intent"),
        },
    }


async def search_jobs(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return await repo.search_videos(query, limit=limit)


async def delete_job(job_id: str) -> bool:
    task = _TASKS.pop(job_id, None)
    if task is not None and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await task
    return await repo.delete_video_job(job_id)


async def translate_job_content(
    job_id: str,
    *,
    target_language: str = "ko",
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """Translate a stored transcript payload on demand."""

    row = await repo.get_video_job(job_id)
    if row is None:
        return None

    transcript_text = (row.get("transcript_text") or "").strip()
    if not transcript_text:
        raise ValueError("Transcript text is not available yet.")

    resolved_api_key = _resolved_gemini_api_key(api_key)
    if not resolved_api_key:
        raise RuntimeError("Set a Gemini API key in Settings to use Korean translation.")

    target_label = _language_display_name(target_language)
    translated_text = await _translate_text_chunks(
        transcript_text,
        target_language=target_language,
        api_key=resolved_api_key,
    )

    source_payload = {
        "summary": row.get("summary") or "",
        "keywords": row.get("keywords", []),
        "topics": row.get("topics", []),
        "intent": row.get("intent") or "",
    }
    meta_prompt = (
        f"Translate the following analyst metadata into natural {target_label}.\n"
        "Return ONLY valid JSON with this exact shape:\n"
        '{"summary":"...","keywords":["..."],"topics":["..."],"intent":"..."}\n'
        "- Preserve company names, proper nouns, and figures.\n"
        "- Translate keywords and topics into concise Korean finance/media terms.\n"
        "- Do not add markdown fences or commentary.\n\n"
        f"SOURCE_JSON:\n{json.dumps(source_payload, ensure_ascii=False)}"
    )
    translated_meta = _extract_json_object(
        await generate_text(meta_prompt, temperature=0.2, max_tokens=1200, api_key=resolved_api_key)
    ) or {}

    translated_summary = str(translated_meta.get("summary") or "").strip()
    if not translated_summary:
        translated_summary = await _translate_text_chunks(
            source_payload["summary"] or smart_chunk(transcript_text, max_chars=1500),
            target_language=target_language,
            api_key=resolved_api_key,
            max_chars=4_500,
            min_chunk=1_200,
        )

    return {
        "job_id": job_id,
        "target_language": target_language,
        "summary": translated_summary,
        "keywords": [str(item).strip() for item in (translated_meta.get("keywords") or source_payload["keywords"]) if str(item).strip()],
        "topics": [str(item).strip() for item in (translated_meta.get("topics") or source_payload["topics"]) if str(item).strip()],
        "intent": str(translated_meta.get("intent") or source_payload["intent"]).strip(),
        "text": translated_text,
    }


async def _process_job(
    job_id: str,
    *,
    language: str | None = None,
    api_key: str | None = None,
    source_label: str | None = None,
    cleanup_source: bool = False,
) -> None:
    """Resolve source media, extract transcript text, run analysis, and persist results."""

    row = await repo.get_video_job(job_id)
    if row is None:
        return

    cleanup_paths: list[Path] = []
    try:
        source_url = row["source_url"]
        source_type = _detect_source_type(source_url, row["source_type"])
        await repo.update_video_job(job_id, source_type=source_type, status="fetching", progress=15, error=None)

        if source_type == "youtube":
            cached = await repo.cache_get(_cache_key(source_url))
            if isinstance(cached, dict) and cached.get("transcript_text"):
                await repo.update_video_job(
                    job_id,
                    title=source_label or cached.get("title"),
                    duration_sec=cached.get("duration_sec"),
                    language=cached.get("language"),
                    transcript_text=cached.get("transcript_text"),
                    summary=cached.get("summary"),
                    keywords=cached.get("keywords", []),
                    topics=cached.get("topics", []),
                    sentiment=cached.get("sentiment"),
                    intent=cached.get("intent"),
                    status="completed",
                    progress=100,
                    completed_at=_now_iso(),
                    error=None,
                )
                return
            material = await _fetch_youtube_source(source_url, preferred_language=language)
        elif source_type == "local":
            material = await _prepare_local_source(source_url, owned_source=cleanup_source)
        else:
            material = await _fetch_remote_source(source_url)

        cleanup_paths.extend(material.cleanup_paths)
        title = source_label or material.title or row.get("title") or _display_name_from_source(source_url)
        detected_language = material.language or language
        duration_sec = material.duration_sec

        await repo.update_video_job(
            job_id,
            title=title,
            duration_sec=duration_sec,
            language=detected_language,
            status="transcribing",
            progress=45,
        )

        transcript_text = (material.transcript_text or "").strip()
        if not transcript_text:
            if material.media_path is None:
                raise RuntimeError("No subtitle track or downloadable media was found for this source.")
            transcribe_path = material.media_path
            if _requires_audio_extraction(material.media_path):
                transcribe_path = await asyncio.to_thread(_extract_audio_track, material.media_path)
                cleanup_paths.append(transcribe_path)
            whisper_result = await asyncio.to_thread(_whisper_transcribe, str(transcribe_path), language)
            transcript_text = (whisper_result.get("text") or "").strip()
            detected_language = whisper_result.get("language") or detected_language
            duration_value = whisper_result.get("duration_sec") or duration_sec
            duration_sec = int(round(duration_value)) if duration_value else duration_sec

        if not transcript_text:
            raise RuntimeError("Transcript extraction finished, but no text was produced.")

        await repo.update_video_job(
            job_id,
            title=title,
            duration_sec=duration_sec,
            language=detected_language,
            transcript_text=transcript_text,
            progress=65,
        )

        await repo.update_video_job(job_id, status="analyzing", progress=80)
        analysis = await _analyze_text(transcript_text, api_key=api_key, title=title)
        completed_at = _now_iso()
        await repo.update_video_job(
            job_id,
            status="completed",
            progress=100,
            completed_at=completed_at,
            error=None,
            title=title,
            duration_sec=duration_sec,
            language=detected_language,
            transcript_text=transcript_text,
            summary=analysis["summary"],
            keywords=analysis["keywords"],
            topics=analysis["topics"],
            sentiment=analysis["sentiment"],
            intent=analysis["intent"],
        )

        if source_type == "youtube":
            await repo.cache_set(
                _cache_key(source_url),
                {
                    "title": title,
                    "duration_sec": duration_sec,
                    "language": detected_language,
                    "transcript_text": transcript_text,
                    "summary": analysis["summary"],
                    "keywords": analysis["keywords"],
                    "topics": analysis["topics"],
                    "sentiment": analysis["sentiment"],
                    "intent": analysis["intent"],
                    "completed_at": completed_at,
                },
                ttl=_YOUTUBE_CACHE_TTL,
            )
    except asyncio.CancelledError:
        logger.info("Video transcript job %s cancelled.", job_id)
        raise
    except Exception as exc:
        logger.exception("Video transcript job %s failed", job_id)
        await repo.update_video_job(
            job_id,
            status="failed",
            progress=100,
            error=str(exc),
            completed_at=_now_iso(),
        )
    finally:
        await asyncio.to_thread(_cleanup_paths, cleanup_paths)


async def _prepare_local_source(source_path: str, *, owned_source: bool = False) -> SourceMaterial:
    path = Path(source_path).expanduser()
    if not path.exists():
        raise RuntimeError(f"Local file not found: {path}")
    cleanup_paths = [path.parent] if owned_source else []
    if _is_caption_file(path):
        content = await asyncio.to_thread(path.read_text, encoding="utf-8", errors="ignore")
        return SourceMaterial(
            title=path.name,
            language=_language_from_filename(path),
            transcript_text=_parse_caption_text(content, path.suffix.lower()),
            cleanup_paths=cleanup_paths,
        )
    return SourceMaterial(
        title=path.name,
        media_path=path,
        cleanup_paths=cleanup_paths,
    )


async def _fetch_remote_source(source_url: str) -> SourceMaterial:
    if _detect_source_type(source_url, "url") == "youtube":
        return await _fetch_youtube_source(source_url)

    temp_dir = Path(tempfile.mkdtemp(prefix="atlas-video-remote-"))
    content_type = ""
    target_path = temp_dir / "download.bin"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=20.0)) as client:
            async with client.stream("GET", source_url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                content_length = int(response.headers.get("content-length") or 0)
                if content_length and content_length > _REMOTE_MAX_BYTES:
                    raise RuntimeError("Remote media is larger than the 500MB safety limit.")
                suffix = _infer_suffix(source_url, content_type)
                if not _is_supported_remote_content(content_type, suffix):
                    raise RuntimeError(f"Unsupported remote content type: {content_type or suffix}")
                target_path = temp_dir / f"download{suffix}"
                total_bytes = 0
                with target_path.open("wb") as handle:
                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > _REMOTE_MAX_BYTES:
                            raise RuntimeError("Remote media exceeded the 500MB safety limit while downloading.")
                        handle.write(chunk)
    except Exception:
        await asyncio.to_thread(_cleanup_paths, [temp_dir])
        raise

    if _is_caption_file(target_path):
        content = await asyncio.to_thread(target_path.read_text, encoding="utf-8", errors="ignore")
        return SourceMaterial(
            title=_display_name_from_source(source_url),
            language=_language_from_filename(target_path),
            transcript_text=_parse_caption_text(content, target_path.suffix.lower()),
            cleanup_paths=[temp_dir],
        )

    return SourceMaterial(
        title=_display_name_from_source(source_url),
        media_path=target_path,
        cleanup_paths=[temp_dir],
    )


async def _fetch_youtube_source(source_url: str, preferred_language: str | None = None) -> SourceMaterial:
    temp_dir = Path(tempfile.mkdtemp(prefix="atlas-video-youtube-"))
    try:
        info: dict[str, Any] = {}
        try:
            info = await asyncio.to_thread(_download_youtube_subtitles, source_url, temp_dir, preferred_language)
        except Exception:
            logger.warning("YouTube subtitle download failed for %s; falling back to audio transcription.", source_url, exc_info=True)
        title = str(info.get("title") or _display_name_from_source(source_url))
        duration_sec = int(info.get("duration")) if info.get("duration") else None
        caption_path = _pick_caption_file(temp_dir)
        if caption_path is not None:
            content = await asyncio.to_thread(caption_path.read_text, encoding="utf-8", errors="ignore")
            return SourceMaterial(
                title=title,
                duration_sec=duration_sec,
                language=_language_from_filename(caption_path),
                transcript_text=_parse_caption_text(content, caption_path.suffix.lower()),
                cleanup_paths=[temp_dir],
            )

        media_path, audio_info = await asyncio.to_thread(_download_youtube_audio, source_url, temp_dir)
        return SourceMaterial(
            title=str(audio_info.get("title") or title),
            duration_sec=int(audio_info.get("duration")) if audio_info.get("duration") else duration_sec,
            media_path=media_path,
            cleanup_paths=[temp_dir],
        )
    except Exception:
        await asyncio.to_thread(_cleanup_paths, [temp_dir])
        raise


def _normalise_subtitle_languages(preferred_language: str | None = None) -> list[str]:
    ordered: list[str] = []
    for value in [preferred_language, "en", "ko", "en-US", "ko-KR"]:
        candidate = (value or "").strip()
        if candidate and candidate not in ordered:
            ordered.append(candidate)
    return ordered


def _download_youtube_subtitles(source_url: str, output_dir: Path, preferred_language: str | None = None) -> dict[str, Any]:
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp is not installed. Run `pip install -r requirements.txt`.")
    last_error: Exception | None = None
    for language in _normalise_subtitle_languages(preferred_language):
        options = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": [language],
            "subtitlesformat": "srt/vtt/best",
            "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        }
        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(source_url, download=True)
            if _pick_caption_file(output_dir) is not None:
                return info
        except Exception as exc:
            last_error = exc
            logger.warning("Subtitle attempt failed for language %s on %s", language, source_url, exc_info=True)

    if last_error is not None:
        raise last_error
    return {}


def _download_youtube_audio(source_url: str, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    if YoutubeDL is None:
        raise RuntimeError("yt-dlp is not installed. Run `pip install -r requirements.txt`.")
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(source_url, download=True)
        return Path(ydl.prepare_filename(info)), info


def _extract_audio_track(media_path: Path) -> Path:
    if ffmpeg is None:
        raise RuntimeError("ffmpeg-python is not installed. Run `pip install -r requirements.txt`.")
    output_path = media_path.parent / f"{media_path.stem}.atlas.wav"
    ffmpeg_binary = _resolve_ffmpeg_binary()
    try:
        stream = ffmpeg.input(str(media_path))
        stream = ffmpeg.output(stream, str(output_path), acodec="pcm_s16le", ac=1, ar="16000", format="wav")
        ffmpeg.run(stream.overwrite_output(), cmd=ffmpeg_binary, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as exc:  # type: ignore[attr-defined]
        stderr = exc.stderr.decode("utf-8", errors="ignore") if getattr(exc, "stderr", None) else str(exc)
        raise RuntimeError(f"ffmpeg failed to extract audio: {stderr.strip()}") from exc
    return output_path


def _whisper_transcribe(audio_path: str, language: str | None = None) -> dict[str, Any]:
    """Transcribe audio or video with a lazily loaded faster-whisper model."""

    model = _get_whisper_model()
    segments, info = model.transcribe(audio_path, language=language, vad_filter=True, beam_size=5)
    parsed_segments: list[dict[str, Any]] = []
    for segment in segments:
        text = (segment.text or "").strip()
        if not text:
            continue
        parsed_segments.append(
            {
                "start": round(float(segment.start), 2),
                "end": round(float(segment.end), 2),
                "text": text,
            }
        )
    full_text = " ".join(segment["text"] for segment in parsed_segments).strip()
    duration_sec = getattr(info, "duration", None) or (parsed_segments[-1]["end"] if parsed_segments else 0)
    return {
        "text": full_text,
        "language": getattr(info, "language", None) or language,
        "duration_sec": duration_sec,
        "segments": parsed_segments,
    }


def _parse_srt_text(srt_content: str) -> str:
    """Strip timing metadata and join subtitle text into a clean transcript."""

    if not srt_content.strip():
        return ""
    if srt is None:
        cleaned = re.sub(r"\d+\s+\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}", "", srt_content)
        cleaned = re.sub(r"^\d+\s*$", "", cleaned, flags=re.MULTILINE)
        return "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())

    subtitles = []
    for item in srt.parse(srt_content):
        text = " ".join(line.strip() for line in item.content.splitlines() if line.strip()).strip()
        if text:
            subtitles.append(text)
    return "\n".join(subtitles)


async def _analyze_text(text: str, *, api_key: str | None = None, title: str | None = None) -> dict[str, Any]:
    """Generate a summary, topics, and sentiment for a transcript."""

    fallback = _fallback_analysis(text)
    chunk_candidates = _split_into_chunks(text, max_chars=10_000, min_chunk=3_000)
    chunks = [smart_chunk(chunk, max_chars=10_000) for chunk in chunk_candidates if chunk.strip()] or [smart_chunk(text, max_chars=10_000)]

    try:
        partial_summaries: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            prompt = (
                "You are preparing analyst notes from one transcript chunk.\n"
                f"Chunk {index} of {len(chunks)} for: {title or 'Untitled media'}\n\n"
                "Return 4-6 concise bullet points covering factual takeaways, recurring themes, risks, and speaker tone.\n"
                "Do not invent facts. Keep names, products, and figures exact when present.\n\n"
                f"TRANSCRIPT CHUNK:\n{chunk}"
            )
            partial_summaries.append(
                await generate_text(prompt, temperature=0.2, max_tokens=700, api_key=api_key)
            )

        summary_blob = "\n\n".join(f"Chunk {idx} notes:\n{summary.strip()}" for idx, summary in enumerate(partial_summaries, start=1))
        head_sample = smart_chunk(text[:10_000], max_chars=2_000)
        tail_sample = smart_chunk(text[-10_000:], max_chars=2_000)
        final_prompt = (
            "You are an expert media and transcript analyst.\n"
            "Use the chunk notes and transcript samples below.\n"
            "Return ONLY valid JSON with this exact shape:\n"
            '{"summary":"...","keywords":["..."],"topics":["..."],"sentiment":"positive|neutral|negative","intent":"..."}\n'
            "Rules:\n"
            "- summary: 3-5 sentences, specific and factual\n"
            "- keywords: 5-8 concise phrases\n"
            "- topics: 3-5 broader themes\n"
            "- sentiment: choose only positive, neutral, or negative\n"
            "- intent: one concise sentence describing what the speaker or content is trying to achieve\n"
            "- Do not add markdown fences or commentary.\n\n"
            f"TITLE: {title or 'Untitled media'}\n\n"
            f"CHUNK NOTES:\n{summary_blob}\n\n"
            f"HEAD SAMPLE:\n{head_sample}\n\n"
            f"TAIL SAMPLE:\n{tail_sample}"
        )
        parsed = _extract_json_object(
            await generate_text(final_prompt, temperature=0.2, max_tokens=1200, api_key=api_key)
        )
        if parsed is None:
            return fallback
        return _normalise_analysis(parsed, fallback)
    except Exception:
        logger.warning("Falling back to heuristic transcript analysis.", exc_info=True)
        return fallback


async def _translate_text_chunks(
    text: str,
    *,
    target_language: str,
    api_key: str,
    max_chars: int = 7_000,
    min_chunk: int = 2_000,
) -> str:
    """Translate long text in chunks while preserving structure."""

    source = text.strip()
    if not source:
        return ""

    target_label = _language_display_name(target_language)
    chunks = _split_into_chunks(source, max_chars=max_chars, min_chunk=min_chunk) or [source]
    translated_chunks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = (
            f"Translate the following transcript chunk into natural {target_label}.\n"
            "- Preserve meaning, numbers, names, and paragraph breaks.\n"
            "- Keep speaker turns and emphasis where obvious.\n"
            "- Return ONLY the translated text.\n"
            f"- This is chunk {index} of {len(chunks)}.\n\n"
            f"TRANSCRIPT CHUNK:\n{chunk}"
        )
        translated_chunks.append(
            (await generate_text(prompt, temperature=0.2, max_tokens=2200, api_key=api_key)).strip()
        )
    return "\n\n".join(chunk for chunk in translated_chunks if chunk)
