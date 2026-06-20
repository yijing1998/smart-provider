"""Sliding-window RPM rate limiter for Smart-Provider."""

import asyncio
import time
from collections import deque
from typing import Callable

from src.config.schema import LimiterConfig


class SlidingWindowRateLimiter:
    """RPM rate limiter based on a sliding time window.

    The limiter records the timestamps of granted permits and allows a new
    permit only when the number of records within the configured window is
    below the configured RPM threshold. It is safe for concurrent use from
    multiple async workers.
    """

    def __init__(
        self,
        config: LimiterConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the limiter.

        Args:
            config: Limiter configuration (rpm, window_seconds).
            clock: Callable returning the current time in seconds. Exposed for
                testing; production code should use the default monotonic clock.
        """
        self._rpm = config.rpm
        self._window_seconds = config.window_seconds
        self._clock = clock
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def is_allowed(self) -> bool:
        """Return True if a new request can be sent right now.

        This method does not consume a permit; it only inspects the current
        state of the sliding window.
        """
        async with self._lock:
            self._cleanup()
            return len(self._timestamps) < self._rpm

    async def acquire(self) -> None:
        """Wait until a permit is available and consume it.

        If the current window is not full, this returns immediately. Otherwise,
        it asynchronously sleeps until the oldest record slides out of the
        window and then grants the permit.
        """
        while True:
            async with self._lock:
                self._cleanup()
                if len(self._timestamps) < self._rpm:
                    self._timestamps.append(self._clock())
                    return

                # Wait until the oldest timestamp leaves the window.
                oldest = self._timestamps[0]
                wait_seconds = (oldest + self._window_seconds) - self._clock()
                if wait_seconds <= 0:
                    # Clock skew or edge case: drop the stale record and grant.
                    self._timestamps.popleft()
                    self._timestamps.append(self._clock())
                    return

            # Release the lock while sleeping so other coroutines can proceed.
            await asyncio.sleep(wait_seconds)

    def _cleanup(self) -> None:
        """Remove timestamps that have slid outside the window."""
        cutoff = self._clock() - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()
