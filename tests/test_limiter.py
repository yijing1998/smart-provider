"""Tests for the Smart-Provider rate limiter."""

import asyncio
import time

import pytest

from src.config.schema import LimiterConfig
from src.limiter import SlidingWindowRateLimiter


async def _run(coro):
    """Helper to run an async coroutine in a sync test."""
    return await coro


def _make_limiter(rpm: int = 2, window_seconds: int = 1) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(
        LimiterConfig(rpm=rpm, window_seconds=window_seconds)
    )


class TestSlidingWindowRateLimiter:
    """Verify sliding-window RPM limiting behavior."""

    def test_immediate_allow_up_to_rpm(self):
        limiter = _make_limiter(rpm=2, window_seconds=1)

        assert asyncio.run(_run(limiter.is_allowed())) is True
        asyncio.run(_run(limiter.acquire()))
        asyncio.run(_run(limiter.acquire()))

        assert asyncio.run(_run(limiter.is_allowed())) is False

    def test_is_allowed_does_not_consume_permit(self):
        limiter = _make_limiter(rpm=1, window_seconds=1)

        for _ in range(5):
            assert asyncio.run(_run(limiter.is_allowed())) is True

        asyncio.run(_run(limiter.acquire()))

        assert asyncio.run(_run(limiter.is_allowed())) is False

    def test_window_slides_and_releases_capacity(self):
        limiter = _make_limiter(rpm=1, window_seconds=1)

        asyncio.run(_run(limiter.acquire()))
        assert asyncio.run(_run(limiter.is_allowed())) is False

        time.sleep(1.01)

        assert asyncio.run(_run(limiter.is_allowed())) is True

    def test_rpm_configuration_limits_acquisitions(self):
        limiter = _make_limiter(rpm=3, window_seconds=1)

        for _ in range(3):
            asyncio.run(_run(limiter.acquire()))

        assert asyncio.run(_run(limiter.is_allowed())) is False

    def test_concurrent_acquires_respect_rpm(self):
        rpm = 1
        window_seconds = 1
        limiter = _make_limiter(rpm=rpm, window_seconds=window_seconds)
        results: list[int] = []
        completion_times: dict[int, float] = {}

        async def acquire_and_record(index: int) -> None:
            await limiter.acquire()
            results.append(index)
            completion_times[index] = time.monotonic()

        async def run_all() -> None:
            await asyncio.gather(
                *(acquire_and_record(i) for i in range(3))
            )

        asyncio.run(run_all())

        assert len(results) == 3

        # Verify that at most one permit was granted per window period.
        sorted_times = sorted(completion_times.values())
        tolerance = 0.05
        for i in range(1, len(sorted_times)):
            assert sorted_times[i] - sorted_times[i - 1] >= window_seconds - tolerance


class TestRateLimiterClockInjection:
    """Verify that the clock is injectable for deterministic tests."""

    def test_fake_clock_advances_window(self):
        current_time = 0.0

        def fake_clock() -> float:
            return current_time

        limiter = SlidingWindowRateLimiter(
            LimiterConfig(rpm=1, window_seconds=10),
            clock=fake_clock,
        )

        asyncio.run(_run(limiter.acquire()))
        assert asyncio.run(_run(limiter.is_allowed())) is False

        current_time = 11.0
        assert asyncio.run(_run(limiter.is_allowed())) is True
