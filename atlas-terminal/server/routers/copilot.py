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


class RedTeamRequest(BaseModel):
    ticker: str = Field(..., min_length=1)
    thesis: str = Field(..., min_length=10)
    api_key: str = ""


def _fallback_red_team(ticker: str, thesis: str) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "source": "rules",
        "critiques": [
            {
                "argument": f"{ticker} may already price in the upside described in the thesis.",
                "evidence_needed": "Compare current valuation multiples, growth expectations, and revision trends against peers.",
                "severity": "high",
            },
            {
                "argument": "The thesis may underweight execution risk and the time required for the catalyst to flow through earnings.",
                "evidence_needed": "Track management guidance, milestone delivery, margin bridge, and capex or working-capital needs.",
                "severity": "medium",
            },
            {
                "argument": "A bearish macro or rates regime could compress multiples even if company fundamentals improve.",
                "evidence_needed": "Stress-test the valuation against lower terminal multiples, higher discount rates, and weaker demand.",
                "severity": "medium",
            },
            {
                "argument": "The strongest counter-case is that consensus already understands the narrative but disagrees on durability.",
                "evidence_needed": "Review sell-side estimate dispersion, short interest, and the gap between narrative KPIs and reported cash flow.",
                "severity": "high",
            },
        ],
        "overlooked_risks": [
            "Valuation multiple compression",
            "Margin or cash-flow conversion disappointment",
            "Competitive response stronger than expected",
        ],
        "consensus_check": "Check whether the thesis is variant on numbers, timing, or only narrative. Narrative-only variants are usually weaker.",
        "strongest_pushback": "The thesis needs proof that upside is not already embedded in consensus estimates and current valuation.",
        "thesis_echo": thesis[:500],
    }


def _parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start:end + 1]
    return json.loads(cleaned)


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


@router.post("/red-team")
async def red_team(req: RedTeamRequest) -> dict[str, Any]:
    ticker = req.ticker.strip().upper()
    thesis = req.thesis.strip()
    fallback = _fallback_red_team(ticker, thesis)
    api_key = req.api_key.strip()
    if not api_key:
        return fallback

    prompt = f"""
You are a skeptical short-seller reviewing an investment thesis.
Do not invent financial figures. Be concrete, adversarial, and useful.

TICKER: {ticker}
THESIS:
{thesis}

Return ONLY valid JSON in this shape:
{{
  "critiques": [
    {{
      "argument": "One-sentence critique",
      "evidence_needed": "What data would confirm or refute this",
      "severity": "high|medium|low"
    }}
  ],
  "overlooked_risks": ["risk 1", "risk 2"],
  "consensus_check": "Where this thesis aligns vs diverges from consensus",
  "strongest_pushback": "The single strongest argument against this thesis"
}}
""".strip()

    try:
        raw = await _call_gemini(api_key=api_key, prompt=prompt, max_tokens=1600, temperature=0.35)
        parsed = _parse_json_object(raw)
        return {
            "ticker": ticker,
            "source": "gemini",
            "critiques": parsed.get("critiques") if isinstance(parsed.get("critiques"), list) else fallback["critiques"],
            "overlooked_risks": parsed.get("overlooked_risks") if isinstance(parsed.get("overlooked_risks"), list) else fallback["overlooked_risks"],
            "consensus_check": parsed.get("consensus_check") or fallback["consensus_check"],
            "strongest_pushback": parsed.get("strongest_pushback") or fallback["strongest_pushback"],
        }
    except Exception:
        return fallback
