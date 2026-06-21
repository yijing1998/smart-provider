"""Shutdown coordination for Smart-Provider.

The :class:`ShutdownManager` provides a shared flag that the ingress layer
and the request processor can use to coordinate graceful shutdown.
"""

from __future__ import annotations

import asyncio


class ShutdownManager:
    """Shared shutdown flag for ingress and processor.

    The manager starts in the running state. Once :meth:`start_shutdown` is
    called, :attr:`is_shutting_down` becomes ``True`` and remains ``True``
    for the lifetime of the process.
    """

    def __init__(self) -> None:
        self._event = asyncio.Event()

    def start_shutdown(self) -> None:
        """Signal that the service is shutting down."""
        self._event.set()

    @property
    def is_shutting_down(self) -> bool:
        """Return True once shutdown has been initiated."""
        return self._event.is_set()
