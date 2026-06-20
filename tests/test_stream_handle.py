"""Tests for the StreamHandle async streaming channel."""

import asyncio

import pytest

from src.ingress.stream_handle import StreamHandle


def _run(coro):
    return asyncio.run(coro)


class TestStreamHandle:
    """Verify StreamHandle chunk delivery and lifecycle."""

    def test_chunk_delivery(self):
        handle = StreamHandle()
        handle.put_chunk({"id": "1"})
        handle.put_chunk({"id": "2"})
        handle.close()

        async def consume():
            chunks = []
            async for chunk in handle:
                chunks.append(chunk)
            return chunks

        chunks = _run(consume())
        assert chunks == [{"id": "1"}, {"id": "2"}]

    def test_error_propagation(self):
        handle = StreamHandle()
        handle.put_chunk({"id": "1"})
        handle.put_error(ValueError("boom"))

        async def consume():
            chunks = []
            with pytest.raises(ValueError, match="boom"):
                async for chunk in handle:
                    chunks.append(chunk)
            return chunks

        chunks = _run(consume())
        assert chunks == [{"id": "1"}]

    def test_cancel_stops_delivery(self):
        handle = StreamHandle()
        handle.put_chunk({"id": "1"})
        handle.cancel()
        handle.put_chunk({"id": "2"})  # should be dropped

        async def consume():
            chunks = []
            async for chunk in handle:
                chunks.append(chunk)
            return chunks

        chunks = _run(consume())
        assert chunks == [{"id": "1"}]

    def test_is_cancelled_property(self):
        handle = StreamHandle()
        assert handle.is_cancelled is False
        handle.cancel()
        assert handle.is_cancelled is True

    def test_close_ends_stream(self):
        handle = StreamHandle()
        handle.close()

        async def consume():
            chunks = []
            async for chunk in handle:
                chunks.append(chunk)
            return chunks

        chunks = _run(consume())
        assert chunks == []

    def test_multiple_closes_are_safe(self):
        handle = StreamHandle()
        handle.close()
        handle.close()

        async def consume():
            chunks = []
            async for chunk in handle:
                chunks.append(chunk)
            return chunks

        chunks = _run(consume())
        assert chunks == []
