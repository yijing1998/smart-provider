"""Tests for the Smart-Provider ingress layer."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from litellm.exceptions import BadRequestError, NotFoundError

from src.circuit_breaker import CircuitBreaker
from src.config import Config
from src.forwarder import ForwardResult, Forwarder, StubForwarder
from src.ingress.app import _status_code_for_litellm_exception, create_app
from src.ingress.context import RequestContext
from src.queue import RequestQueue
from src.shutdown import ShutdownManager


def _valid_chat_request() -> dict:
    return {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "hello"}],
    }


class TestLitellmExceptionMapping:
    """Verify litellm exceptions are mapped to the expected HTTP status codes."""

    def test_bad_request_maps_to_400(self):
        exc = BadRequestError(
            message="bad request", llm_provider="smart-provider", model="gpt-4o"
        )
        assert _status_code_for_litellm_exception(exc) == 400

    def test_not_found_maps_to_404(self):
        exc = NotFoundError(
            message="not found", llm_provider="smart-provider", model="unknown"
        )
        assert _status_code_for_litellm_exception(exc) == 404


class TestRequestParsingAndContext:
    """Verify request parsing, model validation, and context construction."""

    def test_valid_request_returns_200(self):
        queue = RequestQueue(max_size=10)
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )

        assert response.status_code == 200
        body = response.json()
        assert body["model"] == "openai/gpt-4o"
        assert body["choices"][0]["message"]["content"] == "pong"
        assert queue.size() == 0

    def test_invalid_json_body_returns_400(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o"},  # missing messages
            )

        assert response.status_code == 400
        assert response.json()["error"]["type"] == "BadRequestError"

    def test_bare_model_name_is_prefixed(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        queue = CapturingQueue(max_size=10)
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "this-model-does-not-exist",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )

        assert response.status_code == 200
        assert len(captured_contexts) == 1
        assert captured_contexts[0].model == "openai/this-model-does-not-exist"

    def test_provider_prefixed_model_returns_200(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "openai/z-ai/glm-5.1",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )

        assert response.status_code == 200

    def test_model_with_slash_is_still_prefixed(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        queue = CapturingQueue(max_size=10)
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "z-ai/glm-5.1",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )

        assert response.status_code == 200
        assert len(captured_contexts) == 1
        assert captured_contexts[0].model == "openai/z-ai/glm-5.1"

    def test_custom_upstream_provider_is_used_as_prefix(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        config = Config(upstream_litellm_provider="azure")
        queue = CapturingQueue(max_size=10)
        app = create_app(config=config, queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hello"}],
                },
            )

        assert response.status_code == 200
        assert len(captured_contexts) == 1
        assert captured_contexts[0].model == "azure/gpt-4o"

    def test_custom_request_parameters_are_passed_through(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        queue = CapturingQueue(max_size=10)
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hello"}],
                    "temperature": 0.7,
                    "max_tokens": 100,
                    "chat_template_kwargs": {"foo": "bar"},
                },
            )

        assert response.status_code == 200
        assert len(captured_contexts) == 1
        assert captured_contexts[0].extra_body["temperature"] == 0.7
        assert captured_contexts[0].extra_body["max_tokens"] == 100
        assert captured_contexts[0].extra_body["chat_template_kwargs"] == {"foo": "bar"}
        assert "model" not in captured_contexts[0].extra_body
        assert "messages" not in captured_contexts[0].extra_body
        assert "stream" not in captured_contexts[0].extra_body

    def test_stream_request_returns_sse(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "data: [DONE]" in response.text

    def test_client_id_header_is_propagated_to_context(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        queue = CapturingQueue(max_size=10)
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            client.post(
                "/v1/chat/completions",
                json=_valid_chat_request(),
                headers={"X-Client-Id": "client-42"},
            )

        assert len(captured_contexts) == 1
        assert captured_contexts[0].client_id == "client-42"
        assert captured_contexts[0].model == "openai/gpt-4o"
        assert captured_contexts[0].request_id
        assert captured_contexts[0].enqueued_at


class TestQueueFullBehavior:
    """Verify ingress returns 503 when the queue is at capacity."""

    def test_queue_full_returns_503(self):
        class NonConsumingQueue(RequestQueue):
            """A queue that never dequeues, so submitted items remain in it."""

            async def dequeue(self) -> RequestContext:
                await asyncio.Event().wait()

        queue = NonConsumingQueue(max_size=1)
        queue.enqueue(
            RequestContext(model="gpt-4o", messages=[{"role": "user", "content": "x"}])
        )
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )

        assert response.status_code == 503
        assert "full" in response.json()["error"]["message"].lower()


class TestForwarderIntegration:
    """Verify ingress waits on and returns the forwarder result."""

    def test_forwarder_error_is_returned_as_500(self):
        class FailingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                return ForwardResult(
                    status_code=0, body=None, error="upstream unreachable"
                )

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

        app = create_app(
            queue=RequestQueue(max_size=10),
            forwarder=FailingForwarder(),
        )

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )

        assert response.status_code == 500
        assert "upstream unreachable" in response.json()["error"]["message"]


class TestConfigDefaults:
    """Verify ingress respects injected configuration."""

    def test_config_upstream_url_is_used(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        config = Config(upstream_url="https://custom.example.com/v1")
        app = create_app(
            config=config,
            queue=CapturingQueue(max_size=10),
            forwarder=StubForwarder(),
        )

        with TestClient(app) as client:
            client.post("/v1/chat/completions", json=_valid_chat_request())

        assert captured_contexts[0].upstream_target == "https://custom.example.com/v1"


class TestCircuitBreakerIntegration:
    """Verify circuit breaker behavior through the ingress endpoint."""

    def test_upstream_failure_opens_breaker_and_returns_503(self):
        class FailingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                from litellm.exceptions import ServiceUnavailableError

                raise ServiceUnavailableError(
                    message="upstream down",
                    llm_provider="openai",
                    model="gpt-4o",
                )

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

        config = Config(
            circuit_breaker_enabled=True,
            circuit_breaker_failure_threshold=1,
        )
        app = create_app(
            config=config,
            queue=RequestQueue(max_size=10),
            forwarder=FailingForwarder(),
        )

        with TestClient(app) as client:
            response1 = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )
            response2 = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )

        assert response1.status_code == 503
        assert response2.status_code == 503
        assert "circuit breaker" in response2.json()["error"]["message"].lower()

    def test_disabled_breaker_does_not_affect_requests(self):
        config = Config(circuit_breaker_enabled=False)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions", json=_valid_chat_request()
            )

        assert response.status_code == 200


class TestStreamingIntegration:
    """Verify streaming responses through the ingress endpoint."""

    def test_streaming_request_returns_sse_chunks(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = response.text
        assert 'data: {"id"' in body
        assert "data: [DONE]" in body

    def test_streaming_request_with_queue_full_returns_503(self):
        class NonConsumingQueue(RequestQueue):
            async def dequeue(self) -> RequestContext:
                await asyncio.Event().wait()

        queue = NonConsumingQueue(max_size=1)
        queue.enqueue(
            RequestContext(model="gpt-4o", messages=[{"role": "user", "content": "x"}])
        )
        app = create_app(queue=queue, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": "hello"}],
                    "stream": True,
                },
            )

        assert response.status_code == 503


class TestHealthEndpoints:
    """Verify health and readiness endpoints."""

    def test_health_returns_200(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_ready_returns_200_when_running(self):
        app = create_app(forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/ready")

        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_health_always_exposed_even_when_metrics_disabled(self):
        config = Config(observability_metrics_enabled=False)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            health_response = client.get("/health")
            ready_response = client.get("/ready")

        assert health_response.status_code == 200
        assert ready_response.status_code == 200


class TestPrometheusMetricsEndpoint:
    """Verify Prometheus metrics endpoint."""

    def test_prometheus_endpoint_exposed_when_enabled(self):
        config = Config(observability_metrics_enabled=True)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        assert "smart_provider_requests_enqueued_total" in response.text

    def test_prometheus_endpoint_hidden_when_disabled(self):
        config = Config(observability_metrics_enabled=False)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/metrics/prometheus")

        assert response.status_code == 404

    def test_prometheus_endpoint_reflects_processed_request(self):
        config = Config(observability_metrics_enabled=True)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            response = client.get("/metrics/prometheus")

        assert response.status_code == 200
        assert "smart_provider_requests_processed_total" in response.text
        assert "smart_provider_requests_enqueued_total" in response.text


class TestGracefulShutdownIntegration:
    """Verify graceful shutdown behavior through the ingress layer."""

    def test_shutdown_rejects_new_requests(self):
        shutdown_manager = ShutdownManager()
        app = create_app(
            forwarder=StubForwarder(), shutdown_manager=shutdown_manager
        )

        with TestClient(app) as client:
            shutdown_manager.start_shutdown()
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )

        assert response.status_code == 503
        assert "shutting down" in response.json()["error"]["message"].lower()

    def test_health_check_still_works_during_shutdown(self):
        shutdown_manager = ShutdownManager()
        app = create_app(
            forwarder=StubForwarder(), shutdown_manager=shutdown_manager
        )

        with TestClient(app) as client:
            shutdown_manager.start_shutdown()
            health_response = client.get("/health")
            ready_response = client.get("/ready")

        assert health_response.status_code == 200
        assert ready_response.status_code == 503
        assert ready_response.json()["status"] == "shutting_down"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
