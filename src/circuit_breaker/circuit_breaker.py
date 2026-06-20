"""Circuit breaker state machine for Smart-Provider."""

from __future__ import annotations

import time
from enum import Enum, auto
from typing import Callable

from litellm.exceptions import (
    APIConnectionError,
    InternalServerError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

from src.config.schema import CircuitBreakerConfig


class CircuitBreakerState(Enum):
    """States of the circuit breaker."""

    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


class CircuitBreaker:
    """Single-process circuit breaker for upstream API protection.

    The breaker starts in the ``CLOSED`` state and tracks consecutive upstream
    failures. When the failure threshold is reached it transitions to ``OPEN``,
    causing new requests to fail fast without consuming upstream capacity. After
    the configured recovery timeout it moves to ``HALF_OPEN`` and allows a
    single probe request. A successful probe closes the breaker; a failed probe
    re-opens it.

    Only upstream/network-level errors count as failures. Client errors such as
    400 Bad Request or 404 Not Found reset the failure streak without opening
    the breaker.

    This implementation is intentionally synchronous and assumes a single worker
    context (one request processed at a time). It is safe for use from the
    Smart-Provider request processor worker loop.
    """

    _FAILURE_EXCEPTIONS = (
        RateLimitError,
        ServiceUnavailableError,
        InternalServerError,
        APIConnectionError,
        Timeout,
    )

    def __init__(
        self,
        config: CircuitBreakerConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the circuit breaker.

        Args:
            config: Breaker configuration (enabled flag, threshold,
                recovery timeout).
            clock: Callable returning the current time in seconds. Exposed for
                testing; production code should use the default monotonic clock.
        """
        self._threshold = config.failure_threshold
        self._recovery_timeout_seconds = config.recovery_timeout_ms / 1000
        self._clock = clock
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._half_open_probe_sent = False

    @property
    def state(self) -> CircuitBreakerState:
        """Return the current breaker state."""
        return self._state

    def can_execute(self) -> bool:
        """Return True if the caller is allowed to execute the request.

        In ``CLOSED`` state, execution is always allowed. In ``OPEN`` state,
        execution is denied until the recovery timeout elapses, at which point
        the breaker transitions to ``HALF_OPEN`` and allows one probe request.
        In ``HALF_OPEN`` state, only the first caller is allowed; subsequent
        callers are denied until the probe completes.
        """
        if self._state == CircuitBreakerState.CLOSED:
            return True

        if self._state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_probe_sent = False
                return self._allow_half_open_probe()
            return False

        # HALF_OPEN
        return self._allow_half_open_probe()

    def record_success(self) -> None:
        """Record a successful upstream call.

        Resets the failure streak. If the breaker is in ``HALF_OPEN`` state,
        a successful call transitions it back to ``CLOSED``.
        """
        self._failure_count = 0
        self._opened_at = None
        self._half_open_probe_sent = False
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.CLOSED

    def record_failure(self) -> None:
        """Record an upstream failure.

        Increments the consecutive failure count. If the threshold is reached
        from ``CLOSED``, or if a probe fails in ``HALF_OPEN``, the breaker
        opens.
        """
        self._failure_count += 1
        self._half_open_probe_sent = False
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._open()
        elif self._failure_count >= self._threshold:
            self._open()

    def record_exception(self, exc: Exception) -> None:
        """Classify an exception and update the breaker accordingly.

        Only upstream/network-level exceptions count as failures. Client errors
        are treated as a successful upstream interaction and reset the failure
        streak.
        """
        if isinstance(exc, self._FAILURE_EXCEPTIONS):
            self.record_failure()
        else:
            self.record_success()

    def _open(self) -> None:
        """Transition to the OPEN state."""
        self._state = CircuitBreakerState.OPEN
        self._opened_at = self._clock()

    def _should_attempt_reset(self) -> bool:
        """Return True if the recovery timeout has elapsed since opening."""
        if self._opened_at is None:
            return False
        return (self._clock() - self._opened_at) >= self._recovery_timeout_seconds

    def _allow_half_open_probe(self) -> bool:
        """Allow a single probe request in HALF_OPEN state."""
        if not self._half_open_probe_sent:
            self._half_open_probe_sent = True
            return True
        return False
