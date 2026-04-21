"""Server-side feature flags for staged refactors."""

from __future__ import annotations

import os


def _enabled(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def new_data_gateway_enabled() -> bool:
    """Gate router migrations onto the v2 Data Gateway."""

    return _enabled("ATLAS_FLAG_GATEWAY")
