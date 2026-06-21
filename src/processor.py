"""Request processing pipeline for Smart-Provider.

The :class:`RequestProcessor` runs a background worker that coordinates the
request queue, rate limiter, and upstream forwarder. Requests are submitted
by the ingress layer via ``submit()``, which returns an ``asyncio.Future``
that resolves with the upstream response.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from datetime import datetime, timezone

from litellm.exceptions import ServiceUnavailableError, Timeout

from src.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.forwarder import Forwarder
from src.forwarder.forwarder import ForwardResult
from src.ingress.context import RequestContext
from src.ingress.stream_handle import StreamHandle
from src.limiter.rate_limiter import SlidingWindowRateLimiter
from src.observability import MetricsCollector
from src.queue import RequestQueue
from src.shutdown import ShutdownManager

logger = logging.getLogger("litellm")
observability_logger = logging.getLogger("smart-provider")


class RequestProcessor:
    """Background processor that moves requests from queue to upstream.

    A single worker loop performs the following steps:

    1. Wait for a request to be available in the queue.
    2. Check whether the request has exceeded its maximum queue wait time.
    3. Acquire a permit from the rate limiter.
    4. Forward the request asynchronously.
    5. Set the result (or exception) on the Future associated with the request,
       or write chunks to the StreamHandle for streaming requests.
    """

    def __init__(
        self,
        queue: RequestQueue,
        limiter: SlidingWindowRateLimiter,
        forwarder: Forwarder,
        metrics: MetricsCollector | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        shutdown_manager: ShutdownManager | None = None,
    ) -> None:
        self._queue = queue
        self._limiter = limiter
        self._forwarder = forwarder
        self._metrics = metrics or MetricsCollector()
        self._circuit_breaker = circuit_breaker
        self._shutdown_manager = shutdown_manager or ShutdownManager()
        self._futures: dict[str, asyncio.Future] = {}
        self._task: asyncio.Task | None = None

    async def submit(self, context: RequestContext) -> asyncio.Future:
        """Submit a request context to the pipeline.

        Returns a Future that resolves with the upstream :class:`ForwardResult`
        or raises an exception if the request is rejected, times out, or fails
        during forwarding.

        Args:
            context: The internal request context to process.

        Returns:
            A Future representing the eventual upstream result.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._futures[context.request_id] = future

        if self._shutdown_manager.is_shutting_down:
            self._futures.pop(context.request_id, None)
            future.set_exception(
                ServiceUnavailableError(
                    message="Smart-Provider is shutting down",
                    llm_provider="smart-provider",
                    model=context.model,
                )
            )
            return future

        enqueue_result = self._queue.enqueue(context)
        if not enqueue_result.success:
            self._futures.pop(context.request_id, None)
            future.set_exception(
                ServiceUnavailableError(
                    message="Request queue is full",
                    llm_provider="smart-provider",
                    model=context.model,
                )
            )
        else:
            await self._metrics.record_enqueue()
            observability_logger.info(
                "Request enqueued",
                extra={
                    "request_id": context.request_id,
                    "client_id": context.client_id,
                    "model": context.model,
                    "queue_size": await self._current_queue_size(),
                },
            )

        return future

    async def submit_stream(self, context: RequestContext) -> StreamHandle:
        """Submit a streaming request context to the pipeline.

        Returns a :class:`StreamHandle` that yields upstream chunks as they
        arrive. If the queue is full, the handle is closed with an exception
        immediately.

        Args:
            context: The internal request context to process.

        Returns:
            A StreamHandle representing the eventual upstream stream.
        """
        if self._shutdown_manager.is_shutting_down:
            raise ServiceUnavailableError(
                message="Smart-Provider is shutting down",
                llm_provider="smart-provider",
                model=context.model,
            )

        enqueue_result = self._queue.enqueue(context)
        if not enqueue_result.success:
            raise ServiceUnavailableError(
                message="Request queue is full",
                llm_provider="smart-provider",
                model=context.model,
            )

        stream_handle = StreamHandle()
        context.stream = True
        context.stream_handle = stream_handle

        await self._metrics.record_enqueue()
        await self._metrics.record_stream_started()
        observability_logger.info(
            "Streaming request enqueued",
            extra={
                "request_id": context.request_id,
                "client_id": context.client_id,
                "model": context.model,
                "queue_size": await self._current_queue_size(),
            },
        )

        return stream_handle

    async def _current_queue_size(self) -> int:
        """Return the current queue size from the metrics collector."""
        snapshot = await self._metrics.snapshot()
        return int(snapshot.get("queue_size", 0))

    async def _update_circuit_breaker_metrics(
        self, previous_state: CircuitBreakerState | None
    ) -> None:
        """Update metrics when the circuit breaker state changes."""
        if self._circuit_breaker is None:
            return
        current_state = self._circuit_breaker.state
        if previous_state is not None and current_state == previous_state:
            return
        opened = (
            current_state == CircuitBreakerState.OPEN
            and previous_state != CircuitBreakerState.OPEN
        )
        await self._metrics.record_circuit_breaker_state(
            current_state.name.lower(), opened=opened
        )

    async def start(self) -> None:
        """Start the background worker."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="request-processor")

    async def stop(self) -> None:
        """Stop the background worker."""
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    @property
    def is_running(self) -> bool:
        """Return True when the background worker is active."""
        return self._task is not None and not self._task.done()

    async def drain(self, timeout_seconds: float) -> None:
        """Wait for the request queue to empty within the given timeout.

        The background worker continues processing queued requests while
        draining. New requests should already be rejected by the shutdown
        manager before this method is called.
        """
        if self._task is None or self._queue.size() == 0:
            return

        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while self._queue.size() > 0:
            if loop.time() >= deadline:
                logger.warning(
                    "Drain timeout of %.2f seconds reached; %s requests remain",
                    timeout_seconds,
                    self._queue.size(),
                )
                break
            await asyncio.sleep(0.05)

    async def _run(self) -> None:
        """Main worker loop."""
        while True:
            context = await self._queue.dequeue()
            previous_breaker_state = (
                self._circuit_breaker.state if self._circuit_breaker else None
            )
            try:
                waited_ms = (
                    datetime.now(timezone.utc) - context.enqueued_at
                ).total_seconds() * 1000
                await self._metrics.record_dequeue(waited_ms)
                observability_logger.info(
                    "Request dequeued",
                    extra={
                        "request_id": context.request_id,
                        "client_id": context.client_id,
                        "model": context.model,
                        "wait_ms": waited_ms,
                    },
                )

                if waited_ms > context.max_wait_time_ms:
                    logger.warning(
                        "Request %s timed out in queue after %.0f ms",
                        context.request_id,
                        waited_ms,
                    )
                    await self._reject(
                        context,
                        Timeout(
                            message="Request timed out while waiting in queue",
                            llm_provider="smart-provider",
                            model=context.model,
                        ),
                        previous_breaker_state,
                    )
                    continue

                if self._circuit_breaker is not None and not self._circuit_breaker.can_execute():
                    await self._update_circuit_breaker_metrics(
                        previous_breaker_state
                    )
                    logger.warning(
                        "Request %s rejected because circuit breaker is open",
                        context.request_id,
                    )
                    observability_logger.warning(
                        "Request rejected by circuit breaker",
                        extra={
                            "request_id": context.request_id,
                            "client_id": context.client_id,
                            "model": context.model,
                        },
                    )
                    await self._reject(
                        context,
                        ServiceUnavailableError(
                            message="Circuit breaker is open",
                            llm_provider="smart-provider",
                            model=context.model,
                        ),
                        previous_breaker_state,
                    )
                    continue

                await self._limiter.acquire()
                if context.stream:
                    await self._process_stream(context, previous_breaker_state)
                else:
                    await self._process_request(context, previous_breaker_state)
            except Exception as exc:
                logger.exception(
                    "Request %s processing failed", context.request_id
                )
                observability_logger.warning(
                    "Request forwarding failed",
                    extra={
                        "request_id": context.request_id,
                        "client_id": context.client_id,
                        "model": context.model,
                        "error_type": type(exc).__name__,
                    },
                )
                await self._reject(context, exc, previous_breaker_state)

    async def _process_request(
        self,
        context: RequestContext,
        previous_breaker_state: CircuitBreakerState | None,
    ) -> None:
        """Process a non-streaming request and resolve its Future."""
        forward_start = time.perf_counter()
        result = await self._forwarder.forward_async(context)
        forward_seconds = time.perf_counter() - forward_start
        await self._metrics.record_forward_duration(forward_seconds)
        if self._circuit_breaker is not None:
            self._circuit_breaker.record_success()
        await self._update_circuit_breaker_metrics(previous_breaker_state)
        self._set_result(context.request_id, result)
        total_seconds = (
            datetime.now(timezone.utc) - context.enqueued_at
        ).total_seconds()
        await self._metrics.record_request_duration(total_seconds)
        observability_logger.info(
            "Request forwarded successfully",
            extra={
                "request_id": context.request_id,
                "client_id": context.client_id,
                "model": context.model,
                "status_code": result.status_code,
            },
        )

    async def _process_stream(
        self,
        context: RequestContext,
        previous_breaker_state: CircuitBreakerState | None,
    ) -> None:
        """Process a streaming request and write chunks to its StreamHandle."""
        stream_handle = context.stream_handle
        if stream_handle is None:
            raise RuntimeError("Streaming request missing StreamHandle")

        forward_start = time.perf_counter()
        try:
            async for chunk in self._forwarder.stream_async(context):
                if stream_handle.is_cancelled:
                    break
                stream_handle.put_chunk(chunk)
            else:
                if self._circuit_breaker is not None:
                    self._circuit_breaker.record_success()
        except Exception as exc:
            if self._circuit_breaker is not None:
                self._circuit_breaker.record_exception(exc)
            stream_handle.put_error(exc)
        finally:
            forward_seconds = time.perf_counter() - forward_start
            await self._metrics.record_forward_duration(forward_seconds)
            await self._update_circuit_breaker_metrics(previous_breaker_state)
            stream_handle.close()
            await self._metrics.record_stream_completed()
            total_seconds = (
                datetime.now(timezone.utc) - context.enqueued_at
            ).total_seconds()
            await self._metrics.record_request_duration(total_seconds)
            observability_logger.info(
                "Streaming request completed",
                extra={
                    "request_id": context.request_id,
                    "client_id": context.client_id,
                    "model": context.model,
                },
            )

    async def _reject(
        self,
        context: RequestContext,
        exc: BaseException,
        previous_breaker_state: CircuitBreakerState | None,
    ) -> None:
        """Resolve a request with an exception or error a streaming handle."""
        if self._circuit_breaker is not None:
            self._circuit_breaker.record_exception(exc)
            await self._update_circuit_breaker_metrics(previous_breaker_state)

        if context.stream and context.stream_handle is not None:
            context.stream_handle.put_error(exc)
            context.stream_handle.close()
            await self._metrics.record_stream_completed()
        else:
            self._set_exception(context.request_id, exc)

    def _set_result(self, request_id: str, result: ForwardResult) -> None:
        """Resolve the future for a request with a successful result."""
        future = self._futures.pop(request_id, None)
        if future is not None and not future.done():
            future.set_result(result)

    def _set_exception(self, request_id: str, exc: BaseException) -> None:
        """Resolve the future for a request with an exception."""
        future = self._futures.pop(request_id, None)
        if future is not None and not future.done():
            future.set_exception(exc)
