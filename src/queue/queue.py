"""Request queue interface and a simple in-memory implementation."""

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

    This is a minimal stub implementation sufficient for the ingress layer
    integration. The actual queueing policy and back-pressure semantics will
    be refined when the dedicated queue module is implemented.
    """

    def __init__(self, max_size: int = 1000) -> None:
        self._max_size = max_size
        self._items: list[RequestContext] = []

    def enqueue(self, context: RequestContext) -> EnqueueResult:
        """Add a request context to the queue if capacity allows."""
        if len(self._items) >= self._max_size:
            return EnqueueResult(success=False, queue_full=True)
        self._items.append(context)
        return EnqueueResult(success=True)

    def dequeue(self) -> Optional[RequestContext]:
        """Remove and return the oldest context, if any."""
        if not self._items:
            return None
        return self._items.pop(0)

    def is_full(self) -> bool:
        """Return True when the queue has reached its capacity limit."""
        return len(self._items) >= self._max_size

    def size(self) -> int:
        """Return the current number of queued contexts."""
        return len(self._items)
