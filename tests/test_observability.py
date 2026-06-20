"""Tests for the Smart-Provider observability module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from litellm.exceptions import RateLimitError, ServiceUnavailableError

from src.circuit_breaker import CircuitBreaker
from src.config import Config
from src.config.schema import CircuitBreakerConfig
from src.forwarder import ForwardResult, Forwarder, LitellmForwarder, StubForwarder
from src.ingress.context import RequestContext
from src.observability import MetricsCollector
from src.ingress.app import create_app


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def reset_metrics() -> None:
    """Reset the singleton metrics collector before each test."""
    _run(MetricsCollector().reset())


class TestMetricsCollector:
    """Verify in-memory metrics behavior."""

    def test_enqueue_and_dequeue_update_counters(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_enqueue()
            await metrics.record_enqueue()
            await metrics.record_dequeue(wait_ms=10.0)
            return await metrics.snapshot()

        snapshot = _run(run())

        assert snapshot["queue_size"] == 1
        assert snapshot["requests_enqueued_total"] == 2
        assert snapshot["requests_processed_total"] == 1

    def test_wait_time_stats(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_dequeue(wait_ms=10.0)
            await metrics.record_dequeue(wait_ms=30.0)
            return await metrics.snapshot()

        snapshot = _run(run())
        wait = snapshot["wait_time_ms"]

        assert wait["count"] == 2
        assert wait["total_ms"] == 40.0
        assert wait["max_ms"] == 30.0
        assert wait["avg_ms"] == 20.0

    def test_upstream_errors(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_upstream_429()
            await metrics.record_upstream_429()
            await metrics.record_upstream_5xx()
            return await metrics.snapshot()

        snapshot = _run(run())

        assert snapshot["upstream_429_total"] == 2
        assert snapshot["upstream_5xx_total"] == 1

    def test_reset_clears_all_metrics(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_enqueue()
            await metrics.record_upstream_429()
            await metrics.record_dequeue(wait_ms=5.0)
            await metrics.reset()
            return await metrics.snapshot()

        snapshot = _run(run())

        assert snapshot["queue_size"] == 0
        assert snapshot["requests_enqueued_total"] == 0
        assert snapshot["upstream_429_total"] == 0
        assert snapshot["wait_time_ms"]["count"] == 0

    def test_circuit_breaker_metrics(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_circuit_breaker_state("open", opened=True)
            await metrics.record_circuit_breaker_state("half_open")
            await metrics.record_circuit_breaker_state("closed")
            return await metrics.snapshot()

        snapshot = _run(run())

        assert snapshot["circuit_breaker_state"] == "closed"
        assert snapshot["circuit_breaker_opens_total"] == 1

    def test_streaming_metrics(self):
        metrics = MetricsCollector()

        async def run():
            await metrics.record_stream_started()
            await metrics.record_stream_started()
            await metrics.record_stream_completed()
            return await metrics.snapshot()

        snapshot = _run(run())

        assert snapshot["streams_started_total"] == 2
        assert snapshot["streams_completed_total"] == 1


class TestForwarderMetrics:
    """Verify that LitellmForwarder updates metrics on upstream errors."""

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_429_increments_counter(self, mock_acompletion):
        mock_acompletion.side_effect = [
            RateLimitError(message="rate limited", llm_provider="openai", model="gpt-4o"),
            RateLimitError(message="rate limited", llm_provider="openai", model="gpt-4o"),
        ]
        forwarder = LitellmForwarder(
            _forwarder_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            from src.ingress.context import RequestContext
            context = RequestContext(model="gpt-4o", messages=[])
            with pytest.raises(RateLimitError):
                await forwarder.forward_async(context)
            return await MetricsCollector().snapshot()

        snapshot = _run(run())
        assert snapshot["upstream_429_total"] == 2

    @patch("src.forwarder.forwarder.litellm.acompletion", new_callable=AsyncMock)
    def test_5xx_increments_counter(self, mock_acompletion):
        mock_acompletion.side_effect = [
            ServiceUnavailableError(
                message="server error", llm_provider="openai", model="gpt-4o"
            ),
            ServiceUnavailableError(
                message="server error", llm_provider="openai", model="gpt-4o"
            ),
        ]
        forwarder = LitellmForwarder(
            _forwarder_config(max_retries=1, retry_backoff_ms=10)
        )

        async def run():
            from src.ingress.context import RequestContext
            context = RequestContext(model="gpt-4o", messages=[])
            with pytest.raises(ServiceUnavailableError):
                await forwarder.forward_async(context)
            return await MetricsCollector().snapshot()

        snapshot = _run(run())
        assert snapshot["upstream_5xx_total"] == 2


class TestMetricsEndpoint:
    """Verify the /metrics HTTP endpoint."""

    def test_metrics_endpoint_exposed_when_enabled(self):
        config = Config(observability_metrics_enabled=True)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/metrics")

        assert response.status_code == 200
        body = response.json()
        assert "queue_size" in body
        assert "requests_enqueued_total" in body
        assert "requests_processed_total" in body
        assert "upstream_429_total" in body
        assert "upstream_5xx_total" in body
        assert "wait_time_ms" in body
        assert "circuit_breaker_state" in body
        assert "circuit_breaker_opens_total" in body
        assert "streams_started_total" in body
        assert "streams_completed_total" in body

    def test_metrics_endpoint_hidden_when_disabled(self):
        config = Config(observability_metrics_enabled=False)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            response = client.get("/metrics")

        assert response.status_code == 404

    def test_metrics_endpoint_reflects_processed_request(self):
        config = Config(observability_metrics_enabled=True)
        app = create_app(config=config, forwarder=StubForwarder())

        with TestClient(app) as client:
            client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            response = client.get("/metrics")

        assert response.status_code == 200
        body = response.json()
        assert body["requests_enqueued_total"] == 1
        assert body["requests_processed_total"] == 1
        assert body["queue_size"] == 0
        assert body["wait_time_ms"]["count"] == 1

    def test_metrics_endpoint_reflects_circuit_breaker_open(self):
        class FailingForwarder(Forwarder):
            async def forward_async(self, context: RequestContext) -> ForwardResult:
                raise ServiceUnavailableError(
                    message="upstream down",
                    llm_provider="openai",
                    model="gpt-4o",
                )

            async def stream_async(self, context: RequestContext):
                if False:
                    yield {}

        breaker = CircuitBreaker(
            CircuitBreakerConfig(
                enabled=True, failure_threshold=1, recovery_timeout_ms=5000
            )
        )
        config = Config(
            observability_metrics_enabled=True, circuit_breaker_enabled=True
        )
        app = create_app(
            config=config,
            forwarder=FailingForwarder(),
            circuit_breaker=breaker,
        )

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
            )
            assert response.status_code == 503
            metrics_response = client.get("/metrics")

        body = metrics_response.json()
        assert body["circuit_breaker_state"] == "open"
        assert body["circuit_breaker_opens_total"] == 1


def _forwarder_config(max_retries: int = 0, retry_backoff_ms: int = 10):
    from src.config.schema import ForwarderConfig

    return ForwarderConfig(
        timeout_ms=1000,
        max_retries=max_retries,
        retry_backoff_ms=retry_backoff_ms,
    )
