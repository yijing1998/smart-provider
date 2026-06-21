"""Tests for the Smart-Provider request processing pipeline."""

import asyncio
import time

import pytest
from litellm.exceptions import ServiceUnavailableError, Timeout

from src.circuit_breaker import CircuitBreaker
from src.config.schema import CircuitBreakerConfig, LimiterConfig
from src.forwarder import ForwardResult, Forwarder, StubForwarder
from src.ingress.context import RequestContext
from src.limiter import SlidingWindowRateLimiter
from src.observability import MetricsCollector
from src.processor import RequestProcessor
from src.queue import RequestQueue
from src.shutdown import ShutdownManager


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
    circuit_breaker: CircuitBreaker | None = None,
    shutdown_manager: ShutdownManager | None = None,
) -> RequestProcessor:
    queue = RequestQueue(max_size=10)
    limiter = SlidingWindowRateLimiter(
        LimiterConfig(rpm=rpm, window_seconds=window_seconds)
    )
    return RequestProcessor(
        queue=queue,
        limiter=limiter,
        forwarder=forwarder or StubForwarder(),
        circuit_breaker=circuit_breaker,
        shutdown_manager=shutdown_manager,
    )


def _make_circuit_breaker(
    threshold: int = 3,
    recovery_timeout_ms: int = 1000,
    clock=None,
) -> CircuitBreaker:
    config = CircuitBreakerConfig(
        enabled=True,
        failure_threshold=threshold,
        recovery_timeout_ms=recovery_timeout_ms,
    )
    return CircuitBreaker(config, clock=clock or (lambda: 0.0))


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

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

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


class TestRequestProcessorCircuitBreaker:
    """Verify circuit breaker integration in the processor."""

    def test_open_breaker_rejects_request_fast(self):
        class FailingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                raise ServiceUnavailableError(
                    message="upstream down",
                    llm_provider="openai",
                    model="gpt-4o",
                )

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

        breaker = _make_circuit_breaker(threshold=1, recovery_timeout_ms=5000)
        processor = _make_processor(
            forwarder=FailingForwarder(), circuit_breaker=breaker
        )

        async def run() -> None:
            await processor.start()
            try:
                # First request fails and opens the breaker.
                future1 = await processor.submit(_context())
                with pytest.raises(ServiceUnavailableError):
                    await asyncio.wait_for(future1, timeout=1.0)
                assert breaker.state.name == "OPEN"

                # Second request should fail fast without calling the forwarder.
                future2 = await processor.submit(_context())
                with pytest.raises(ServiceUnavailableError) as exc_info:
                    await asyncio.wait_for(future2, timeout=1.0)
                assert "circuit breaker is open" in str(exc_info.value).lower()
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_half_open_probe_recovery(self):
        current_time = 0.0
        call_count = 0

        class RecoveringForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ServiceUnavailableError(
                        message="upstream down",
                        llm_provider="openai",
                        model="gpt-4o",
                    )
                return ForwardResult(status_code=200, body={"ok": True})

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

        def clock() -> float:
            return current_time

        breaker = _make_circuit_breaker(
            threshold=1, recovery_timeout_ms=1000, clock=clock
        )
        processor = _make_processor(
            forwarder=RecoveringForwarder(), circuit_breaker=breaker
        )

        async def run() -> None:
            nonlocal current_time
            await processor.start()
            try:
                future1 = await processor.submit(_context())
                with pytest.raises(ServiceUnavailableError):
                    await asyncio.wait_for(future1, timeout=1.0)
                assert breaker.state.name == "OPEN"

                current_time = 1.0
                future2 = await processor.submit(_context())
                result = await asyncio.wait_for(future2, timeout=1.0)
                assert result.status_code == 200
                assert breaker.state.name == "CLOSED"
            finally:
                await processor.stop()

        asyncio.run(run())


class TestRequestProcessorStreaming:
    """Verify streaming request handling through the processor."""

    def test_streaming_request_yields_chunks(self):
        class StreamingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                raise NotImplementedError

            async def stream_async(self, context: RequestContext):
                yield {"id": "chunk-1"}
                yield {"id": "chunk-2"}

        processor = _make_processor(forwarder=StreamingForwarder())

        async def run() -> list[dict]:
            await processor.start()
            try:
                handle = await processor.submit_stream(_context())
                chunks = []
                async for chunk in handle:
                    chunks.append(chunk)
                return chunks
            finally:
                await processor.stop()

        chunks = asyncio.run(run())
        assert chunks == [{"id": "chunk-1"}, {"id": "chunk-2"}]

    def test_streaming_request_error_is_propagated(self):
        class FailingStreamingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                raise NotImplementedError

            async def stream_async(self, context: RequestContext):
                yield {"id": "chunk-1"}
                raise ServiceUnavailableError(
                    message="upstream failed",
                    llm_provider="openai",
                    model="gpt-4o",
                )

        processor = _make_processor(forwarder=FailingStreamingForwarder())

        async def run() -> None:
            await processor.start()
            try:
                handle = await processor.submit_stream(_context())
                with pytest.raises(ServiceUnavailableError, match="upstream failed"):
                    async for _ in handle:
                        pass
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_streaming_request_is_rate_limited(self):
        rpm = 1
        window_seconds = 1
        processor = _make_processor(rpm=rpm, window_seconds=window_seconds)

        async def run() -> None:
            await processor.start()
            try:
                start = time.monotonic()
                handle1 = await processor.submit_stream(_context())
                chunks1 = []
                async for chunk in handle1:
                    chunks1.append(chunk)

                handle2 = await processor.submit_stream(_context())
                chunks2 = []
                async for chunk in handle2:
                    chunks2.append(chunk)

                elapsed = time.monotonic() - start
                assert elapsed >= window_seconds - 0.05
            finally:
                await processor.stop()

        asyncio.run(run())


class TestRequestProcessorRunningState:
    """Verify is_running and shutdown rejection behavior."""

    def test_is_running_true_when_started(self):
        processor = _make_processor()

        async def run() -> None:
            await processor.start()
            try:
                assert processor.is_running is True
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_is_running_false_when_stopped(self):
        processor = _make_processor()

        async def run() -> None:
            await processor.start()
            await processor.stop()
            assert processor.is_running is False

        asyncio.run(run())

    def test_submit_rejected_when_shutting_down(self):
        shutdown_manager = ShutdownManager()
        processor = _make_processor(shutdown_manager=shutdown_manager)

        async def run() -> None:
            await processor.start()
            try:
                shutdown_manager.start_shutdown()
                future = await processor.submit(_context())
                with pytest.raises(ServiceUnavailableError, match="shutting down"):
                    await asyncio.wait_for(future, timeout=1.0)
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_submit_stream_rejected_when_shutting_down(self):
        shutdown_manager = ShutdownManager()
        processor = _make_processor(shutdown_manager=shutdown_manager)

        async def run() -> None:
            await processor.start()
            try:
                shutdown_manager.start_shutdown()
                with pytest.raises(ServiceUnavailableError, match="shutting down"):
                    await processor.submit_stream(_context())
            finally:
                await processor.stop()

        asyncio.run(run())


class TestRequestProcessorDrain:
    """Verify graceful drain behavior."""

    def test_drain_empties_queue(self):
        processor = _make_processor()

        async def run() -> None:
            await processor.start()
            try:
                futures = [
                    await processor.submit(_context()) for _ in range(3)
                ]
                await processor.drain(timeout_seconds=2.0)
                assert processor._queue.size() == 0
                results = await asyncio.gather(*futures)
                assert all(r.status_code == 200 for r in results)
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_drain_returns_when_queue_already_empty(self):
        processor = _make_processor()

        async def run() -> None:
            await processor.start()
            try:
                await processor.drain(timeout_seconds=1.0)
                assert processor._queue.size() == 0
            finally:
                await processor.stop()

        asyncio.run(run())

    def test_drain_respects_timeout(self):
        class SlowQueue(RequestQueue):
            """A queue that never reports empty so drain must time out."""

            def size(self) -> int:
                return 1

        processor = _make_processor()
        processor._queue = SlowQueue(max_size=10)

        async def run() -> None:
            await processor.start()
            try:
                start = time.monotonic()
                await processor.drain(timeout_seconds=0.1)
                elapsed = time.monotonic() - start
                assert elapsed >= 0.1
            finally:
                await processor.stop()

        asyncio.run(run())
