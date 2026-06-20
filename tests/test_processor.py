"""Tests for the Smart-Provider request processing pipeline."""

import asyncio
import time

import pytest
from litellm.exceptions import Timeout

from src.config.schema import LimiterConfig
from src.forwarder import ForwardResult, Forwarder, StubForwarder
from src.ingress.context import RequestContext
from src.limiter import SlidingWindowRateLimiter
from src.observability import MetricsCollector
from src.processor import RequestProcessor
from src.queue import RequestQueue


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    """Reset the singleton metrics collector before each test."""
    asyncio.run(MetricsCollector().reset())


def _context(max_wait_time_ms: int = 30000) -> RequestContext:
    return RequestContext(
        model="gpt-4o",
        messages=[{"role": "user", "content": "hello"}],
        max_wait_time_ms=max_wait_time_ms,
    )


def _make_processor(
    rpm: int = 1000,
    window_seconds: int = 1,
    forwarder: Forwarder | None = None,
) -> RequestProcessor:
    queue = RequestQueue(max_size=10)
    limiter = SlidingWindowRateLimiter(
        LimiterConfig(rpm=rpm, window_seconds=window_seconds)
    )
    return RequestProcessor(
        queue=queue,
        limiter=limiter,
        forwarder=forwarder or StubForwarder(),
    )


class TestRequestProcessorLifecycle:
    """Verify start/stop behavior."""

    def test_start_creates_worker_task(self):
        processor = _make_processor()
        asyncio.run(processor.start())
        assert processor._task is not None
        asyncio.run(processor.stop())

    def test_stop_cancels_worker_task(self):
        processor = _make_processor()
        asyncio.run(processor.start())
        asyncio.run(processor.stop())
        assert processor._task is None


class TestRequestProcessorSubmission:
    """Verify Future-based result propagation."""

    def test_successful_result_is_returned(self):
        processor = _make_processor()

        async def run() -> ForwardResult:
            await processor.start()
            try:
                future = await processor.submit(_context())
                return await asyncio.wait_for(future, timeout=1.0)
            finally:
                await processor.stop()

        result = asyncio.run(run())
        assert result.status_code == 200
        assert result.body["choices"][0]["message"]["content"] == "pong"

    def test_forwarder_error_is_propagated(self):
        class FailingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                return ForwardResult(status_code=0, body=None, error="boom")

        processor = _make_processor(forwarder=FailingForwarder())

        async def run() -> ForwardResult:
            await processor.start()
            try:
                future = await processor.submit(_context())
                return await asyncio.wait_for(future, timeout=1.0)
            finally:
                await processor.stop()

        result = asyncio.run(run())
        assert result.error == "boom"


class TestRequestProcessorRateLimiting:
    """Verify that the processor respects the rate limiter."""

    def test_multiple_requests_are_throttled(self):
        rpm = 1
        window_seconds = 1
        processor = _make_processor(rpm=rpm, window_seconds=window_seconds)
        completion_times: dict[str, float] = {}

        async def submit_and_record(request_id: str) -> None:
            context = RequestContext(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hello"}],
                max_wait_time_ms=10000,
            )
            future = await processor.submit(context)
            await future
            completion_times[request_id] = time.monotonic()

        async def run() -> None:
            await processor.start()
            try:
                await asyncio.gather(
                    submit_and_record("a"),
                    submit_and_record("b"),
                    submit_and_record("c"),
                )
            finally:
                await processor.stop()

        asyncio.run(run())

        sorted_times = sorted(completion_times.values())
        tolerance = 0.05
        for i in range(1, len(sorted_times)):
            assert sorted_times[i] - sorted_times[i - 1] >= window_seconds - tolerance


class TestRequestProcessorWaitTimeout:
    """Verify requests that wait too long in the queue time out."""

    def test_queue_wait_timeout_returns_timeout(self):
        class DelayedQueue(RequestQueue):
            """A queue that delays dequeue so the wait timeout can trigger."""

            def __init__(self, delay: float, max_size: int = 10) -> None:
                super().__init__(max_size=max_size)
                self._delay = delay

            async def dequeue(self) -> RequestContext:
                await asyncio.sleep(self._delay)
                return await super().dequeue()

        queue = DelayedQueue(delay=0.2, max_size=10)
        limiter = SlidingWindowRateLimiter(
            LimiterConfig(rpm=1000, window_seconds=1)
        )
        processor = RequestProcessor(
            queue=queue,
            limiter=limiter,
            forwarder=StubForwarder(),
        )

        async def run() -> None:
            await processor.start()
            try:
                future = await processor.submit(_context(max_wait_time_ms=50))
                with pytest.raises(Timeout):
                    await asyncio.wait_for(future, timeout=1.0)
            finally:
                await processor.stop()

        asyncio.run(run())
