"""In-memory metrics collector for Smart-Provider with Prometheus export."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


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
    and upstream error classifications. It also exposes the same metrics in
    Prometheus format through a dedicated registry.
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
            cls._instance._registry = CollectorRegistry()
            cls._instance._init_prometheus_metrics()
        return cls._instance

    def _init_prometheus_metrics(self) -> None:
        """Create Prometheus metrics in the dedicated registry."""
        self._prom_queue_size = Gauge(
            "smart_provider_queue_size",
            "Current number of requests in the queue",
            registry=self._registry,
        )
        self._prom_requests_enqueued_total = Counter(
            "smart_provider_requests_enqueued_total",
            "Total number of requests accepted into the queue",
            registry=self._registry,
        )
        self._prom_requests_processed_total = Counter(
            "smart_provider_requests_processed_total",
            "Total number of requests dequeued for processing",
            registry=self._registry,
        )
        self._prom_upstream_429_total = Counter(
            "smart_provider_upstream_429_total",
            "Total number of upstream 429 responses",
            registry=self._registry,
        )
        self._prom_upstream_5xx_total = Counter(
            "smart_provider_upstream_5xx_total",
            "Total number of upstream 5xx or connection errors",
            registry=self._registry,
        )
        self._prom_circuit_breaker_state = Gauge(
            "smart_provider_circuit_breaker_state",
            "Current circuit breaker state (0=closed, 1=half_open, 2=open)",
            registry=self._registry,
        )
        self._prom_circuit_breaker_opens_total = Counter(
            "smart_provider_circuit_breaker_opens_total",
            "Total number of times the circuit breaker has opened",
            registry=self._registry,
        )
        self._prom_streams_started_total = Counter(
            "smart_provider_streams_started_total",
            "Total number of streaming requests accepted",
            registry=self._registry,
        )
        self._prom_streams_completed_total = Counter(
            "smart_provider_streams_completed_total",
            "Total number of streaming requests completed or failed",
            registry=self._registry,
        )
        buckets = [
            0.001,
            0.005,
            0.01,
            0.025,
            0.05,
            0.1,
            0.25,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
        ]
        self._prom_queue_wait_duration_seconds = Histogram(
            "smart_provider_queue_wait_duration_seconds",
            "Time requests spend waiting in the queue",
            buckets=buckets,
            registry=self._registry,
        )
        self._prom_request_duration_seconds = Histogram(
            "smart_provider_request_duration_seconds",
            "Total time from enqueue to response return",
            buckets=buckets,
            registry=self._registry,
        )
        self._prom_forward_duration_seconds = Histogram(
            "smart_provider_forward_duration_seconds",
            "Time spent calling the upstream API",
            buckets=buckets,
            registry=self._registry,
        )

    async def record_enqueue(self) -> None:
        """Record that a request was accepted into the queue."""
        async with self._mutex:
            self._queue_size += 1
            self._requests_enqueued_total += 1
            self._prom_queue_size.set(self._queue_size)
            self._prom_requests_enqueued_total.inc()

    async def record_dequeue(self, wait_ms: float) -> None:
        """Record that a request left the queue and entered forwarding."""
        async with self._mutex:
            self._queue_size = max(0, self._queue_size - 1)
            self._requests_processed_total += 1
            self._wait_time_stats.record(wait_ms)
            self._prom_queue_size.set(self._queue_size)
            self._prom_requests_processed_total.inc()
            self._prom_queue_wait_duration_seconds.observe(wait_ms / 1000.0)

    async def record_upstream_429(self) -> None:
        """Record an upstream 429 Too Many Requests response."""
        async with self._mutex:
            self._upstream_429_total += 1
            self._prom_upstream_429_total.inc()

    async def record_upstream_5xx(self) -> None:
        """Record an upstream 5xx or connection-level error."""
        async with self._mutex:
            self._upstream_5xx_total += 1
            self._prom_upstream_5xx_total.inc()

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
            numeric_state = {"closed": 0, "half_open": 1, "open": 2}.get(
                state.lower(), 0
            )
            self._prom_circuit_breaker_state.set(numeric_state)
            if opened:
                self._circuit_breaker_opens_total += 1
                self._prom_circuit_breaker_opens_total.inc()

    async def record_stream_started(self) -> None:
        """Record that a streaming request was accepted into the queue."""
        async with self._mutex:
            self._streams_started_total += 1
            self._prom_streams_started_total.inc()

    async def record_stream_completed(self) -> None:
        """Record that a streaming request finished or failed."""
        async with self._mutex:
            self._streams_completed_total += 1
            self._prom_streams_completed_total.inc()

    async def record_request_duration(self, duration_seconds: float) -> None:
        """Record the total duration from enqueue to response return."""
        async with self._mutex:
            self._prom_request_duration_seconds.observe(duration_seconds)

    async def record_forward_duration(self, duration_seconds: float) -> None:
        """Record the duration of an upstream API call."""
        async with self._mutex:
            self._prom_forward_duration_seconds.observe(duration_seconds)

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

    def prometheus_metrics(self) -> bytes:
        """Return the current metrics in Prometheus exposition format."""
        return generate_latest(self._registry)

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
            self._reset_prometheus_metrics()

    def _reset_prometheus_metrics(self) -> None:
        """Reset Prometheus metric values to zero."""
        self._prom_queue_size.set(0)
        self._prom_requests_enqueued_total._value.set(0)
        self._prom_requests_processed_total._value.set(0)
        self._prom_upstream_429_total._value.set(0)
        self._prom_upstream_5xx_total._value.set(0)
        self._prom_circuit_breaker_state.set(0)
        self._prom_circuit_breaker_opens_total._value.set(0)
        self._prom_streams_started_total._value.set(0)
        self._prom_streams_completed_total._value.set(0)
        for histogram in (
            self._prom_queue_wait_duration_seconds,
            self._prom_request_duration_seconds,
            self._prom_forward_duration_seconds,
        ):
            histogram._sum.set(0)
            for sample in histogram._buckets:
                sample.set(0)
