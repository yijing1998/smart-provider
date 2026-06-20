"""Upstream forwarder interface and an asynchronous stub.

The forwarder is responsible for sending dequeued requests to the upstream
API and returning the response. This module defines the async interface and
a stub implementation so the request pipeline can be wired up before the real
upstream integration (using litellm) is implemented.
"""

from dataclasses import dataclass
from typing import Any, Optional

from src.ingress.context import RequestContext


@dataclass(frozen=True)
class ForwardResult:
    """Result produced by the upstream forwarder.

    Attributes:
        status_code: HTTP status code returned by the upstream API.
        body: Response body; usually a dict matching the OpenAI completion
            response shape, but may also carry an error payload.
        error: Optional error message when the forwarder could not complete
            the request.
    """

    status_code: int
    body: Any
    error: Optional[str] = None


class Forwarder:
    """Stub forwarder that returns a synthetic success response.

    This allows the request pipeline to be tested end-to-end before the real
    upstream forwarder (with timeout handling, error classification, and
    litellm upstream calls) is implemented.
    """

    async def forward_async(self, context: RequestContext) -> ForwardResult:
        """Return a synthetic completion response for the given context."""
        return ForwardResult(
            status_code=200,
            body={
                "id": context.request_id,
                "object": "chat.completion",
                "model": context.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "pong"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )
