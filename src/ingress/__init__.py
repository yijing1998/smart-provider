"""Ingress layer for Smart-Provider.

The ingress module exposes an OpenAI-compatible HTTP endpoint, parses incoming
requests with the help of the litellm SDK, builds an internal request context,
and hands the context off to the request queue.
"""

from .context import RequestContext

__all__ = ["RequestContext"]
