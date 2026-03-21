"""FastAPI router for AI chat with SSE streaming.

Compatible with Vercel AI SDK's ``useChat`` hook on the frontend.
SSE format: ``data: <text>\\n\\n`` per chunk, ``data: [DONE]\\n\\n`` at end.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from server.ai.context_builder import context_builder
from server.ai.llm_router import LLMConfig, LLMProvider, llm_router

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ChatRequest(BaseModel):
    """Payload for chat endpoints."""

    messages: list[ChatMessage]
    ticker: Optional[str] = None
    active_widgets: list[str] = Field(default_factory=list)
    widget_data: dict[str, Any] = Field(default_factory=dict)
    provider: Optional[str] = None  # Force a specific provider


class ConfigureRequest(BaseModel):
    """Payload for LLM configuration."""

    provider: str
    api_key: str


class ChatCompletionResponse(BaseModel):
    """Non-streaming chat response."""

    content: str
    provider: str
    model: str


class SuggestedQuestionsResponse(BaseModel):
    """Suggested questions response."""

    questions: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_prompt(messages: list[ChatMessage]) -> str:
    """Collapse chat history into a single prompt string.

    The most recent user message is used as the primary prompt; earlier
    messages provide conversational context.
    """
    parts: list[str] = []
    for msg in messages[:-1]:
        prefix = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{prefix}: {msg.content}")

    if messages:
        parts.append(messages[-1].content)

    return "\n\n".join(parts)


def _resolve_llm_config(
    provider_name: Optional[str],
) -> Optional[LLMConfig]:
    """Build an ``LLMConfig`` if the caller forced a provider."""
    if not provider_name:
        return None
    try:
        provider = LLMProvider(provider_name.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{provider_name}'. "
            f"Supported: gemini, claude, openai",
        )
    return LLMConfig(provider=provider)


async def _sse_generator(
    prompt: str,
    system_prompt: str,
    config: Optional[LLMConfig],
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted chunks compatible with Vercel AI SDK ``useChat``.

    Format per chunk::

        data: {"content":"<text>"}\n\n

    Terminal event::

        data: [DONE]\n\n
    """
    try:
        async for chunk in llm_router.stream(
            prompt=prompt,
            config=config,
            system_prompt=system_prompt,
        ):
            # Vercel AI SDK expects plain text chunks in `data:` field
            yield f"data: {json.dumps({'content': chunk})}\n\n"
    except RuntimeError as exc:
        logger.error("LLM stream error: %s", exc)
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"
    except Exception:
        logger.error("Unexpected stream error:\n%s", traceback.format_exc())
        yield f"data: {json.dumps({'error': 'Internal server error'})}\n\n"
    finally:
        yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream AI response via Server-Sent Events.

    Compatible with Vercel AI SDK's ``useChat`` hook.
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages list is empty")

    # 1. Build context from active widgets
    system_prompt = context_builder.build_system_prompt(
        ticker=request.ticker or "",
        active_widgets=request.active_widgets,
        widget_data=request.widget_data,
    )

    # 2. Build the prompt from conversation history
    prompt = _build_prompt(request.messages)

    # 3. Resolve optional provider override
    config = _resolve_llm_config(request.provider)

    # 4. Return SSE stream
    return StreamingResponse(
        _sse_generator(prompt, system_prompt, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/complete", response_model=ChatCompletionResponse)
async def chat_complete(request: ChatRequest) -> ChatCompletionResponse:
    """Non-streaming AI response."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages list is empty")

    system_prompt = context_builder.build_system_prompt(
        ticker=request.ticker or "",
        active_widgets=request.active_widgets,
        widget_data=request.widget_data,
    )

    prompt = _build_prompt(request.messages)
    config = _resolve_llm_config(request.provider)
    resolved = llm_router._resolve_config(prompt, config)

    try:
        content = await llm_router.generate(
            prompt=prompt,
            config=config,
            system_prompt=system_prompt,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.error("Chat completion error:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal server error")

    return ChatCompletionResponse(
        content=content,
        provider=resolved.provider.value,
        model=resolved.model,
    )


@router.get("/suggested", response_model=SuggestedQuestionsResponse)
async def get_suggested_questions(
    ticker: str = "",
    widgets: str = "",
) -> SuggestedQuestionsResponse:
    """Return suggested questions based on active widgets.

    Args:
        ticker: Active ticker symbol (currently unused, reserved for future).
        widgets: Comma-separated list of active widget identifiers,
                 e.g. ``"dcf,financials,technical"``.
    """
    active_widgets = [w.strip() for w in widgets.split(",") if w.strip()]
    questions = context_builder.build_suggested_questions(active_widgets)
    return SuggestedQuestionsResponse(questions=questions)


@router.post("/configure")
async def configure_llm(request: ConfigureRequest) -> dict[str, str]:
    """Configure an LLM provider with an API key.

    Returns the list of currently available providers after configuration.
    """
    try:
        provider = LLMProvider(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider '{request.provider}'. "
            f"Supported: gemini, claude, openai",
        )

    if not request.api_key:
        raise HTTPException(status_code=400, detail="api_key is required")

    llm_router.configure(provider, request.api_key)

    available = [p.value for p in llm_router.get_available_providers()]
    return {
        "status": "ok",
        "provider": provider.value,
        "available_providers": ", ".join(available),
    }
