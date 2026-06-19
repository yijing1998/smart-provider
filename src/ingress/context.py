"""Internal request context shared across Smart-Provider modules."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


@dataclass
class RequestContext:
    """Smart-Provider internal representation of an incoming request.

    The context is created by the ingress layer and consumed by the queue,
    rate limiter, and upstream forwarder. It is intentionally decoupled from
    litellm's request types so that the rest of the system does not depend on
    a specific SDK shape.
    """

    model: str
    messages: list[dict[str, Any]]
    request_id: str = field(default_factory=lambda: str(uuid4()))
    client_id: str = "default"
    upstream_target: str = "https://api.openai.com/v1"
    stream: bool = False
    extra_body: Optional[dict[str, Any]] = None
    extra_headers: Optional[dict[str, str]] = None
    max_wait_time_ms: int = 30000
    enqueued_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        """Ensure collections are concrete instances."""
        if self.extra_body is None:
            self.extra_body = {}
        if self.extra_headers is None:
            self.extra_headers = {}
