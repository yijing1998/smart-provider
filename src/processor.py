"""Request processing pipeline for Smart-Provider.

The :class:`RequestProcessor` runs a background worker that coordinates the
request queue, rate limiter, and upstream forwarder. Requests are submitted
by the ingress layer via ``submit()``, which returns an ``asyncio.Future``
that resolves with the upstream response.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone

from litellm.exceptions import ServiceUnavailableError, Timeout

from src.forwarder import Forwarder
from src.forwarder.forwarder import ForwardResult
from src.ingress.context import RequestContext
from src.limiter.rate_limiter import SlidingWindowRateLimiter
from src.queue import RequestQueue

logger = logging.getLogger("litellm")


class RequestProcessor:
    """Background processor that moves requests from queue to upstream.

    A single worker loop performs the following steps:

    1. Wait for a request to be available in the queue.
    2. Check whether the request has exceeded its maximum queue wait time.
    3. Acquire a permit from the rate limiter.
    4. Forward the request asynchronously.
    5. Set the result (or exception) on the Future associated with the request.
    """

    def __init__(
        self,
        queue: RequestQueue,
        limiter: SlidingWindowRateLimiter,
        forwarder: Forwarder,
    ) -> None:
        self._queue = queue
        self._limiter = limiter
        self._forwarder = forwarder
        self._futures: dict[str, asyncio.Future] = {}
        self._task: asyncio.Task | None = None

    def submit(self, context: RequestContext) -> asyncio.Future:
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

        return future

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

    async def _run(self) -> None:
        """Main worker loop."""
        while True:
            context = await self._queue.dequeue()
            try:
                waited_ms = (
                    datetime.now(timezone.utc) - context.enqueued_at
                ).total_seconds() * 1000
                if waited_ms > context.max_wait_time_ms:
                    logger.warning(
                        "Request %s timed out in queue after %.0f ms",
                        context.request_id,
                        waited_ms,
                    )
                    self._set_exception(
                        context.request_id,
                        Timeout(
                            message="Request timed out while waiting in queue",
                            llm_provider="smart-provider",
                            model=context.model,
                        ),
                    )
                    continue

                await self._limiter.acquire()
                result = await self._forwarder.forward_async(context)
                self._set_result(context.request_id, result)
            except Exception as exc:
                logger.exception(
                    "Request %s processing failed", context.request_id
                )
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
