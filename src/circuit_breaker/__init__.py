"""Circuit breaker for Smart-Provider.

The circuit breaker protects the proxy from continuously calling an upstream
API that is experiencing sustained failures. When the failure threshold is
reached, new requests fail fast until the upstream recovers.
"""

from .circuit_breaker import CircuitBreaker, CircuitBreakerState

__all__ = ["CircuitBreaker", "CircuitBreakerState"]
