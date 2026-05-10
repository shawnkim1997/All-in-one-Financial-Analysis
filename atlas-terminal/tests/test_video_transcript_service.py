"""Tests for the video transcript service and repository integration."""

from __future__ import annotations

import asyncio

from server.db.unified_repo import repo
from server.services import video_transcript_service as service


def test_parse_srt_text_strips_timestamps() -> None:
    raw_srt = """1
00:00:00,000 --> 00:00:01,500
Welcome to the call.

2
00:00:01,500 --> 00:00:03,000
Revenue grew 12%.
"""

    parsed = service._parse_srt_text(raw_srt)

    assert "00:00:00,000" not in parsed
    assert parsed == "Welcome to the call.\nRevenue grew 12%."


def test_analyze_text_runs_chunk_map_reduce(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_generate_text(prompt: str, **_: object) -> str:
        calls.append(prompt)
        if len(calls) < 3:
            return f"- chunk note {len(calls)}"
        return (
            '{"summary":"Management highlighted revenue growth.",'
            '"keywords":["revenue growth","guidance"],'
            '"topics":["Earnings"],'
            '"sentiment":"positive",'
            '"intent":"Reassure investors about momentum."}'
        )

    monkeypatch.setattr(service, "generate_text", fake_generate_text)
    monkeypatch.setattr(service, "_split_into_chunks", lambda text, max_chars=10_000, min_chunk=3_000: ["chunk one", "chunk two"])

    result = asyncio.run(service._analyze_text("long transcript body", api_key="test-key", title="Demo call"))

    assert result["summary"] == "Management highlighted revenue growth."
    assert result["keywords"] == ["revenue growth", "guidance"]
    assert len(calls) == 3


def test_submit_job_processes_statuses_to_completion(monkeypatch) -> None:
    async def run_test() -> None:
        await repo.init_db()
        statuses: list[str] = []
        original_update = service.repo.update_video_job

        async def recording_update(job_id: str, **fields: object):
            if "status" in fields:
                statuses.append(str(fields["status"]))
            return await original_update(job_id, **fields)

        async def fake_prepare_local_source(source_path: str, *, owned_source: bool = False) -> service.SourceMaterial:
            return service.SourceMaterial(
                title="demo.mp4",
                duration_sec=96,
                language="en",
                transcript_text="Revenue grew strongly and management stayed confident about AI demand.",
            )

        async def fake_analyze_text(text: str, *, api_key: str | None = None, title: str | None = None):
            return {
                "summary": "Revenue and AI demand were the main focus.",
                "keywords": ["revenue", "ai demand"],
                "topics": ["Earnings"],
                "sentiment": "positive",
                "intent": "Reassure investors about execution.",
            }

        monkeypatch.setattr(service.repo, "update_video_job", recording_update)
        monkeypatch.setattr(service, "_prepare_local_source", fake_prepare_local_source)
        monkeypatch.setattr(service, "_analyze_text", fake_analyze_text)

        job_id = await service.submit_job("/tmp/demo.mp4", "local", api_key="test-key", source_label="demo.mp4")
        await service._TASKS[job_id]
        row = await repo.get_video_job(job_id)

        assert row is not None
        assert row["status"] == "completed"
        assert row["progress"] == 100
        assert row["summary"] == "Revenue and AI demand were the main focus."
        assert statuses == ["fetching", "transcribing", "analyzing", "completed"]

    asyncio.run(run_test())


def test_video_fts_search_returns_snippet() -> None:
    async def run_test() -> None:
        await repo.init_db()
        await repo.add_video_job("job-1", "https://example.com/earnings", "url")
        await repo.update_video_job(
            "job-1",
            title="Q1 Earnings Call",
            transcript_text="Management discussed AI revenue, guidance, and margin expansion in detail.",
            summary="AI revenue and guidance dominated the discussion.",
        )
        await repo.add_video_job("job-2", "https://example.com/interview", "url")
        await repo.update_video_job(
            "job-2",
            title="CEO Interview",
            transcript_text="Consumer demand remained steady and product cadence was unchanged.",
        )

        hits = await repo.search_videos("guidance", limit=10)

        assert hits
        assert hits[0]["job_id"] == "job-1"
        assert "guidance" in hits[0]["snippet"].lower()
        assert hits[0]["rank"] > 0

    asyncio.run(run_test())


def test_translate_job_content_translates_meta_and_chunks(monkeypatch) -> None:
    async def run_test() -> None:
        await repo.init_db()
        await repo.add_video_job("job-ko", "https://example.com/demo", "url")
        await repo.update_video_job(
            "job-ko",
            transcript_text="first chunk\n\nsecond chunk",
            summary="Original summary.",
            keywords=["guidance", "margin"],
            topics=["Earnings"],
            intent="Reassure investors.",
            status="completed",
            progress=100,
        )

        prompts: list[str] = []

        async def fake_generate_text(prompt: str, **_: object) -> str:
            prompts.append(prompt)
            if "SOURCE_JSON" in prompt:
                return (
                    '{"summary":"번역된 요약","keywords":["가이던스","마진"],'
                    '"topics":["실적"],"intent":"투자자를 안심시키려는 목적입니다."}'
                )
            if "chunk 1 of 2" in prompt:
                return "첫 번째 청크"
            if "chunk 2 of 2" in prompt:
                return "두 번째 청크"
            return "대체 요약"

        monkeypatch.setattr(service, "generate_text", fake_generate_text)
        monkeypatch.setattr(service, "_split_into_chunks", lambda text, max_chars=7000, min_chunk=2000: ["first chunk", "second chunk"])

        translated = await service.translate_job_content("job-ko", target_language="ko", api_key="test-key")

        assert translated is not None
        assert translated["summary"] == "번역된 요약"
        assert translated["keywords"] == ["가이던스", "마진"]
        assert translated["text"] == "첫 번째 청크\n\n두 번째 청크"
        assert len(prompts) == 3

    asyncio.run(run_test())
