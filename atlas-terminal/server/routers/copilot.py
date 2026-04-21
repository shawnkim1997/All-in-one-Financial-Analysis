"""Copilot chat router with terminal context injection."""

from __future__ import annotations

import json
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.routers.analysis import _call_gemini, _get_financial_context

router = APIRouter()


class CopilotContext(BaseModel):
    activeSymbol: str | None = None
    activePage: str = "equity"
    recentSymbols: list[str] = Field(default_factory=list)
    currency: str = "USD"
    theme: str = "bloomberg"
    watchlist: list[str] = Field(default_factory=list)


class CopilotMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class CopilotChatRequest(BaseModel):
    message: str
    context: CopilotContext = Field(default_factory=CopilotContext)
    history: list[CopilotMessage] = Field(default_factory=list)
    api_key: str = ""


@router.post("/chat")
async def copilot_chat(req: CopilotChatRequest) -> dict[str, Any]:
    api_key = req.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key is required")

    active_symbol = (req.context.activeSymbol or "").strip().upper()
    context_json = json.dumps(req.context.model_dump(), ensure_ascii=False, indent=2)
    financial_context = _get_financial_context(active_symbol) if active_symbol else "No active financial symbol."
    history = "\n".join(f"{msg.role}: {msg.content}" for msg in req.history[-8:])
    prompt = f"""
You are ATLAS Copilot, a concise equity research assistant embedded in ATLAS Terminal.
Use the terminal context below to answer the user's question. Do not invent numbers.
If a requested figure is not in context, say what data would be needed.

Terminal context:
{context_json}

Financial context for active symbol:
{financial_context}

Recent conversation:
{history or "No prior messages."}

User question:
{req.message}
""".strip()

    text = await _call_gemini(api_key=api_key, prompt=prompt, max_tokens=2048, temperature=0.35)
    return {"message": text, "context": req.context.model_dump()}
