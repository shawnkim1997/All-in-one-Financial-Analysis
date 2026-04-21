"""Korea Investment Securities provider placeholder.

KIS should become the first provider for Korean equities once credentials and
the concrete client are wired.  Keeping it as a provider now lets the chain
ordering and feature-flagged migration land without touching routers.
"""

from __future__ import annotations

import os

from server.core.providers.base import BaseProvider, ProviderNotConfigured


class KISProvider(BaseProvider):
    name = "kis"

    def supports_symbol(self, symbol: str) -> bool:
        normalized = symbol.strip().upper()
        return normalized.endswith(".KS") or normalized.endswith(".KQ") or normalized[:6].isdigit()

    def _configured(self) -> bool:
        return bool(os.getenv("KIS_APP_KEY") and os.getenv("KIS_APP_SECRET"))

    async def quote(self, symbol: str):  # type: ignore[no-untyped-def]
        if not self._configured():
            raise ProviderNotConfigured("KIS credentials are not set")
        raise ProviderNotConfigured("KIS client is not wired yet")
