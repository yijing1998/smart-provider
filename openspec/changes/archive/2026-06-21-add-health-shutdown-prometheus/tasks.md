# Implementation Tasks

## 1. Configuration

- [x] 1.1 Add `shutdown_drain_timeout_ms` field to `src/config/schema.py` with default 30000 ms and range validation
- [x] 1.2 Update `docs/configuration.md` to document the new environment variable

## 2. Request Pipeline

- [x] 2.1 Add `drain(timeout_seconds: float)` method to `RequestProcessor` that processes queued requests until empty or timeout
- [x] 2.2 Add `is_running()` property to `RequestProcessor` for readiness checks
- [x] 2.3 Reject new submissions via `submit()` and `submit_stream()` when processor is shutting down
- [x] 2.4 Add unit tests for drain behavior, shutdown rejection, and running state

## 3. Health Checks

- [x] 3.1 Add `/health` endpoint returning `{"status": "healthy"}`
- [x] 3.2 Add `/ready` endpoint checking processor running state, shutdown flag, and queue capacity
- [x] 3.3 Ensure `/health` and `/ready` are always exposed regardless of metrics config
- [x] 3.4 Add unit tests for health and readiness endpoints

## 4. Graceful Shutdown

- [x] 4.1 Introduce `ShutdownManager` or shutdown flag accessible to ingress and processor
- [x] 4.2 Add middleware to return HTTP 503 for non-health-check requests during shutdown
- [x] 4.3 Update FastAPI lifespan to perform graceful shutdown: set flag, drain queue, stop processor
- [x] 4.4 Add unit/integration tests for graceful shutdown behavior

## 5. Prometheus Metrics

- [x] 5.1 Add `prometheus-client` to `pyproject.toml` dependencies
- [x] 5.2 Integrate Prometheus metrics registry with `MetricsCollector`
- [x] 5.3 Add `/metrics/prometheus` endpoint returning Prometheus exposition format when metrics are enabled
- [x] 5.4 Map existing metrics to Prometheus Counter/Gauge/Histogram with controlled label cardinality
- [x] 5.5 Add `request_duration_seconds`, `forward_duration_seconds`, and `queue_wait_duration_seconds` histograms
- [x] 5.6 Add unit tests for Prometheus endpoint output format and metric values

## 6. Ingress Integration

- [x] 6.1 Wire health checks, shutdown middleware, and Prometheus endpoint into `src/ingress/app.py`
- [x] 6.2 Ensure existing `/metrics` JSON endpoint remains unchanged
- [x] 6.3 Add integration tests covering all new endpoints and shutdown behavior through TestClient

## 7. Verification

- [x] 7.1 Run full test suite and ensure all 108+ tests pass
- [x] 7.2 Manually verify `/health`, `/ready`, `/metrics`, `/metrics/prometheus` endpoints with local server
- [x] 7.3 Verify graceful shutdown drains queue within configured timeout
