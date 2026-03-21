"""Builds AI context from active widget data for the ATLAS Terminal chat."""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Widget-specific context templates
# ---------------------------------------------------------------------------

_DCF_TEMPLATE = """
## DCF Valuation Context
- Implied share price: ${implied_price:.2f}
- Current market price: ${current_price:.2f}
- Upside/Downside: {upside:+.1f}%
- WACC: {wacc:.1f}%
- Terminal growth rate: {terminal_growth:.1f}%
- FCF projections (5Y): {fcf_projections}
"""

_FINANCIALS_TEMPLATE = """
## Financial Metrics Context
- Revenue (TTM): ${revenue}
- Net income (TTM): ${net_income}
- Gross margin: {gross_margin:.1f}%
- Operating margin: {operating_margin:.1f}%
- ROE: {roe:.1f}%
- Debt/Equity: {debt_equity:.2f}
- Current ratio: {current_ratio:.2f}
"""

_TECHNICAL_TEMPLATE = """
## Technical Analysis Context
- RSI (14): {rsi:.1f}
- MACD: {macd:.4f} | Signal: {macd_signal:.4f}
- SMA 50: ${sma_50:.2f} | SMA 200: ${sma_200:.2f}
- 52-week high: ${high_52w:.2f} | Low: ${low_52w:.2f}
- Volume (avg 20d): {avg_volume}
"""

_PORTFOLIO_TEMPLATE = """
## Portfolio Context
- Total value: ${total_value:,.0f}
- Number of positions: {position_count}
- Top holdings: {top_holdings}
- Sector allocation: {sector_allocation}
"""

_FILING_TEMPLATE = """
## SEC Filing Context
- Latest filing type: {filing_type}
- Filed on: {filing_date}
- Key sections available: {sections}
"""

# ---------------------------------------------------------------------------
# Suggested questions per widget
# ---------------------------------------------------------------------------

_WIDGET_QUESTIONS: dict[str, list[str]] = {
    "dcf": [
        "Are the market's growth assumptions reasonable for this company?",
        "What would the fair value be with a higher discount rate?",
        "How sensitive is the valuation to terminal growth assumptions?",
    ],
    "financials": [
        "How do the margins compare to industry peers?",
        "Is the revenue growth trend sustainable?",
        "What are the key drivers behind the profitability changes?",
    ],
    "technical": [
        "What does the current technical setup suggest for the near term?",
        "Is the stock overbought or oversold based on RSI?",
        "Are there any notable divergences between price and momentum?",
    ],
    "portfolio": [
        "Is my sector diversification sufficient?",
        "Which positions carry the most concentration risk?",
        "How does my portfolio beta compare to the market?",
    ],
    "filing": [
        "What are the key risks disclosed in the latest filing?",
        "Are there any notable changes in accounting policies?",
        "What does management say about the competitive landscape?",
    ],
    "news": [
        "What is the overall sentiment of recent news?",
        "Are there any material events that could affect the stock?",
        "How might recent headlines impact the company's outlook?",
    ],
}

_DEFAULT_QUESTIONS: list[str] = [
    "Give me a quick overview of this company's financial health.",
    "What are the biggest risks facing this stock right now?",
    "Should I consider adding this to my portfolio? Why or why not?",
]


# ---------------------------------------------------------------------------
# ContextBuilder
# ---------------------------------------------------------------------------


class ContextBuilder:
    """Builds AI context from active widget data.

    The context is injected into the system prompt so the LLM can reference
    concrete numbers when answering the user's questions about a ticker.
    """

    def build_system_prompt(
        self,
        ticker: str,
        active_widgets: list[str],
        widget_data: dict[str, Any],
    ) -> str:
        """Build a context-aware system prompt.

        Args:
            ticker: The active ticker symbol (e.g. ``"AAPL"``).
            active_widgets: List of widget identifiers currently visible
                (e.g. ``["dcf", "financials", "technical"]``).
            widget_data: A dict keyed by widget name containing the data
                displayed in each widget.

        Returns:
            A system prompt string enriched with financial context.
        """
        sections: list[str] = [
            "You are ATLAS, an expert financial analyst assistant "
            "integrated into the ATLAS Terminal.\n"
            "You have direct access to the data the user is currently viewing.\n"
            "Answer concisely with concrete numbers when available. "
            "Use markdown formatting for readability.",
        ]

        # Always include base info if available
        base = widget_data.get("base", {})
        if ticker:
            sections.append(
                f"\n## Active Ticker: {ticker.upper()}\n"
                f"- Sector: {base.get('sector', 'N/A')}\n"
                f"- Current price: ${base.get('current_price', 'N/A')}\n"
                f"- Market cap: {base.get('market_cap', 'N/A')}\n"
            )

        # Append widget-specific context
        for widget in active_widgets:
            section = self._build_widget_section(widget, widget_data)
            if section:
                sections.append(section)

        return "\n".join(sections)

    def build_suggested_questions(
        self,
        active_widgets: list[str],
    ) -> list[str]:
        """Generate suggested questions based on active widgets.

        Args:
            active_widgets: List of widget identifiers currently visible.

        Returns:
            A list of 3-5 suggested question strings.
        """
        questions: list[str] = []

        for widget in active_widgets:
            widget_key = widget.lower().strip()
            if widget_key in _WIDGET_QUESTIONS:
                # Pick the first question from each active widget
                questions.append(_WIDGET_QUESTIONS[widget_key][0])

        # Pad with defaults if we have fewer than 3
        for q in _DEFAULT_QUESTIONS:
            if len(questions) >= 5:
                break
            if q not in questions:
                questions.append(q)

        return questions[:5]

    # -- private helpers ----------------------------------------------------

    def _build_widget_section(
        self, widget: str, widget_data: dict[str, Any]
    ) -> str:
        """Render context section for a specific widget.

        Returns an empty string when no data is available for the widget.
        """
        widget_key = widget.lower().strip()
        data = widget_data.get(widget_key, {})

        if not data:
            return ""

        try:
            if widget_key == "dcf":
                return _DCF_TEMPLATE.format(**data)
            if widget_key == "financials":
                return _FINANCIALS_TEMPLATE.format(**data)
            if widget_key == "technical":
                return _TECHNICAL_TEMPLATE.format(**data)
            if widget_key == "portfolio":
                return _PORTFOLIO_TEMPLATE.format(**data)
            if widget_key == "filing":
                return _FILING_TEMPLATE.format(**data)
        except (KeyError, ValueError, TypeError) as exc:
            # Gracefully degrade -- partial data is fine
            return f"\n## {widget.title()} Context\nPartial data: {data}\n"

        # Unknown widget -- dump raw data as a summary
        return f"\n## {widget.title()} Context\n{data}\n"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
context_builder = ContextBuilder()
