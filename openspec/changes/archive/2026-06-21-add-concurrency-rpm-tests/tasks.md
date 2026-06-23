# Implementation Tasks

## 1. Setup

- [x] 1.1 Add `pytest-asyncio` and `asgi-lifespan` to `pyproject.toml` dev dependencies
- [x] 1.2 Install `pytest-asyncio` and `asgi-lifespan` into `.venv`
- [x] 1.3 Add `asyncio_mode = "auto"` and `slow` marker to pytest configuration in `pyproject.toml`
- [x] 1.4 Add async `reset_metrics` fixture to `tests/conftest.py`

## 2. Test Helpers

- [x] 2.1 Create `RecordingForwarder` test helper that records upstream call timestamps
- [x] 2.2 Create helper to assert that upstream call times respect RPM sliding window
- [x] 2.3 Create helper to build a test app with small RPM window for fast concurrency tests

## 3. Core Concurrency Tests

- [x] 3.1 Implement burst test: 20 concurrent requests with rpm=5, verify any window has ≤ 5 upstream calls
- [x] 3.2 Implement sustained load test: 100 requests over 10s with rpm=10, verify rate stability
- [x] 3.3 Implement queue backpressure test: queue_max_size=5 with 20 concurrent requests, verify 503 for overflow
- [x] 3.4 Implement queue wait timeout test: rpm=1 with 5 concurrent requests and small max_wait_ms, verify 504
- [x] 3.5 Implement mixed streaming/non-streaming test: 3 streaming + 7 non-streaming with rpm=5, verify combined quota

## 4. Integration & Verification

- [x] 4.1 Run full test suite and ensure all existing 125 tests still pass
- [x] 4.2 Run only concurrency tests and verify they pass consistently
- [x] 4.3 Run `pytest -m "not slow"` to verify slow tests can be skipped
- [x] 4.4 Review test running time and adjust tolerances if needed
