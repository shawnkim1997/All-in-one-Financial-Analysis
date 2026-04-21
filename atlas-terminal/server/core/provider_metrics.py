"""In-process provider counters for Data Gateway migration measurements."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderMetricRow:
    provider: str
    method: str
    attempts: int
    successes: int
    failures: int


class ProviderMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._attempts: defaultdict[tuple[str, str], int] = defaultdict(int)
        self._successes: defaultdict[tuple[str, str], int] = defaultdict(int)
        self._failures: defaultdict[tuple[str, str], int] = defaultdict(int)

    def record_attempt(self, provider: str, method: str) -> None:
        with self._lock:
            self._attempts[(provider, method)] += 1

    def record_success(self, provider: str, method: str) -> None:
        with self._lock:
            self._successes[(provider, method)] += 1

    def record_failure(self, provider: str, method: str) -> None:
        with self._lock:
            self._failures[(provider, method)] += 1

    def snapshot(self) -> list[ProviderMetricRow]:
        with self._lock:
            keys = set(self._attempts) | set(self._successes) | set(self._failures)
            return [
                ProviderMetricRow(
                    provider=provider,
                    method=method,
                    attempts=self._attempts[(provider, method)],
                    successes=self._successes[(provider, method)],
                    failures=self._failures[(provider, method)],
                )
                for provider, method in sorted(keys)
            ]

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()
            self._successes.clear()
            self._failures.clear()


provider_metrics = ProviderMetrics()
