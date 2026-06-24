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
            config: Limiter configuration (rpm, window_seconds, min_interval_ms).
            clock: Callable returning the current time in seconds. Exposed for
                testing; production code should use the default monotonic clock.
        """
        self._rpm = config.rpm
        self._window_seconds = config.window_seconds
        self._min_interval_ms = config.min_interval_ms
        self._clock = clock
        self._timestamps: deque[float] = deque()
        self._last_sent_at: float | None = None
        self._lock = asyncio.Lock()

    async def is_allowed(self) -> bool:
        """Return True if a new request can be sent right now.

        This method does not consume a permit; it only inspects the current
        state of the sliding window and the minimum interval constraint.
        """
        async with self._lock:
            self._cleanup()
            if len(self._timestamps) >= self._rpm:
                return False
            return self._min_interval_wait_seconds(self._clock()) <= 0

    async def acquire(self) -> None:
        """Wait until a permit is available and consume it.

        If the current window is not full and the minimum interval has passed,
        this returns immediately. Otherwise, it asynchronously sleeps until
        both constraints are satisfied and then grants the permit.
        """
        while True:
            wait_seconds = 0.0
            async with self._lock:
                self._cleanup()
                now = self._clock()

                if len(self._timestamps) < self._rpm:
                    wait_seconds = self._min_interval_wait_seconds(now)
                    if wait_seconds <= 0:
                        self._timestamps.append(now)
                        self._last_sent_at = now
                        return
                else:
                    # Wait until the oldest timestamp leaves the window.
                    oldest = self._timestamps[0]
                    window_wait = (oldest + self._window_seconds) - now
                    if window_wait <= 0:
                        # Clock skew or edge case: drop the stale record and grant.
                        self._timestamps.popleft()
                        wait_seconds = self._min_interval_wait_seconds(now)
                        if wait_seconds <= 0:
                            self._timestamps.append(now)
                            self._last_sent_at = now
                            return
                    else:
                        wait_seconds = max(
                            window_wait,
                            self._min_interval_wait_seconds(now),
                        )

            # Release the lock while sleeping so other coroutines can proceed.
            await asyncio.sleep(wait_seconds)

    def _cleanup(self) -> None:
        """Remove timestamps that have slid outside the window."""
        cutoff = self._clock() - self._window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def _min_interval_wait_seconds(self, now: float) -> float:
        """Return the remaining seconds before the minimum interval passes.

        Returns 0.0 when no minimum interval is configured, no previous request
        has been recorded, or the configured interval has already elapsed.
        """
        if self._min_interval_ms is None or self._last_sent_at is None:
            return 0.0
        elapsed_ms = (now - self._last_sent_at) * 1000
        remaining_ms = self._min_interval_ms - elapsed_ms
        return max(0.0, remaining_ms / 1000)
