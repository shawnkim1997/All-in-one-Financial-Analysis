"""Simple in-memory TTL cache for expensive macro data fetches."""

from __future__ import annotations

import time
import threading
from typing import Any, Callable, TypeVar

_lock = threading.Lock()
_store: dict[str, tuple[float, Any]] = {}

F = TypeVar("F", bound=Callable)


def cached(key: str, ttl_seconds: int = 3600):
    """Decorator that caches a function result for *ttl_seconds*."""
    def decorator(fn: Callable) -> Callable:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            now = time.time()
            with _lock:
                if key in _store:
                    ts, val = _store[key]
                    if now - ts < ttl_seconds:
                        return val
            result = fn(*args, **kwargs)
            with _lock:
                _store[key] = (now, result)
            return result
        return wrapper
    return decorator


def invalidate(key: str) -> None:
    with _lock:
        _store.pop(key, None)


def invalidate_all() -> None:
    with _lock:
        _store.clear()
