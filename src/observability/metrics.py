"""In-memory metrics collector for Smart-Provider."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass
class _WaitTimeStats:
    """Aggregate statistics for queue wait times."""

    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def record(self, wait_ms: float) -> None:
        self.count += 1
        self.total_ms += wait_ms
        if wait_ms > self.max_ms:
            self.max_ms = wait_ms

    def to_dict(self) -> dict[str, float]:
        return {
            "count": self.count,
            "total_ms": self.total_ms,
            "max_ms": self.max_ms,
            "avg_ms": self.total_ms / self.count if self.count else 0.0,
        }

    def reset(self) -> None:
        self.count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0


class MetricsCollector:
    """Async-safe singleton collector for runtime metrics.

    The collector maintains counters for the queue state, processed requests,
    and upstream error classifications. It is intentionally simple and
    in-memory; external persistence or Prometheus export can be added later.
    """

    _instance: MetricsCollector | None = None

    def __new__(cls) -> MetricsCollector:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._queue_size = 0
            cls._instance._requests_enqueued_total = 0
            cls._instance._requests_processed_total = 0
            cls._instance._upstream_429_total = 0
            cls._instance._upstream_5xx_total = 0
            cls._instance._wait_time_stats = _WaitTimeStats()
            cls._instance._circuit_breaker_state = "closed"
            cls._instance._circuit_breaker_opens_total = 0
            cls._instance._streams_started_total = 0
            cls._instance._streams_completed_total = 0
            cls._instance._mutex = asyncio.Lock()
        return cls._instance

    async def record_enqueue(self) -> None:
        """Record that a request was accepted into the queue."""
        async with self._mutex:
            self._queue_size += 1
            self._requests_enqueued_total += 1

    async def record_dequeue(self, wait_ms: float) -> None:
        """Record that a request left the queue and entered forwarding."""
        async with self._mutex:
            self._queue_size = max(0, self._queue_size - 1)
            self._requests_processed_total += 1
            self._wait_time_stats.record(wait_ms)

    async def record_upstream_429(self) -> None:
        """Record an upstream 429 Too Many Requests response."""
        async with self._mutex:
            self._upstream_429_total += 1

    async def record_upstream_5xx(self) -> None:
        """Record an upstream 5xx or connection-level error."""
        async with self._mutex:
            self._upstream_5xx_total += 1

    async def record_circuit_breaker_state(
        self, state: str, opened: bool = False
    ) -> None:
        """Record the current circuit breaker state.

        Args:
            state: One of "closed", "open", or "half_open".
            opened: True when the breaker transitions to OPEN, so the cumulative
                open counter can be incremented.
        """
        async with self._mutex:
            self._circuit_breaker_state = state
            if opened:
                self._circuit_breaker_opens_total += 1

    async def record_stream_started(self) -> None:
        """Record that a streaming request was accepted into the queue."""
        async with self._mutex:
            self._streams_started_total += 1

    async def record_stream_completed(self) -> None:
        """Record that a streaming request finished or failed."""
        async with self._mutex:
            self._streams_completed_total += 1

    async def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the current metrics."""
        async with self._mutex:
            return {
                "queue_size": self._queue_size,
                "requests_enqueued_total": self._requests_enqueued_total,
                "requests_processed_total": self._requests_processed_total,
                "upstream_429_total": self._upstream_429_total,
                "upstream_5xx_total": self._upstream_5xx_total,
                "wait_time_ms": self._wait_time_stats.to_dict(),
                "circuit_breaker_state": self._circuit_breaker_state,
                "circuit_breaker_opens_total": self._circuit_breaker_opens_total,
                "streams_started_total": self._streams_started_total,
                "streams_completed_total": self._streams_completed_total,
            }

    async def reset(self) -> None:
        """Reset all metrics to zero. Useful for tests."""
        async with self._mutex:
            self._queue_size = 0
            self._requests_enqueued_total = 0
            self._requests_processed_total = 0
            self._upstream_429_total = 0
            self._upstream_5xx_total = 0
            self._wait_time_stats.reset()
            self._circuit_breaker_state = "closed"
            self._circuit_breaker_opens_total = 0
            self._streams_started_total = 0
            self._streams_completed_total = 0
