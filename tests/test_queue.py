"""Tests for the Smart-Provider request queue."""

import asyncio

import pytest

from src.ingress.context import RequestContext
from src.queue import RequestQueue


def _context(model: str = "gpt-4o") -> RequestContext:
    return RequestContext(model=model, messages=[{"role": "user", "content": "hi"}])


class TestRequestQueue:
    """Verify asyncio-based request queue behavior."""

    def test_enqueue_and_size(self):
        queue = RequestQueue(max_size=2)
        assert queue.size() == 0
        assert queue.enqueue(_context()).success is True
        assert queue.size() == 1
        assert queue.enqueue(_context()).success is True
        assert queue.is_full() is True

    def test_enqueue_fails_when_full(self):
        queue = RequestQueue(max_size=1)
        queue.enqueue(_context())
        result = queue.enqueue(_context())
        assert result.success is False
        assert result.queue_full is True

    def test_async_dequeue_returns_item(self):
        queue = RequestQueue(max_size=2)
        context = _context()
        queue.enqueue(context)

        async def run() -> RequestContext:
            return await queue.dequeue()

        result = asyncio.run(run())
        assert result.request_id == context.request_id
        assert queue.size() == 0

    def test_async_dequeue_waits_for_item(self):
        queue = RequestQueue(max_size=2)

        async def producer() -> None:
            await asyncio.sleep(0.05)
            queue.enqueue(_context())

        async def consumer() -> RequestContext:
            return await queue.dequeue()

        async def run() -> RequestContext:
            results = await asyncio.gather(consumer(), producer())
            return results[0]

        result = asyncio.run(run())
        assert result.model == "gpt-4o"

    def test_try_dequeue_non_blocking(self):
        queue = RequestQueue(max_size=2)
        assert queue.try_dequeue() is None
        context = _context()
        queue.enqueue(context)
        assert queue.try_dequeue() is not None
        assert queue.try_dequeue() is None
