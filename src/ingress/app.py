"""FastAPI application implementing the Smart-Provider ingress layer.

This module relies on the litellm SDK for OpenAI-compatible request parsing,
model validation, exception classification, and logging. It does not use
litellm's completion functions for upstream forwarding; that responsibility
remains with the forwarder module.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from litellm import get_model_info
from litellm.exceptions import (
    APIConnectionError,
    APIError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from litellm.types.completion import CompletionRequest
from pydantic import ValidationError

from src.circuit_breaker import CircuitBreaker
from src.config import Config, load_config
from src.forwarder import Forwarder, LitellmForwarder
from src.ingress.context import RequestContext
from src.observability import MetricsCollector
from src.limiter import SlidingWindowRateLimiter
from src.processor import RequestProcessor
from src.queue import RequestQueue
from src.shutdown import ShutdownManager

# Reuse litellm's logger namespace so ingress events appear alongside
# litellm logs when the same handlers are configured.
logger = logging.getLogger("litellm")


def create_app(
    config: Optional[Config] = None,
    queue: Optional[RequestQueue] = None,
    limiter: Optional[SlidingWindowRateLimiter] = None,
    forwarder: Optional[Forwarder] = None,
    processor: Optional[RequestProcessor] = None,
    circuit_breaker: Optional[CircuitBreaker] = None,
    shutdown_manager: Optional[ShutdownManager] = None,
) -> FastAPI:
    """Create and configure the Ingress FastAPI application.

    The dependencies can be injected for testing; in production they default
    to in-memory implementations configured from ``Config``.
    """
    cfg = config or load_config()
    logging.getLogger("smart-provider").setLevel(
        getattr(logging, cfg.observability_log_level.upper(), logging.INFO)
    )
    request_shutdown_manager = shutdown_manager or ShutdownManager()
    request_processor = processor
    if request_processor is None:
        request_queue = queue or RequestQueue(max_size=cfg.queue.max_size)
        request_limiter = limiter or SlidingWindowRateLimiter(cfg.limiter)
        request_forwarder = forwarder or LitellmForwarder(cfg.forwarder)
        request_circuit_breaker = circuit_breaker
        if request_circuit_breaker is None and cfg.circuit_breaker.enabled:
            request_circuit_breaker = CircuitBreaker(cfg.circuit_breaker)
        request_processor = RequestProcessor(
            request_queue,
            request_limiter,
            request_forwarder,
            circuit_breaker=request_circuit_breaker,
            shutdown_manager=request_shutdown_manager,
        )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        await request_processor.start()
        yield
        request_shutdown_manager.start_shutdown()
        drain_timeout_seconds = cfg.shutdown_drain_timeout_ms / 1000
        logger.info(
            "Shutting down gracefully with drain timeout %.2f seconds",
            drain_timeout_seconds,
        )
        await request_processor.drain(timeout_seconds=drain_timeout_seconds)
        await request_processor.stop()

    app = FastAPI(
        title="Smart-Provider Ingress",
        version="0.1.0",
        docs_url="/docs",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def _shutdown_middleware(request: Request, call_next) -> Any:
        """Reject non-health-check requests while shutting down."""
        if (
            request_shutdown_manager.is_shutting_down
            and request.url.path not in ("/health", "/ready")
        ):
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "message": "Smart-Provider is shutting down",
                        "type": "ServiceUnavailableError",
                    }
                },
            )
        return await call_next(request)

    @app.exception_handler(BadRequestError)
    @app.exception_handler(NotFoundError)
    @app.exception_handler(RateLimitError)
    @app.exception_handler(ServiceUnavailableError)
    @app.exception_handler(InternalServerError)
    @app.exception_handler(APIConnectionError)
    @app.exception_handler(APIError)
    @app.exception_handler(Timeout)
    async def _handle_litellm_exception(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Map litellm exceptions to OpenAI-compatible HTTP responses."""
        status_code = _status_code_for_litellm_exception(exc)
        body = {
            "error": {
                "message": str(exc),
                "type": type(exc).__name__,
            }
        }
        return JSONResponse(status_code=status_code, content=body)

    @app.exception_handler(ValidationError)
    async def _handle_validation_error(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Map Pydantic validation errors (from litellm request parsing) to 400."""
        logger.warning("Request validation failed: %s", exc)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": "Invalid request body",
                    "type": "BadRequestError",
                    "details": exc.errors(),
                }
            },
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Liveness probe: return whether the process is alive."""
        return {"status": "healthy"}

    @app.get("/ready")
    async def ready() -> Any:
        """Readiness probe: return whether the service is willing to receive traffic."""
        if request_shutdown_manager.is_shutting_down:
            return JSONResponse(
                status_code=503,
                content={"status": "shutting_down"},
            )
        if not request_processor.is_running:
            return JSONResponse(
                status_code=503,
                content={"status": "processor_not_running"},
            )
        return {"status": "ready"}

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: Request,
        x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
    ) -> Any:
        """Receive an OpenAI-compatible chat completion request.

        The request body is parsed with litellm's CompletionRequest, the model
        is validated via litellm model info, and the request is converted into
        the internal RequestContext and submitted to the queue.
        """
        raw_body = await request.json()

        # 1. Parse using litellm's OpenAI-compatible request type.
        try:
            completion_request = CompletionRequest(**raw_body)
        except ValidationError as exc:
            logger.warning("Failed to parse completion request: %s", exc)
            raise BadRequestError(
                message="Invalid chat completion request",
                llm_provider="smart-provider",
                model=str(raw_body.get("model", "")),
            ) from exc

        # 3. Validate required fields that litellm marks as optional.
        if not completion_request.messages:
            logger.warning("Request missing messages field")
            raise BadRequestError(
                message="Request body must include a non-empty 'messages' field",
                llm_provider="smart-provider",
                model=completion_request.model,
            )

        # 4. Validate the model using litellm's model info.
        try:
            get_model_info(completion_request.model)
        except Exception as exc:
            logger.warning("Unknown model requested: %s", completion_request.model)
            raise NotFoundError(
                message=f"Model '{completion_request.model}' is not recognized",
                llm_provider="smart-provider",
                model=completion_request.model,
            ) from exc

        # 5. Build the internal request context.
        #    litellm may represent messages as dicts or Pydantic models depending
        #    on configuration; normalize to plain dicts.
        messages = [
            msg.model_dump(mode="json") if hasattr(msg, "model_dump") else msg
            for msg in completion_request.messages
        ]
        context = RequestContext(
            model=completion_request.model,
            messages=messages,
            client_id=x_client_id or "default",
            upstream_target=cfg.upstream_url,
            stream=bool(completion_request.stream),
            extra_body=_extra_body(completion_request),
            extra_headers=dict(request.headers) if request.headers else {},
            max_wait_time_ms=cfg.queue_max_wait_ms,
        )

        # 5. Submit to the pipeline and return the upstream result.
        logger.info(
            "Request %s submitted (model=%s, client=%s, stream=%s)",
            context.request_id,
            context.model,
            context.client_id,
            context.stream,
        )

        if context.stream:
            stream_handle = await request_processor.submit_stream(context)
            return StreamingResponse(
                _sse_generator(stream_handle, context.request_id),
                media_type="text/event-stream",
            )

        try:
            future = await request_processor.submit(context)
            result = await asyncio.wait_for(
                future,
                timeout=context.max_wait_time_ms / 1000,
            )
        except asyncio.TimeoutError as exc:
            logger.warning("Request %s timed out waiting for response", context.request_id)
            raise Timeout(
                message="Request timed out waiting for response",
                llm_provider="smart-provider",
                model=context.model,
            ) from exc

        if result.error:
            logger.error(
                "Request %s forwarding failed: %s",
                context.request_id,
                result.error,
            )
            raise InternalServerError(
                message=result.error,
                llm_provider="smart-provider",
                model=context.model,
            )

        logger.info(
            "Request %s returning upstream response (status=%s)",
            context.request_id,
            result.status_code,
        )
        return JSONResponse(status_code=result.status_code, content=result.body)

    if cfg.observability_metrics_enabled:

        @app.get("/metrics")
        async def metrics() -> Any:
            """Expose runtime metrics snapshot."""
            return await MetricsCollector().snapshot()

        @app.get("/metrics/prometheus")
        async def prometheus_metrics() -> Any:
            """Expose runtime metrics in Prometheus exposition format."""
            return StreamingResponse(
                content=iter([MetricsCollector().prometheus_metrics()]),
                media_type="text/plain; version=0.0.4; charset=utf-8",
            )

    return app


async def _sse_generator(stream_handle, request_id: str):
    """Convert a StreamHandle into Server-Sent Events.

    Each upstream chunk becomes a ``data:`` line. If an error occurs during
    streaming, an ``event: error`` frame is emitted before the final
    ``data: [DONE]`` terminator. If the client disconnects, the StreamHandle
    is cancelled so the worker stops consuming upstream chunks.
    """
    try:
        async for chunk in stream_handle:
            yield f"data: {json.dumps(chunk)}\n\n"
    except asyncio.CancelledError:
        logger.info("Request %s stream cancelled by client", request_id)
        stream_handle.cancel()
        raise
    except Exception as exc:
        logger.warning("Request %s streaming failed: %s", request_id, exc)
        error_payload = {
            "error": {
                "message": str(exc),
                "type": type(exc).__name__,
            }
        }
        yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"
    finally:
        if not stream_handle.is_closed:
            stream_handle.cancel()
    yield "data: [DONE]\n\n"


def _status_code_for_litellm_exception(exc: Exception) -> int:
    """Map litellm exception classes to HTTP status codes."""
    if isinstance(exc, BadRequestError):
        return 400
    if isinstance(exc, NotFoundError):
        return 404
    if isinstance(exc, RateLimitError):
        return 429
    if isinstance(exc, Timeout):
        return 504
    if isinstance(exc, APIConnectionError):
        return 502
    if isinstance(exc, InternalServerError):
        return 500
    if isinstance(exc, ServiceUnavailableError):
        return 503
    if isinstance(exc, APIError):
        return 502
    return 500


def _extra_body(completion_request: CompletionRequest) -> dict[str, Any]:
    """Extract non-core fields from the litellm request for upstream passthrough."""
    extra: dict[str, Any] = {}
    if completion_request.temperature is not None:
        extra["temperature"] = completion_request.temperature
    if completion_request.max_tokens is not None:
        extra["max_tokens"] = completion_request.max_tokens
    if completion_request.top_p is not None:
        extra["top_p"] = completion_request.top_p
    if completion_request.n is not None:
        extra["n"] = completion_request.n
    if completion_request.stop is not None:
        extra["stop"] = completion_request.stop
    if completion_request.seed is not None:
        extra["seed"] = completion_request.seed
    if completion_request.tools is not None:
        extra["tools"] = [
            tool.model_dump(mode="json") for tool in completion_request.tools
        ]
    if completion_request.tool_choice is not None:
        extra["tool_choice"] = completion_request.tool_choice
    return extra
