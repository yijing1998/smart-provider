"""Tests for the litellm-based upstream forwarder."""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import (
    APIConnectionError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.config.schema import ForwarderConfig
from src.forwarder import LitellmForwarder
from src.ingress.context import RequestContext


def _context(upstream_target: str = "https://api.openai.com/v1") -> RequestContext:
    return RequestContext(
        model="gpt-4o",
        messages=[{"role": "user", "content": "hello"}],
        upstream_target=upstream_target,
    )


def _make_config(
    timeout_ms: int = 1000,
    max_retries: int = 0,
    retry_backoff_ms: int = 10,
) -> ForwarderConfig:
    return ForwarderConfig(
        timeout_ms=timeout_ms,
        max_retries=max_retries,
        retry_backoff_ms=retry_backoff_ms,
    )


class _FakeResponse:
    """Minimal stand-in for a litellm ModelResponse."""

    def __init__(self, body: dict):
        self._body = body

    def model_dump(self, mode: str = "json") -> dict:
        return self._body


class TestLitellmForwarderSuccess:
    """Verify successful upstream calls."""

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_successful_response_is_converted(self, mock_acompletion):
        mock_acompletion.return_value = _FakeResponse(
            {"id": "resp-1", "model": "gpt-4o"}
        )
        forwarder = LitellmForwarder(_make_config())

        async def run():
            return await forwarder.forward_async(_context())

        result = asyncio.run(run())

        assert result.status_code == 200
        assert result.body == {"id": "resp-1", "model": "gpt-4o"}
        mock_acompletion.assert_awaited_once()
        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["messages"] == [{"role": "user", "content": "hello"}]
        assert call_kwargs["api_base"] == "https://api.openai.com/v1"

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_extra_body_is_merged(self, mock_acompletion):
        mock_acompletion.return_value = _FakeResponse({"ok": True})
        forwarder = LitellmForwarder(_make_config())
        context = RequestContext(
            model="gpt-4o",
            messages=[{"role": "user", "content": "hello"}],
            extra_body={"temperature": 0.5, "max_tokens": 100},
        )

        async def run():
            return await forwarder.forward_async(context)

        asyncio.run(run())

        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 100


    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_authorization_bearer_token_is_passed_as_api_key(self, mock_acompletion):
        mock_acompletion.return_value = _FakeResponse({"ok": True})
        forwarder = LitellmForwarder(_make_config())
        context = RequestContext(
            model="openai/z-ai/glm-5.1",
            messages=[{"role": "user", "content": "hello"}],
            upstream_target="https://integrate.api.nvidia.com/v1",
            extra_headers={"Authorization": "Bearer secret-nvidia-key"},
        )

        async def run():
            return await forwarder.forward_async(context)

        result = asyncio.run(run())

        assert result.status_code == 200
        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["api_key"] == "secret-nvidia-key"
        assert call_kwargs["model"] == "openai/z-ai/glm-5.1"
        assert call_kwargs["api_base"] == "https://integrate.api.nvidia.com/v1"

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_missing_authorization_passes_none_api_key(self, mock_acompletion):
        mock_acompletion.return_value = _FakeResponse({"ok": True})
        forwarder = LitellmForwarder(_make_config())

        async def run():
            return await forwarder.forward_async(_context())

        asyncio.run(run())

        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["api_key"] is None

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_lowercase_authorization_header_is_recognized(self, mock_acompletion):
        mock_acompletion.return_value = _FakeResponse({"ok": True})
        forwarder = LitellmForwarder(_make_config())
        context = RequestContext(
            model="gpt-4o",
            messages=[{"role": "user", "content": "hello"}],
            extra_headers={"authorization": "Bearer lowercase-key"},
        )

        async def run():
            return await forwarder.forward_async(context)

        asyncio.run(run())

        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["api_key"] == "lowercase-key"

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_stream_passes_api_key(self, mock_acompletion):
        async def _stream(**kwargs):
            yield _FakeResponse({"chunk": 1})

        mock_acompletion.side_effect = _stream
        forwarder = LitellmForwarder(_make_config())
        context = RequestContext(
            model="openai/z-ai/glm-5.1",
            messages=[{"role": "user", "content": "hello"}],
            upstream_target="https://integrate.api.nvidia.com/v1",
            extra_headers={"Authorization": "Bearer stream-key"},
            stream=True,
        )

        async def run():
            chunks = []
            async for chunk in forwarder.stream_async(context):
                chunks.append(chunk)
            return chunks

        asyncio.run(run())

        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["api_key"] == "stream-key"
        assert call_kwargs["stream"] is True


class TestLitellmForwarderErrors:
    """Verify error handling and retry behavior."""

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_timeout_raises_timeout_exception(self, mock_acompletion):
        async def _hang(**kwargs):
            await asyncio.sleep(10)

        mock_acompletion.side_effect = _hang
        forwarder = LitellmForwarder(_make_config(timeout_ms=50))

        async def run():
            return await forwarder.forward_async(_context())

        with pytest.raises(Timeout):
            asyncio.run(run())

        assert mock_acompletion.call_count == 1

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_429_is_retried_then_success(self, mock_acompletion):
        mock_acompletion.side_effect = [
            RateLimitError(
                message="rate limited", llm_provider="openai", model="gpt-4o"
            ),
            _FakeResponse({"id": "resp-2"}),
        ]
        forwarder = LitellmForwarder(
            _make_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            return await forwarder.forward_async(_context())

        result = asyncio.run(run())

        assert result.status_code == 200
        assert result.body == {"id": "resp-2"}
        assert mock_acompletion.call_count == 2

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_500_is_retried_then_raises(self, mock_acompletion):
        exc = ServiceUnavailableError(
            message="server error", llm_provider="openai", model="gpt-4o"
        )
        mock_acompletion.side_effect = [exc, exc]
        forwarder = LitellmForwarder(
            _make_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            return await forwarder.forward_async(_context())

        with pytest.raises(ServiceUnavailableError):
            asyncio.run(run())

        assert mock_acompletion.call_count == 2

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_400_is_not_retried(self, mock_acompletion):
        exc = BadRequestError(
            message="bad request", llm_provider="openai", model="gpt-4o"
        )
        mock_acompletion.side_effect = exc
        forwarder = LitellmForwarder(_make_config(max_retries=2))

        async def run():
            return await forwarder.forward_async(_context())

        with pytest.raises(BadRequestError):
            asyncio.run(run())

        assert mock_acompletion.call_count == 1

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_connection_error_is_retried(self, mock_acompletion):
        mock_acompletion.side_effect = [
            APIConnectionError(
                message="connection failed",
                llm_provider="openai",
                model="gpt-4o",
            ),
            _FakeResponse({"id": "resp-3"}),
        ]
        forwarder = LitellmForwarder(
            _make_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            return await forwarder.forward_async(_context())

        result = asyncio.run(run())

        assert result.status_code == 200
        assert mock_acompletion.call_count == 2

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_internal_server_error_is_retried(self, mock_acompletion):
        mock_acompletion.side_effect = [
            InternalServerError(
                message="internal error",
                llm_provider="openai",
                model="gpt-4o",
            ),
            _FakeResponse({"id": "resp-4"}),
        ]
        forwarder = LitellmForwarder(
            _make_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            return await forwarder.forward_async(_context())

        result = asyncio.run(run())

        assert result.status_code == 200
        assert mock_acompletion.call_count == 2


class TestLitellmForwarderStreaming:
    """Verify streaming upstream calls."""

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_stream_async_yields_chunks(self, mock_acompletion):
        class _FakeChunk:
            def model_dump(self, mode: str = "json") -> dict:
                return {"id": "chunk-1", "object": "chat.completion.chunk"}

        async def _fake_stream(**kwargs):
            yield _FakeChunk()
            yield _FakeChunk()

        mock_acompletion.return_value = _fake_stream()
        forwarder = LitellmForwarder(_make_config())

        async def run():
            chunks = []
            async for chunk in forwarder.stream_async(_context()):
                chunks.append(chunk)
            return chunks

        chunks = asyncio.run(run())

        assert len(chunks) == 2
        assert chunks[0]["id"] == "chunk-1"
        mock_acompletion.assert_awaited_once()
        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["stream"] is True
        assert call_kwargs["model"] == "gpt-4o"

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_stream_async_passes_extra_body(self, mock_acompletion):
        class _FakeChunk:
            def model_dump(self, mode: str = "json") -> dict:
                return {"ok": True}

        async def _fake_stream(**kwargs):
            yield _FakeChunk()

        mock_acompletion.return_value = _fake_stream()
        forwarder = LitellmForwarder(_make_config())
        context = RequestContext(
            model="gpt-4o",
            messages=[{"role": "user", "content": "hello"}],
            extra_body={"temperature": 0.5},
        )

        async def run():
            chunks = []
            async for chunk in forwarder.stream_async(context):
                chunks.append(chunk)
            return chunks

        asyncio.run(run())

        call_kwargs = mock_acompletion.await_args.kwargs
        assert call_kwargs["temperature"] == 0.5

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_stream_async_timeout_raises_timeout_exception(self, mock_acompletion):
        async def _hang(**kwargs):
            await asyncio.sleep(10)

        mock_acompletion.side_effect = _hang
        forwarder = LitellmForwarder(_make_config(timeout_ms=50))

        async def run():
            async for _ in forwarder.stream_async(_context()):
                pass

        with pytest.raises(Timeout):
            asyncio.run(run())


class TestLitellmForwarderBackoff:
    """Verify retry backoff timing."""

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_backoff_increases_between_retries(self, mock_acompletion):
        exc = RateLimitError(
            message="rate limited", llm_provider="openai", model="gpt-4o"
        )
        mock_acompletion.side_effect = [exc, exc, _FakeResponse({"id": "resp-5"})]
        forwarder = LitellmForwarder(
            _make_config(max_retries=2, retry_backoff_ms=50)
        )

        async def run():
            return await forwarder.forward_async(_context())

        start = time.monotonic()
        result = asyncio.run(run())
        elapsed = time.monotonic() - start

        assert result.status_code == 200
        assert mock_acompletion.call_count == 3
        # Expected backoff: 50ms + 100ms = 150ms; allow some tolerance.
        assert elapsed >= 0.13
