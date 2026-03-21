"""AI Analysis router -- Gemini-powered financial analysis.
Direct Gemini API calls without depending on Streamlit app module.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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


def _call_gemini(api_key: str, prompt: str, max_tokens: int = 4096) -> str:
    """Call Gemini API directly and return text response."""
    import urllib.request
    import urllib.error

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
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
