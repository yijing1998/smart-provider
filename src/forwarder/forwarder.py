"""Upstream forwarder interface, stub, and litellm-based implementation."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

import litellm
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.config.schema import ForwarderConfig
from src.ingress.context import RequestContext
from src.observability import MetricsCollector

logger = logging.getLogger("litellm")
observability_logger = logging.getLogger("smart-provider")


@dataclass(frozen=True)
class ForwardResult:
    """Result produced by the upstream forwarder.

    Attributes:
        status_code: HTTP status code returned by the upstream API.
        body: Response body; usually a dict matching the OpenAI completion
            response shape, but may also carry an error payload.
        error: Optional error message when the forwarder could not complete
            the request.
    """

    status_code: int
    body: Any
    error: Optional[str] = None


class Forwarder(ABC):
    """Abstract upstream forwarder."""

    @abstractmethod
    async def forward_async(self, context: RequestContext) -> ForwardResult:
        """Send the request to the upstream API and return the response."""
        ...

    @abstractmethod
    async def stream_async(
        self, context: RequestContext
    ) -> AsyncIterator[dict[str, Any]]:
        """Send a streaming request to the upstream API and yield chunks."""
        ...


class StubForwarder(Forwarder):
    """Stub forwarder that returns a synthetic success response."""

    async def forward_async(self, context: RequestContext) -> ForwardResult:
        """Return a synthetic completion response for the given context."""
        return ForwardResult(
            status_code=200,
            body={
                "id": context.request_id,
                "object": "chat.completion",
                "model": context.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    async def stream_async(
        self, context: RequestContext
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield a synthetic streaming chunk and a finish chunk."""
        yield {
            "id": context.request_id,
            "object": "chat.completion.chunk",
            "model": context.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "pong"},
                    "finish_reason": None,
                }
            ],
        }
        yield {
            "id": context.request_id,
            "object": "chat.completion.chunk",
            "model": context.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
        }


class LitellmForwarder(Forwarder):
    """Forwarder that calls the upstream API via litellm.acompletion()."""

    _RETRYABLE_EXCEPTIONS = (
        APIConnectionError,
        RateLimitError,
        ServiceUnavailableError,
        InternalServerError,
    )

    def __init__(
        self,
        config: ForwarderConfig,
        metrics: MetricsCollector | None = None,
    ) -> None:
        self._config = config
        self._metrics = metrics or MetricsCollector()

    async def forward_async(self, context: RequestContext) -> ForwardResult:
        """Forward the request to the configured upstream API.

        The method applies the configured timeout and retries with exponential
        backoff. Retries are performed for transient errors such as connection
        failures, 429 rate limits, and 5xx server errors. Other errors are
        propagated immediately.

        Args:
            context: The internal request context to forward.

        Returns:
            A ``ForwardResult`` containing the upstream response.

        Raises:
            litellm exceptions matching the upstream error category, or
            ``Timeout`` when the upstream call exceeds the configured timeout.
        """
        timeout_seconds = self._config.timeout_ms / 1000
        kwargs: dict[str, Any] = {
            "model": context.model,
            "messages": context.messages,
            "api_base": context.upstream_target,
        }
        if context.extra_body:
            kwargs.update(context.extra_body)

        last_exception: Optional[Exception] = None
        max_attempts = self._config.max_retries + 1

        for attempt in range(max_attempts):
            try:
                response = await asyncio.wait_for(
                    litellm.acompletion(**kwargs),
                    timeout=timeout_seconds,
                )
                body = self._response_to_dict(response)
                return ForwardResult(status_code=200, body=body)
            except asyncio.TimeoutError:
                last_exception = Timeout(
                    message="Upstream request timed out",
                    llm_provider="smart-provider",
                    model=context.model,
                )
            except self._RETRYABLE_EXCEPTIONS as exc:
                last_exception = exc
                await self._record_upstream_error(exc)
                logger.warning(
                    "Request %s attempt %d/%d failed with %s: %s",
                    context.request_id,
                    attempt + 1,
                    max_attempts,
                    type(exc).__name__,
                    exc,
                )
            except APIError as exc:
                # Other API errors (e.g., 400, 401, 404) are not retried,
                # but 5xx-class APIError that is not already caught above
                # should still be recorded.
                await self._record_upstream_error(exc)
                raise

            if attempt < max_attempts - 1:
                backoff_seconds = (self._config.retry_backoff_ms / 1000) * (
                    2 ** attempt
                )
                logger.info(
                    "Retrying request %s in %.2f seconds",
                    context.request_id,
                    backoff_seconds,
                )
                await asyncio.sleep(backoff_seconds)

        if last_exception is not None:
            raise last_exception

        raise RuntimeError("Unexpected end of retry loop")

    async def stream_async(
        self, context: RequestContext
    ) -> AsyncIterator[dict[str, Any]]:
        """Forward a streaming request to the configured upstream API.

        The method calls ``litellm.acompletion(..., stream=True)`` and yields
        each chunk as a JSON-serializable dict. Timeouts apply to the initial
        upstream connection; once chunks start arriving, no per-chunk timeout
        is enforced in this version.

        Args:
            context: The internal request context to forward.

        Yields:
            Dict representations of upstream streaming chunks.

        Raises:
            litellm exceptions matching the upstream error category, or
            ``Timeout`` when the upstream call does not start within the
            configured timeout.
        """
        timeout_seconds = self._config.timeout_ms / 1000
        kwargs: dict[str, Any] = {
            "model": context.model,
            "messages": context.messages,
            "api_base": context.upstream_target,
            "stream": True,
        }
        if context.extra_body:
            kwargs.update(context.extra_body)

        try:
            response = await asyncio.wait_for(
                litellm.acompletion(**kwargs),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise Timeout(
                message="Upstream stream request timed out",
                llm_provider="smart-provider",
                model=context.model,
            )

        async for chunk in response:
            yield self._response_to_dict(chunk)

    async def _record_upstream_error(self, exc: APIError) -> None:
        """Update metrics for upstream errors.

        429 errors are tracked separately from 5xx/connection errors so that
        operators can observe when the smoothing strategy is insufficient.
        """
        if isinstance(exc, RateLimitError):
            await self._metrics.record_upstream_429()
            observability_logger.warning(
                "Upstream returned 429",
                extra={
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", 429),
                },
            )
        else:
            await self._metrics.record_upstream_5xx()
            observability_logger.warning(
                "Upstream returned 5xx or connection error",
                extra={
                    "error_type": type(exc).__name__,
                    "status_code": getattr(exc, "status_code", None),
                },
            )

    @staticmethod
    def _response_to_dict(response: Any) -> dict[str, Any]:
        """Convert a litellm response object to a JSON-serializable dict."""
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        if hasattr(response, "dict"):
            return response.dict()
        return dict(response)
