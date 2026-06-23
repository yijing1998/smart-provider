"""OpenAI-compatible request adapter for Smart-Provider ingress.

This module converts raw client request bodies that follow the OpenAI Chat
Completions API into Smart-Provider's internal ``SmartProviderCompletionRequest``
model. The adapter isolates external protocol details from the rest of the
pipeline so that future client formats can be supported by adding new adapters
rather than changing ingress core logic.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.ingress.models import SmartProviderCompletionRequest


def adapt(raw_body: dict[str, Any]) -> SmartProviderCompletionRequest:
    """Adapt an OpenAI-compatible request body to the internal request model.

    Args:
        raw_body: The parsed JSON body from the client.

    Returns:
        A validated internal request model.

    Raises:
        ValidationError: If the request body does not conform to the expected
            OpenAI-compatible shape.
    """
    return SmartProviderCompletionRequest(**raw_body)
