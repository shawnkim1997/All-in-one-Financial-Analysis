"""Unified Multi-LLM router supporting Gemini, Claude, and OpenAI."""

from __future__ import annotations

import asyncio
import logging
from enum import Enum
from typing import AsyncGenerator, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.0-flash",
    "claude": "claude-sonnet-4-20250514",
    "openai": "gpt-4o-mini",
}


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"


class LLMConfig(BaseModel):
    """Configuration for a single LLM request."""

    provider: LLMProvider
    model: str = ""
    api_key: str = ""
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128_000)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class LLMRouter:
    """Routes requests to the appropriate LLM provider.

    Register API keys via ``configure()``, then call ``generate()`` or
    ``stream()`` with an optional ``LLMConfig``.  When no config is given the
    router auto-selects a provider based on prompt length:

    * < 5 000 chars  -> Gemini (fast)
    * > 10 000 chars -> Claude (long-context)
    * fallback       -> OpenAI
    """

    def __init__(self) -> None:
        self._providers: dict[LLMProvider, str] = {}

    # -- configuration ------------------------------------------------------

    def configure(self, provider: LLMProvider, api_key: str) -> None:
        """Register an API key for *provider*."""
        self._providers[provider] = api_key
        logger.info("LLM provider configured: %s", provider.value)

    def get_available_providers(self) -> list[LLMProvider]:
        """Return the list of providers that have an API key configured."""
        return list(self._providers.keys())

    # -- public interface ---------------------------------------------------

    def _resolve_config(
        self, prompt: str, config: Optional[LLMConfig]
    ) -> LLMConfig:
        """Return a fully-resolved ``LLMConfig``.

        If *config* is ``None`` the provider is auto-selected based on prompt
        length and available keys.
        """
        if config is not None:
            resolved = config.model_copy()
            if not resolved.api_key:
                resolved.api_key = self._providers.get(resolved.provider, "")
            if not resolved.model:
                resolved.model = DEFAULT_MODELS.get(resolved.provider.value, "")
            return resolved

        provider = self._auto_select_provider(prompt)
        return LLMConfig(
            provider=provider,
            model=DEFAULT_MODELS[provider.value],
            api_key=self._providers.get(provider, ""),
        )

    def _auto_select_provider(self, prompt: str) -> LLMProvider:
        """Pick the best available provider for *prompt*."""
        length = len(prompt)

        if length < 5_000 and LLMProvider.GEMINI in self._providers:
            return LLMProvider.GEMINI
        if length > 10_000 and LLMProvider.CLAUDE in self._providers:
            return LLMProvider.CLAUDE
        if LLMProvider.OPENAI in self._providers:
            return LLMProvider.OPENAI

        # Fallback: use whatever is available
        for p in (LLMProvider.GEMINI, LLMProvider.CLAUDE, LLMProvider.OPENAI):
            if p in self._providers:
                return p

        raise RuntimeError("No LLM provider configured. Call configure() first.")

    async def generate(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        system_prompt: str = "",
    ) -> str:
        """Generate a complete response from the best available LLM."""
        cfg = self._resolve_config(prompt, config)
        dispatch = {
            LLMProvider.GEMINI: self._gemini_generate,
            LLMProvider.CLAUDE: self._claude_generate,
            LLMProvider.OPENAI: self._openai_generate,
        }
        handler = dispatch[cfg.provider]
        return await handler(
            prompt, system_prompt, cfg.model, cfg.api_key,
            cfg.temperature, cfg.max_tokens,
        )

    async def stream(
        self,
        prompt: str,
        config: Optional[LLMConfig] = None,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks from the LLM."""
        cfg = self._resolve_config(prompt, config)
        dispatch = {
            LLMProvider.GEMINI: self._gemini_stream,
            LLMProvider.CLAUDE: self._claude_stream,
            LLMProvider.OPENAI: self._openai_stream,
        }
        handler = dispatch[cfg.provider]
        async for chunk in handler(
            prompt, system_prompt, cfg.model, cfg.api_key,
            cfg.temperature, cfg.max_tokens,
        ):
            yield chunk

    # -- Gemini -------------------------------------------------------------

    async def _gemini_generate(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> str:
        """Call Google Gemini API (non-streaming)."""
        try:
            import google.generativeai as genai  # lazy import
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system or None,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        response = await asyncio.to_thread(
            gen_model.generate_content, prompt,
        )
        return response.text

    async def _gemini_stream(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Call Google Gemini API (streaming)."""
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise RuntimeError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            ) from exc

        genai.configure(api_key=api_key)
        gen_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=system or None,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        response = await asyncio.to_thread(
            gen_model.generate_content, prompt, stream=True,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    # -- Claude -------------------------------------------------------------

    async def _claude_generate(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> str:
        """Call Anthropic Claude API (non-streaming)."""
        try:
            import anthropic  # lazy import
        except ImportError as exc:
            raise RuntimeError(
                "anthropic is not installed. Run: pip install anthropic"
            ) from exc

        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are a helpful financial analyst.",
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def _claude_stream(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Call Anthropic Claude API (streaming)."""
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic is not installed. Run: pip install anthropic"
            ) from exc

        client = anthropic.AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "You are a helpful financial analyst.",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # -- OpenAI -------------------------------------------------------------

    async def _openai_generate(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> str:
        """Call OpenAI API (non-streaming)."""
        try:
            import openai  # lazy import
        except ImportError as exc:
            raise RuntimeError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        client = openai.AsyncOpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return choice.message.content or ""

    async def _openai_stream(
        self, prompt: str, system: str, model: str,
        api_key: str, temperature: float, max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """Call OpenAI API (streaming)."""
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError(
                "openai is not installed. Run: pip install openai"
            ) from exc

        client = openai.AsyncOpenAI(api_key=api_key)
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
llm_router = LLMRouter()
