"""Async streaming channel between the request processor worker and ingress."""

from __future__ import annotations

import asyncio
from typing import Any


class StreamHandle:
    """Asynchronous channel for streaming upstream chunks to an ingress handler.

    A :class:`StreamHandle` is created by the ingress layer when a streaming
    request is submitted. The processor worker writes chunks produced by the
    upstream forwarder into the handle, while the ingress handler consumes them
    through ``async for chunk in handle`` and forwards them to the client as
    Server-Sent Events.

    The handle supports three terminal conditions:

    - ``close()``: normal end-of-stream.
    - ``put_error(exc)``: an exception occurred; the consumer will re-raise it.
    - ``cancel()``: the client disconnected; the producer should stop writing.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any] | Exception | None] = (
            asyncio.Queue()
        )
        self._cancelled = asyncio.Event()
        self._closed = False

    async def __aiter__(self):
        """Yield chunks until the stream is closed or an error is emitted."""
        while True:
            item = await self._queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
            yield item

    def put_chunk(self, chunk: dict[str, Any]) -> None:
        """Write a chunk to the stream.

        Silently drops the chunk if the handle has been cancelled or closed.
        """
        if self._closed or self._cancelled.is_set():
            return
        self._queue.put_nowait(chunk)

    def put_error(self, exc: Exception) -> None:
        """Signal that an exception occurred and close the stream."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(exc)

    def close(self) -> None:
        """Signal normal end-of-stream."""
        if self._closed:
            return
        self._closed = True
        self._queue.put_nowait(None)

    def cancel(self) -> None:
        """Signal that the client disconnected.

        After cancellation, ``put_chunk`` will drop further chunks and the
        producer should stop iterating over the upstream stream.
        """
        if self._cancelled.is_set():
            return
        self._cancelled.set()
        self.close()

    @property
    def is_cancelled(self) -> bool:
        """Return True if the stream has been cancelled."""
        return self._cancelled.is_set()

    @property
    def is_closed(self) -> bool:
        """Return True if the stream has been closed or errored."""
        return self._closed
