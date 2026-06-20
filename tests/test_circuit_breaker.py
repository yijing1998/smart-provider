"""Tests for the Smart-Provider circuit breaker."""

import pytest
from litellm.exceptions import (
    APIConnectionError,
    BadRequestError,
    InternalServerError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.config.schema import CircuitBreakerConfig


def _make_breaker(
    threshold: int = 3,
    recovery_timeout_ms: int = 1000,
    clock=None,
) -> CircuitBreaker:
    config = CircuitBreakerConfig(
        enabled=True,
        failure_threshold=threshold,
        recovery_timeout_ms=recovery_timeout_ms,
    )
    return CircuitBreaker(config, clock=clock or (lambda: 0.0))


class TestCircuitBreakerStateTransitions:
    """Verify state machine transitions."""

    def test_initial_state_is_closed(self):
        breaker = _make_breaker()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.can_execute() is True

    def test_opens_after_threshold_failures(self):
        breaker = _make_breaker(threshold=3)
        for _ in range(2):
            breaker.record_failure()
            assert breaker.state == CircuitBreakerState.CLOSED
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_closed_allows_execution(self):
        breaker = _make_breaker()
        assert breaker.can_execute() is True

    def test_open_denies_execution(self):
        breaker = _make_breaker(threshold=1)
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False

    def test_opens_after_failure_exception(self):
        breaker = _make_breaker(threshold=1)
        exc = RateLimitError(
            message="rate limited", llm_provider="openai", model="gpt-4o"
        )
        breaker.record_exception(exc)
        assert breaker.state == CircuitBreakerState.OPEN


class TestCircuitBreakerRecovery:
    """Verify recovery and half-open behavior."""

    def test_transitions_to_half_open_after_recovery_timeout(self):
        current_time = 0.0

        def clock() -> float:
            return current_time

        breaker = _make_breaker(
            threshold=1, recovery_timeout_ms=1000, clock=clock
        )
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        current_time = 1.0
        assert breaker.can_execute() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes_breaker(self):
        current_time = 0.0
        breaker = _make_breaker(
            threshold=1, recovery_timeout_ms=1, clock=lambda: current_time
        )
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        current_time = 1.0
        assert breaker.can_execute() is True
        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens_breaker(self):
        current_time = 0.0
        breaker = _make_breaker(
            threshold=1, recovery_timeout_ms=1, clock=lambda: current_time
        )
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        current_time = 1.0
        assert breaker.can_execute() is True
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

    def test_half_open_allows_only_one_probe(self):
        current_time = 0.0
        breaker = _make_breaker(
            threshold=1, recovery_timeout_ms=1, clock=lambda: current_time
        )
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        current_time = 1.0
        assert breaker.can_execute() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN
        # Subsequent calls in half-open should be denied until probe completes.
        assert breaker.can_execute() is False

    def test_success_resets_failure_count(self):
        breaker = _make_breaker(threshold=3)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerExceptionClassification:
    """Verify which exceptions count as failures."""

    @pytest.mark.parametrize(
        "exc",
        [
            RateLimitError(
                message="rate limited", llm_provider="openai", model="gpt-4o"
            ),
            ServiceUnavailableError(
                message="server error", llm_provider="openai", model="gpt-4o"
            ),
            InternalServerError(
                message="internal error", llm_provider="openai", model="gpt-4o"
            ),
            APIConnectionError(
                message="connection failed",
                llm_provider="openai",
                model="gpt-4o",
            ),
            Timeout(
                message="upstream timeout",
                llm_provider="openai",
                model="gpt-4o",
            ),
        ],
    )
    def test_upstream_errors_count_as_failures(self, exc):
        breaker = _make_breaker(threshold=1)
        breaker.record_exception(exc)
        assert breaker.state == CircuitBreakerState.OPEN

    @pytest.mark.parametrize(
        "exc",
        [
            BadRequestError(
                message="bad request", llm_provider="openai", model="gpt-4o"
            ),
            NotFoundError(
                message="not found", llm_provider="openai", model="gpt-4o"
            ),
            ValueError("unexpected error"),
        ],
    )
    def test_client_and_other_errors_do_not_count_as_failures(self, exc):
        breaker = _make_breaker(threshold=1)
        breaker.record_exception(exc)
        assert breaker.state == CircuitBreakerState.CLOSED


class TestCircuitBreakerClockInjection:
    """Verify that the clock is injectable for deterministic tests."""

    def test_fake_clock_controls_recovery(self):
        current_time = 0.0

        def clock() -> float:
            return current_time

        breaker = _make_breaker(
            threshold=1, recovery_timeout_ms=5000, clock=clock
        )
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN

        assert breaker.can_execute() is False

        current_time = 4.9
        assert breaker.can_execute() is False

        current_time = 5.0
        assert breaker.can_execute() is True
