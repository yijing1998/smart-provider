"""Runtime configuration for Smart-Provider."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Smart-Provider runtime configuration.

    Attributes:
        upstream_url: Target upstream API endpoint address.
        rate_limit_rpm: Requests-per-minute limit enforced by the rate limiter.
        queue_max_size: Maximum number of pending requests in the queue.
        forwarder_timeout_ms: Upstream request timeout in milliseconds.
        server_port: Port the ingress HTTP server listens on.
        client_id_header: Header name used to extract the client identifier.
    """

    upstream_url: str = "https://api.openai.com/v1"
    rate_limit_rpm: int = 60
    queue_max_size: int = 1000
    forwarder_timeout_ms: int = 30000
    server_port: int = 8080
    client_id_header: str = "X-Client-Id"

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Build a Config instance from a plain dictionary.

        Only recognized keys are mapped; unknown keys are ignored so the
        configuration can evolve without breaking older deployments.
        """
        return cls(
            upstream_url=data.get("upstream_url", cls.upstream_url),
            rate_limit_rpm=int(data.get("rate_limit_rpm", cls.rate_limit_rpm)),
            queue_max_size=int(data.get("queue_max_size", cls.queue_max_size)),
            forwarder_timeout_ms=int(
                data.get("forwarder_timeout_ms", cls.forwarder_timeout_ms)
            ),
            server_port=int(data.get("server_port", cls.server_port)),
            client_id_header=data.get("client_id_header", cls.client_id_header),
        )
