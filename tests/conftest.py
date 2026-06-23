"""Shared pytest fixtures for Smart-Provider tests."""

import pytest

from src.observability import MetricsCollector


@pytest.fixture
async def reset_metrics() -> None:
    """Reset the singleton metrics collector before and after an async test."""
    await MetricsCollector().reset()
    yield
    await MetricsCollector().reset()
