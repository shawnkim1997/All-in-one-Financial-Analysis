"""AI Analysis router -- Gemini-powered financial analysis.
Direct Gemini API calls without depending on Streamlit app module.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.models.schemas import AnomalyExplainRequest, AnomalyExplainResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalysisRequest(BaseModel):
    ticker: str
    question: str = ""
    api_key: str = ""
    sector: str = ""
    industry: str = ""


class SimpleQuestionRequest(BaseModel):
    ticker: str
    question: str
    api_key: str = ""


def _call_gemini(
    api_key: str,
    prompt: str,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Call Gemini API directly and return text response."""
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return "No response from Gemini."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("Gemini API error %d: %s", e.code, body)
        raise HTTPException(status_code=e.code, detail=f"Gemini API error: {body[:200]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini call failed: {e}")


def _build_anomaly_filing_context(
    ticker: str,
    email: str,
    filing_focus: str,
    display_name: str,
    account_key: str,
) -> str:
    from server.services.sec_parser import get_10k_sections
    from server.services.text_chunker import smart_chunk

    sections, _ = get_10k_sections(ticker.upper(), email.strip())
    focus = (filing_focus or "10k_mda").lower()
    if focus == "risk":
        raw = "\n\n".join(
            p
            for p in (
                sections.get("item1a", ""),
                sections.get("item9a", ""),
                sections.get("item3", ""),
            )
            if p
        )
    else:
        raw = sections.get("item7", "") or ""

    if not raw.strip():
        return ""

    hint = f"{display_name or ''} {account_key or ''}".strip()
    if hint:
        tokens = [t.lower() for t in re.split(r"[\s_/]+", hint) if len(t) > 2]
        if tokens:
            paras = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
            if not paras:
                paras = [raw]
            scored: List[tuple[int, str]] = []
            for para in paras:
                pl = para.lower()
                score = sum(1 for t in tokens if t in pl)
                scored.append((score, para))
            scored.sort(key=lambda x: (-x[0], -len(x[1])))
            priority = "\n\n".join(p for _, p in scored[:15])
            if priority.strip():
                raw = priority

    return smart_chunk(raw, max_chars=14000)


def _parse_llm_json_object(text: str) -> Dict[str, Any]:
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s)
    return json.loads(s)


def _anomaly_response_from_parsed(obj: Dict[str, Any]) -> AnomalyExplainResponse:
    cites = obj.get("citations") or []
    norm_cites: List[Dict[str, str]] = []
    if isinstance(cites, list):
        for c in cites:
            if isinstance(c, dict):
                norm_cites.append(
                    {
                        "excerpt": str(c.get("excerpt", ""))[:2000],
                        "context": str(c.get("context", ""))[:500],
                    }
                )
    causes = obj.get("likely_causes") or []
    if not isinstance(causes, list):
        causes = []
    conf = str(obj.get("confidence", "medium")).lower()
    if conf not in ("high", "medium", "low"):
        conf = "medium"
    return AnomalyExplainResponse(
        summary=str(obj.get("summary", ""))[:8000],
        likely_causes=[str(x) for x in causes][:20],
        citations=norm_cites[:15],
        confidence=conf,
    )


def _get_financial_context(ticker: str) -> str:
    """Build financial context from yfinance for AI analysis."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}
        ctx = f"""Company: {info.get('longName', ticker)} ({ticker})
Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}
Market Cap: ${info.get('marketCap', 0)/1e9:.1f}B
Revenue: ${info.get('totalRevenue', 0)/1e9:.1f}B | Revenue Growth: {(info.get('revenueGrowth', 0) or 0)*100:.1f}%
Profit Margin: {(info.get('profitMargins', 0) or 0)*100:.1f}% | Gross Margin: {(info.get('grossMargins', 0) or 0)*100:.1f}%
ROE: {(info.get('returnOnEquity', 0) or 0)*100:.1f}% | ROA: {(info.get('returnOnAssets', 0) or 0)*100:.1f}%
D/E: {info.get('debtToEquity', 'N/A')} | Current Ratio: {info.get('currentRatio', 'N/A')}
P/E: {info.get('trailingPE', 'N/A')} | Forward P/E: {info.get('forwardPE', 'N/A')}
Price: ${info.get('currentPrice', 'N/A')} | 52W High: ${info.get('fiftyTwoWeekHigh', 'N/A')} | 52W Low: ${info.get('fiftyTwoWeekLow', 'N/A')}
Target Mean: ${info.get('targetMeanPrice', 'N/A')} | Recommendation: {info.get('recommendationKey', 'N/A')}
Free Cash Flow: ${info.get('freeCashflow', 0)/1e9:.1f}B
"""
        return ctx
    except Exception:
        return f"Ticker: {ticker}"


@router.post("/strategy", summary="AI financial analysis")
async def strategy_analysis(req: AnalysisRequest):
    """General AI financial analysis using Gemini."""
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required. Set your Gemini key in Settings.")

    context = _get_financial_context(req.ticker.upper())
    question = req.question or f"Provide a comprehensive financial analysis of {req.ticker.upper()}"

    prompt = f"""You are an expert financial analyst. Analyze the following company and answer the user's question.

{context}

User Question: {question}

Provide a detailed, professional analysis in markdown format. Include:
- Key financial metrics assessment
- Strengths and weaknesses
- Valuation perspective
- Risk factors
- Your overall assessment

Be specific with numbers and data. Answer in the same language as the question."""

    result = _call_gemini(api_key, prompt)
    return {"ticker": req.ticker.upper(), "analysis": result}


@router.post("/risks", summary="Risk analysis")
async def risk_analysis(req: AnalysisRequest):
    """AI-powered risk analysis."""
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required.")

    context = _get_financial_context(req.ticker.upper())

    prompt = f"""You are a risk analyst. Analyze the following company's risk factors:

{context}

Provide a detailed risk assessment including:
1. Financial risks (leverage, liquidity, profitability trends)
2. Market risks (valuation, competition, sector headwinds)
3. Operational risks
4. Regulatory risks
5. Overall risk rating (Low/Medium/High)

Be specific and use the financial data provided. Answer in markdown format."""

    result = _call_gemini(api_key, prompt)
    return {"ticker": req.ticker.upper(), "analysis": result}


@router.post("/mda", summary="MD&A analysis")
async def mda_insights(req: AnalysisRequest):
    """AI management discussion analysis."""
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required.")

    context = _get_financial_context(req.ticker.upper())

    prompt = f"""Analyze the management perspective for this company:

{context}

Provide insights on:
1. Revenue drivers and growth strategy
2. Margin trends and cost management
3. Capital allocation priorities
4. Key management concerns
5. Future outlook

Use markdown format with headers and bullet points."""

    result = _call_gemini(api_key, prompt)
    return {"ticker": req.ticker.upper(), "report": result}


@router.post("/forensic", summary="Forensic audit")
async def forensic_audit(req: AnalysisRequest):
    """AI forensic audit analysis."""
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required.")

    context = _get_financial_context(req.ticker.upper())

    prompt = f"""Perform a forensic financial audit on this company:

{context}

Check for:
1. Earnings quality (cash flow vs net income)
2. Aggressive accounting signs
3. Related party transactions
4. Off-balance sheet items
5. Revenue recognition concerns
6. Management compensation alignment

Use markdown format. Be thorough but fair."""

    result = _call_gemini(api_key, prompt)
    return {"ticker": req.ticker.upper(), "forensic": result}


@router.post("/financials", summary="Extract financials via LLM")
async def extract_financials(req: AnalysisRequest):
    """Use Gemini to provide financial analysis."""
    api_key = req.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API key required.")

    context = _get_financial_context(req.ticker.upper())
    result = _call_gemini(api_key, f"Summarize the key financial data for analysis:\n\n{context}")
    return {"ticker": req.ticker.upper(), "financials": result}


@router.post(
    "/anomaly-explain",
    response_model=AnomalyExplainResponse,
    summary="Explain YoY anomaly from 10-K text (strict JSON)",
)
async def anomaly_explain(req: AnomalyExplainRequest):
    """Use Item 7 / risk sections plus Gemini to explain a flagged line item."""
    api_key = (req.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key required.")

    email = (req.sec_email or os.getenv("SEC_EDGAR_EMAIL") or "").strip()
    if not email:
        raise HTTPException(
            status_code=400,
            detail="SEC fair-access email required (pass sec_email or set SEC_EDGAR_EMAIL).",
        )

    try:
        ctx = _build_anomaly_filing_context(
            req.ticker,
            email,
            req.filing_focus,
            req.display_name,
            req.account_key,
        )
    except Exception as exc:
        logger.exception("anomaly-explain filing load failed")
        raise HTTPException(
            status_code=502,
            detail=f"Could not load SEC filing text: {exc}",
        ) from exc

    if not ctx:
        raise HTTPException(
            status_code=404,
            detail="No 10-K section text available for this ticker.",
        )

    mag = float(req.magnitude_pct or 0.0)
    dir_lbl = "increase" if (req.direction or "").lower() == "up" else "decrease"
    prompt = f"""You are a securities analyst. The user flagged a large year-over-year change in a financial statement line item (from automated screening — do not recompute numbers).

Ticker: {req.ticker.upper()}
Line item (account key): {req.account_key or "unknown"}
Display name: {req.display_name or "unknown"}
Direction: {dir_lbl} (approx. {mag:.1f}% YoY — context only).

Below is excerpted SEC filing text. Infer plausible qualitative explanations.

--- FILING EXCERPT ---
{ctx}
--- END EXCERPT ---

Output rules:
- Single JSON object only. No markdown, no code fences, no surrounding text.
- Do not invent new numerical results.
- Required JSON shape:
{{
  "summary": "2-4 sentences",
  "likely_causes": ["short strings"],
  "citations": [{{"excerpt": "quote from excerpt", "context": "Item 7 / Item 1A / etc."}}],
  "confidence": "high" | "medium" | "low"
}}
"""

    raw = ""
    try:
        raw = _call_gemini(api_key, prompt, max_tokens=2048, temperature=0.2)
        parsed = _parse_llm_json_object(raw)
        return _anomaly_response_from_parsed(parsed)
    except json.JSONDecodeError:
        return AnomalyExplainResponse(
            summary="The model returned non-JSON; raw output is attached in citations.",
            likely_causes=[],
            citations=[{"excerpt": (raw or "")[:1500], "context": "raw model output"}],
            confidence="low",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("anomaly-explain Gemini failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Translation endpoint
# ---------------------------------------------------------------------------

class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    target_lang: str = Field("ko", description="Target language code (ko, ja, zh, etc.)")
    api_key: str = ""


@router.post("/translate", summary="Translate filing text via Gemini")
async def translate_text(req: TranslateRequest):
    """Translate SEC/DART filing section text to the target language."""
    api_key = req.api_key or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key required")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text to translate")

    # Limit input to ~12,000 chars to stay within Gemini context
    if len(text) > 12_000:
        from server.services.text_chunker import smart_chunk
        text = smart_chunk(text, max_chars=12_000)

    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese (Simplified)",
        "es": "Spanish", "fr": "French", "de": "German",
    }
    lang_name = lang_names.get(req.target_lang, req.target_lang)

    prompt = (
        f"Translate the following SEC filing text to {lang_name}. "
        "Rules:\n"
        "- Preserve all numbers, financial figures, dates, and ticker symbols exactly as-is.\n"
        "- Keep technical financial terms (e.g., EBITDA, GAAP, P/E) in English.\n"
        "- Maintain paragraph structure and formatting.\n"
        "- Translate naturally, not word-for-word.\n\n"
        f"---\n{text}\n---"
    )

    try:
        result = _call_gemini(api_key, prompt, max_tokens=8192, temperature=0.2)
        return {"translated_text": result}
    except Exception as exc:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Institutional Analysis — Wall Street 10
# ---------------------------------------------------------------------------

class InstitutionalRequest(BaseModel):
    ticker: str
    api_key: str = ""
    lang: str = Field("en", description="Output language: en, ko, ja")


@router.post("/institutional", summary="Wall Street 10 institutional analysis")
async def institutional_analysis(req: InstitutionalRequest):
    """Generate comprehensive institutional-grade analysis from 10 Wall Street perspectives.

    Gathers all pre-computed quantitative data (DuPont, Altman Z, F-Score,
    DCF, anomalies, peers) and feeds them to Gemini for multi-perspective
    interpretation.  The LLM interprets numbers; it never computes them.
    """
    api_key = req.api_key or os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API key required. Set in Settings.")

    ticker = req.ticker.upper()

    # 1) Gather all quantitative data
    from server.services.institutional_report import (
        gather_quantitative_context,
        build_institutional_prompt,
    )
    try:
        context = gather_quantitative_context(ticker)
    except Exception as exc:
        logger.exception("Failed to gather quant context for %s", ticker)
        raise HTTPException(status_code=500, detail=f"Data gathering failed: {exc}") from exc

    if len(context) < 200:
        raise HTTPException(status_code=404, detail=f"Insufficient data for {ticker}")

    # Extract F-Score for prompt
    fscore = 0
    try:
        from server.services.research_dashboard import build_research_dashboard
        dash = build_research_dashboard(ticker)
        if dash:
            fscore = dash.fscore_total
    except Exception:
        pass

    # 2) Build prompt and call Gemini
    prompt = build_institutional_prompt(ticker, context, fscore)

    # Language instruction
    if req.lang == "ko":
        prompt += "\n\nIMPORTANT: Write the entire analysis in Korean (한국어). Keep financial terms (P/E, EBITDA, DCF, etc.) in English."
    elif req.lang == "ja":
        prompt += "\n\nIMPORTANT: Write the entire analysis in Japanese (日本語). Keep financial terms in English."

    try:
        raw = _call_gemini(api_key, prompt, max_tokens=8192, temperature=0.3)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gemini call failed: {exc}") from exc

    # 3) Parse JSON response
    try:
        parsed = _parse_llm_json_object(raw)
    except json.JSONDecodeError:
        # Return raw text as executive_summary if JSON parsing fails
        parsed = {
            "executive_summary": raw[:3000] if raw else "Analysis generation failed.",
            "goldman_sachs": "",
            "morgan_stanley": "",
            "jp_morgan": "",
            "blackrock": "",
            "bridgewater": "",
            "berkshire": "",
            "citadel": "",
            "two_sigma": "",
            "elliott": "",
        }

    return {
        "ticker": ticker,
        "sections": parsed,
        "quant_context": context,
    }
