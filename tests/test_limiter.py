"""Tests for the Smart-Provider rate limiter."""

import asyncio
import time

import pytest

from src.config.schema import LimiterConfig
from src.limiter import SlidingWindowRateLimiter


async def _run(coro):
    """Helper to run an async coroutine in a sync test."""
    return await coro


def _make_limiter(
    rpm: int = 2,
    window_seconds: int = 1,
    min_interval_ms: int | None = None,
) -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(
        LimiterConfig(
            rpm=rpm,
            window_seconds=window_seconds,
            min_interval_ms=min_interval_ms,
        )
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


class TestRateLimiterMinInterval:
    """Verify minimum interval between granted permits."""

    def test_no_min_interval_preserves_existing_behavior(self):
        limiter = _make_limiter(rpm=10, window_seconds=1)

        asyncio.run(_run(limiter.acquire()))
        asyncio.run(_run(limiter.acquire()))

        assert asyncio.run(_run(limiter.is_allowed())) is True

    def test_acquire_waits_when_min_interval_not_elapsed(self):
        min_interval_ms = 100
        limiter = _make_limiter(
            rpm=10, window_seconds=1, min_interval_ms=min_interval_ms
        )

        async def run():
            start = time.monotonic()
            await limiter.acquire()
            await limiter.acquire()
            elapsed_ms = (time.monotonic() - start) * 1000
            return elapsed_ms

        elapsed_ms = asyncio.run(run())
        assert elapsed_ms >= min_interval_ms - 5  # tolerance

    def test_acquire_is_immediate_when_min_interval_elapsed(self):
        min_interval_ms = 50
        limiter = _make_limiter(
            rpm=10, window_seconds=1, min_interval_ms=min_interval_ms
        )

        asyncio.run(_run(limiter.acquire()))
        time.sleep(min_interval_ms / 1000 + 0.01)

        async def run():
            start = time.monotonic()
            await limiter.acquire()
            return (time.monotonic() - start) * 1000

        elapsed_ms = asyncio.run(run())
        assert elapsed_ms < 5

    def test_is_allowed_respects_min_interval(self):
        min_interval_ms = 100
        limiter = _make_limiter(
            rpm=10, window_seconds=1, min_interval_ms=min_interval_ms
        )

        assert asyncio.run(_run(limiter.is_allowed())) is True
        asyncio.run(_run(limiter.acquire()))
        assert asyncio.run(_run(limiter.is_allowed())) is False

        time.sleep(min_interval_ms / 1000 + 0.01)
        assert asyncio.run(_run(limiter.is_allowed())) is True

    def test_concurrent_acquires_respect_min_interval(self):
        min_interval_ms = 80
        limiter = _make_limiter(
            rpm=10, window_seconds=1, min_interval_ms=min_interval_ms
        )
        completion_times: dict[int, float] = {}

        async def acquire_and_record(index: int) -> None:
            await limiter.acquire()
            completion_times[index] = time.monotonic()

        async def run_all() -> None:
            await asyncio.gather(
                *(acquire_and_record(i) for i in range(3))
            )

        asyncio.run(run_all())

        assert len(completion_times) == 3
        sorted_times = sorted(completion_times.values())
        tolerance = 0.01
        for i in range(1, len(sorted_times)):
            assert (
                sorted_times[i] - sorted_times[i - 1]
                >= min_interval_ms / 1000 - tolerance
            )

    def test_min_interval_with_fake_clock(self):
        current_time = 0.0

        def fake_clock() -> float:
            return current_time

        limiter = SlidingWindowRateLimiter(
            LimiterConfig(rpm=2, window_seconds=10, min_interval_ms=500),
            clock=fake_clock,
        )

        asyncio.run(_run(limiter.acquire()))
        assert asyncio.run(_run(limiter.is_allowed())) is False

        current_time = 0.4
        assert asyncio.run(_run(limiter.is_allowed())) is False

        current_time = 0.6
        assert asyncio.run(_run(limiter.is_allowed())) is True


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
