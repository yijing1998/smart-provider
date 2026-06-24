"""Pydantic-based configuration schema for Smart-Provider."""

from typing import Optional

from litellm import LITELLM_CHAT_PROVIDERS
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QueueConfig(BaseModel):
    """Configuration slice for the request queue."""

    max_size: int = Field(ge=1)
    max_wait_ms: int = Field(ge=1)


class LimiterConfig(BaseModel):
    """Configuration slice for the rate limiter."""

    rpm: int = Field(ge=1)
    tpm: Optional[int] = Field(default=None, ge=1)
    window_seconds: int = Field(ge=1)
    min_interval_ms: Optional[int] = Field(default=None, ge=0)


class ForwarderConfig(BaseModel):
    """Configuration slice for the upstream forwarder."""

    timeout_ms: int = Field(ge=1)
    max_retries: int = Field(ge=0)
    retry_backoff_ms: int = Field(ge=0)


class CircuitBreakerConfig(BaseModel):
    """Configuration slice for the circuit breaker (reserved for future use)."""

    enabled: bool
    failure_threshold: int = Field(ge=1)
    recovery_timeout_ms: int = Field(ge=1)


class ObservabilityConfig(BaseModel):
    """Configuration slice for observability (reserved for future use)."""

    log_level: str
    metrics_enabled: bool


class DistributedRateLimiterConfig(BaseModel):
    """Configuration slice for distributed rate limiting (reserved for future use)."""

    enabled: bool
    url: Optional[str] = None


class Config(BaseSettings):
    """Smart-Provider runtime configuration.

    Configuration values are loaded from environment variables prefixed with
    ``SMART_PROVIDER_`` and from an optional ``.env`` file in the working
    directory. All fields are validated at startup; invalid values cause the
    process to fail fast.
    """

    model_config = SettingsConfigDict(
        env_prefix="SMART_PROVIDER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    # Server / ingress
    server_port: int = Field(default=8080, ge=1, le=65535)
    client_id_header: str = Field(default="X-Client-Id", min_length=1)

    # Upstream target
    upstream_url: str = Field(default="https://api.openai.com/v1", min_length=1)
    upstream_litellm_provider: str = Field(default="openai", min_length=1)

    # Queue
    queue_max_size: int = Field(default=1000, ge=1)
    queue_max_wait_ms: int = Field(default=30000, ge=1)
    shutdown_drain_timeout_ms: int = Field(default=30000, ge=1)

    # Rate limiting
    rate_limit_rpm: int = Field(default=60, ge=1)
    rate_limit_tpm: Optional[int] = Field(default=None, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    rate_limit_min_interval_ms: Optional[int] = Field(default=None, ge=0)

    # Forwarder
    forwarder_timeout_ms: int = Field(default=30000, ge=1)
    forwarder_max_retries: int = Field(default=0, ge=0)
    forwarder_retry_backoff_ms: int = Field(default=1000, ge=0)

    # Circuit breaker (reserved for future use)
    circuit_breaker_enabled: bool = False
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1)
    circuit_breaker_recovery_timeout_ms: int = Field(default=30000, ge=1)

    # Observability (reserved for future use)
    observability_log_level: str = Field(default="INFO")
    observability_metrics_enabled: bool = False

    # Distributed rate limiter (reserved for future use)
    distributed_rate_limiter_enabled: bool = False
    distributed_rate_limiter_url: Optional[str] = None

    @field_validator("upstream_litellm_provider")
    @classmethod
    def _validate_upstream_litellm_provider(cls, value: str) -> str:
        """Validate that the provider is known to litellm."""
        if value not in LITELLM_CHAT_PROVIDERS:
            raise ValueError(
                f"upstream_litellm_provider must be one of {LITELLM_CHAT_PROVIDERS}, "
                f"got {value!r}"
            )
        return value

    @field_validator("observability_log_level")
    @classmethod
    def _normalize_log_level(cls, value: str) -> str:
        """Normalize and validate the log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(
                f"observability_log_level must be one of {allowed}, got {value!r}"
            )
        return upper

    @property
    def queue(self) -> QueueConfig:
        """Return the queue configuration slice."""
        return QueueConfig(
            max_size=self.queue_max_size,
            max_wait_ms=self.queue_max_wait_ms,
        )

    @property
    def limiter(self) -> LimiterConfig:
        """Return the rate limiter configuration slice."""
        return LimiterConfig(
            rpm=self.rate_limit_rpm,
            tpm=self.rate_limit_tpm,
            window_seconds=self.rate_limit_window_seconds,
            min_interval_ms=self.rate_limit_min_interval_ms,
        )

    @property
    def forwarder(self) -> ForwarderConfig:
        """Return the forwarder configuration slice."""
        return ForwarderConfig(
            timeout_ms=self.forwarder_timeout_ms,
            max_retries=self.forwarder_max_retries,
            retry_backoff_ms=self.forwarder_retry_backoff_ms,
        )

    @property
    def circuit_breaker(self) -> CircuitBreakerConfig:
        """Return the circuit breaker configuration slice (reserved)."""
        return CircuitBreakerConfig(
            enabled=self.circuit_breaker_enabled,
            failure_threshold=self.circuit_breaker_failure_threshold,
            recovery_timeout_ms=self.circuit_breaker_recovery_timeout_ms,
        )

    @property
    def observability(self) -> ObservabilityConfig:
        """Return the observability configuration slice (reserved)."""
        return ObservabilityConfig(
            log_level=self.observability_log_level,
            metrics_enabled=self.observability_metrics_enabled,
        )

    @property
    def distributed_rate_limiter(self) -> DistributedRateLimiterConfig:
        """Return the distributed rate limiter configuration slice (reserved)."""
        return DistributedRateLimiterConfig(
            enabled=self.distributed_rate_limiter_enabled,
            url=self.distributed_rate_limiter_url,
        )
