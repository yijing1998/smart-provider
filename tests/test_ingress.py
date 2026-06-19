"""Tests for the Smart-Provider ingress layer."""

import pytest
from fastapi.testclient import TestClient
from litellm.exceptions import BadRequestError, NotFoundError

from src.config import Config
from src.forwarder import ForwardResult, Forwarder
from src.ingress.app import _status_code_for_litellm_exception, create_app
from src.ingress.context import RequestContext
from src.queue import RequestQueue


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
        app = create_app(queue=queue)
        client = TestClient(app)

        response = client.post("/v1/chat/completions", json=_valid_chat_request())

        assert response.status_code == 200
        body = response.json()
        assert body["model"] == "gpt-4o"
        assert body["choices"][0]["message"]["content"] == "pong"
        assert queue.size() == 1

    def test_invalid_json_body_returns_400(self):
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/v1/chat/completions",
            json={"model": "gpt-4o"},  # missing messages
        )

        assert response.status_code == 400
        assert response.json()["error"]["type"] == "BadRequestError"

    def test_unknown_model_returns_404(self):
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "this-model-does-not-exist",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

        assert response.status_code == 404

    def test_stream_request_returns_503(self):
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

        assert response.status_code == 503

    def test_client_id_header_is_propagated_to_context(self):
        captured_contexts: list[RequestContext] = []

        class CapturingQueue(RequestQueue):
            def enqueue(self, context: RequestContext):
                captured_contexts.append(context)
                return super().enqueue(context)

        queue = CapturingQueue(max_size=10)
        app = create_app(queue=queue)
        client = TestClient(app)

        client.post(
            "/v1/chat/completions",
            json=_valid_chat_request(),
            headers={"X-Client-Id": "client-42"},
        )

        assert len(captured_contexts) == 1
        assert captured_contexts[0].client_id == "client-42"
        assert captured_contexts[0].model == "gpt-4o"
        assert captured_contexts[0].request_id
        assert captured_contexts[0].enqueued_at


class TestQueueFullBehavior:
    """Verify ingress returns 503 when the queue is at capacity."""

    def test_queue_full_returns_503(self):
        queue = RequestQueue(max_size=1)
        queue.enqueue(
            RequestContext(model="gpt-4o", messages=[{"role": "user", "content": "x"}])
        )
        app = create_app(queue=queue)
        client = TestClient(app)

        response = client.post("/v1/chat/completions", json=_valid_chat_request())

        assert response.status_code == 503
        assert "full" in response.json()["error"]["message"].lower()


class TestForwarderIntegration:
    """Verify ingress waits on and returns the forwarder result."""

    def test_forwarder_error_is_returned_as_500(self):
        class FailingForwarder(Forwarder):
            def forward(self, context: RequestContext) -> ForwardResult:
                return ForwardResult(
                    status_code=0, body=None, error="upstream unreachable"
                )

        app = create_app(
            queue=RequestQueue(max_size=10),
            forwarder=FailingForwarder(),
        )
        client = TestClient(app)

        response = client.post("/v1/chat/completions", json=_valid_chat_request())

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
        app = create_app(config=config, queue=CapturingQueue(max_size=10))
        client = TestClient(app)

        client.post("/v1/chat/completions", json=_valid_chat_request())

        assert captured_contexts[0].upstream_target == "https://custom.example.com/v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
