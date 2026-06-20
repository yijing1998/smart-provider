"""Request queue interface and an asyncio-based in-memory implementation."""

import asyncio
from dataclasses import dataclass
from typing import Optional

from src.ingress.context import RequestContext


@dataclass(frozen=True)
class EnqueueResult:
    """Result of an enqueue operation.

    Attributes:
        success: True if the context was accepted into the queue.
        queue_full: True if the queue rejected the context due to capacity.
    """

    success: bool
    queue_full: bool = False


class RequestQueue:
    """In-memory FIFO request queue with a capacity limit.

    The queue is backed by :class:`asyncio.Queue` so that consumers can wait
    asynchronously for new items. Producers still use a synchronous
    :meth:`enqueue` since request admission happens in the HTTP handler.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._queue: asyncio.Queue[RequestContext] = asyncio.Queue(
            maxsize=max_size
        )

    def enqueue(self, context: RequestContext) -> EnqueueResult:
        """Add a request context to the queue if capacity allows."""
        try:
            self._queue.put_nowait(context)
        except asyncio.QueueFull:
            return EnqueueResult(success=False, queue_full=True)
        return EnqueueResult(success=True)

    async def dequeue(self) -> RequestContext:
        """Remove and return the oldest context, waiting if necessary."""
        return await self._queue.get()

    def try_dequeue(self) -> Optional[RequestContext]:
        """Remove and return the oldest context if one is available.

        Returns None when the queue is empty. This is useful for callers that
        need a non-blocking peek at the queue.
        """
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def is_full(self) -> bool:
        """Return True when the queue has reached its capacity limit."""
        return self._queue.full()

    def size(self) -> int:
        """Return the current number of queued contexts."""
        return self._queue.qsize()
