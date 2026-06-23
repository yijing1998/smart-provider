"""Concurrency tests for Smart-Provider.

These tests verify that Smart-Provider respects RPM limits and queue
semantics when multiple HTTP clients send requests concurrently.
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient

from src.config import Config
from src.forwarder import Forwarder, ForwardResult
from src.ingress.app import create_app
from src.ingress.context import RequestContext
from src.observability import MetricsCollector


class RecordingForwarder(Forwarder):
    """Forwarder that records the exact time each upstream call is made."""

    def __init__(self) -> None:
        self.call_times: list[float] = []
        self._lock = asyncio.Lock()

    async def forward_async(self, context: RequestContext) -> ForwardResult:
        async with self._lock:
            self.call_times.append(time.perf_counter())
        return ForwardResult(
            status_code=200,
            body={
                "id": context.request_id,
                "object": "chat.completion",
                "model": context.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    async def stream_async(
        self, context: RequestContext
    ) -> AsyncIterator[dict[str, Any]]:
        async with self._lock:
            self.call_times.append(time.perf_counter())
        yield {
            "id": context.request_id,
            "object": "chat.completion.chunk",
            "model": context.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "pong"},
                    "finish_reason": None,
                }
            ],
        }
        yield {
            "id": context.request_id,
            "object": "chat.completion.chunk",
            "model": context.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }


@asynccontextmanager
async def _app_client(app: FastAPI):
    """Wrap an ASGI app with lifespan management and an async HTTP client."""
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client


def _assert_rpm_respected(
    call_times: list[float], rpm: int, window_seconds: float
) -> None:
    """Assert that no sliding window contains more than ``rpm`` calls."""
    for start in call_times:
        count = sum(
            1 for t in call_times if start <= t < start + window_seconds
        )
        assert count <= rpm, (
            f"Window [{start:.3f}, {start + window_seconds:.3f}) "
            f"contains {count} calls, exceeding rpm={rpm}"
        )


def _make_config(
    *,
    rpm: int,
    queue_max_size: int = 1000,
    queue_max_wait_ms: int = 30000,
    window_seconds: int = 1,
) -> Config:
    """Create a Config tuned for fast concurrency tests."""
    return Config(
        upstream_url="https://example.com/v1",
        rate_limit_rpm=rpm,
        rate_limit_window_seconds=window_seconds,
        queue_max_size=queue_max_size,
        queue_max_wait_ms=queue_max_wait_ms,
        observability_metrics_enabled=False,
        forwarder_timeout_ms=5000,
        forwarder_max_retries=0,
    )


@pytest.fixture
async def reset_metrics() -> None:
    """Reset metrics before and after each concurrency test."""
    await MetricsCollector().reset()
    yield
    await MetricsCollector().reset()


@pytest.mark.asyncio
@pytest.mark.slow
async def test_burst_requests_respect_rpm(reset_metrics) -> None:
    """Concurrent burst must not exceed RPM in any sliding window."""
    rpm = 5
    window_seconds = 1
    total_requests = 20
    forwarder = RecordingForwarder()
    config = _make_config(rpm=rpm, window_seconds=window_seconds)
    app = create_app(config=config, forwarder=forwarder)

    async with _app_client(app) as client:
        tasks = [
            client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            for _ in range(total_requests)
        ]
        responses = await asyncio.gather(*tasks)

    assert all(r.status_code == 200 for r in responses)
    assert len(forwarder.call_times) == total_requests
    _assert_rpm_respected(forwarder.call_times, rpm, window_seconds)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_sustained_load_maintains_rpm(reset_metrics) -> None:
    """Steady stream of requests stays within RPM over time."""
    rpm = 10
    window_seconds = 1
    total_requests = 100
    send_interval = 0.1  # 10 requests per second
    forwarder = RecordingForwarder()
    config = _make_config(rpm=rpm, window_seconds=window_seconds)
    app = create_app(config=config, forwarder=forwarder)

    async with _app_client(app) as client:
        responses = []
        for _ in range(total_requests):
            responses.append(
                await client.post(
                    "/v1/chat/completions",
                    json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
                )
            )
            await asyncio.sleep(send_interval)

    assert all(r.status_code == 200 for r in responses)
    assert len(forwarder.call_times) == total_requests
    _assert_rpm_respected(forwarder.call_times, rpm, window_seconds)


@pytest.mark.asyncio
async def test_concurrent_burst_fills_queue_and_rejects(reset_metrics) -> None:
    """When the queue is full, concurrent excess requests get 503."""
    rpm = 1
    queue_max_size = 5
    total_requests = 20
    forwarder = RecordingForwarder()
    config = _make_config(
        rpm=rpm,
        queue_max_size=queue_max_size,
        queue_max_wait_ms=5000,
    )
    app = create_app(config=config, forwarder=forwarder)

    async with _app_client(app) as client:
        tasks = [
            client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            for _ in range(total_requests)
        ]
        responses = await asyncio.gather(*tasks)

    success_count = sum(1 for r in responses if r.status_code == 200)
    rejected_count = sum(1 for r in responses if r.status_code == 503)

    assert success_count == queue_max_size
    assert rejected_count == total_requests - queue_max_size
    assert len(forwarder.call_times) == queue_max_size


@pytest.mark.asyncio
async def test_concurrent_requests_timeout_in_queue(reset_metrics) -> None:
    """Requests waiting too long in a congested queue return 504."""
    rpm = 1
    total_requests = 5
    max_wait_ms = 200
    forwarder = RecordingForwarder()
    config = _make_config(
        rpm=rpm,
        queue_max_size=total_requests,
        queue_max_wait_ms=max_wait_ms,
    )
    app = create_app(config=config, forwarder=forwarder)

    async with _app_client(app) as client:
        tasks = [
            client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            for _ in range(total_requests)
        ]
        responses = await asyncio.gather(*tasks)

    success_count = sum(1 for r in responses if r.status_code == 200)
    timeout_count = sum(1 for r in responses if r.status_code == 504)

    assert success_count == 1
    assert timeout_count == total_requests - 1


@pytest.mark.asyncio
@pytest.mark.slow
async def test_mixed_streaming_and_non_streaming_respect_rpm(
    reset_metrics,
) -> None:
    """Streaming and non-streaming requests share the same RPM budget."""
    rpm = 5
    window_seconds = 1
    streaming_requests = 3
    non_streaming_requests = 7
    total_requests = streaming_requests + non_streaming_requests
    forwarder = RecordingForwarder()
    config = _make_config(rpm=rpm, window_seconds=window_seconds)
    app = create_app(config=config, forwarder=forwarder)

    async with _app_client(app) as client:
        tasks = []
        for _ in range(non_streaming_requests):
            tasks.append(
                client.post(
                    "/v1/chat/completions",
                    json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
                )
            )
        for _ in range(streaming_requests):
            tasks.append(
                client.post(
                    "/v1/chat/completions",
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": "hi"}],
                        "stream": True,
                    },
                )
            )
        responses = await asyncio.gather(*tasks)

    assert all(r.status_code == 200 for r in responses)
    assert len(forwarder.call_times) == total_requests
    _assert_rpm_respected(forwarder.call_times, rpm, window_seconds)
