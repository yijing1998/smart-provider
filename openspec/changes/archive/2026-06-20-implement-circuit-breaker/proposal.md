# 实现熔断器（Circuit Breaker）

## Why

Smart-Provider 当前采用单进程部署，所有请求都经过同一个内存队列和单一 Worker 处理。当上游 API 因故障或限流而持续返回 429/5xx 时，请求仍不断入队、等待、重试，最终可能占满整个队列，导致服务对所有客户端都无响应。引入熔断器后，系统能在检测到上游连续异常时快速失败新请求，避免无效调用堆积，并在上游恢复后自动闭合，从而提升单进程场景下的可用性与稳定性。

## What Changes

- 新增 `src/circuit_breaker/` 模块，实现 `CircuitBreaker` 状态机：
  - 支持 `CLOSED`、`OPEN`、`HALF_OPEN` 三种状态；
  - 基于连续失败次数触发熔断；
  - 超时后自动转入半开状态，允许单个探测请求；
  - 探测成功则闭合，失败则重新打开。
- 复用已预留的配置项：`circuit_breaker_enabled`、`circuit_breaker_failure_threshold`、`circuit_breaker_recovery_timeout_ms`。
- 在 `RequestProcessor` 的 Worker 循环中，出队后、限速前检查熔断状态；若熔断打开，则立即通过 Future 返回 `ServiceUnavailableError`（503）。
- 在 `RequestProcessor` 中根据上游转发结果更新熔断器：成功调用 `record_success()`，异常调用 `record_exception()`。
- 明确熔断器只把上游/网络层错误计入失败：429、5xx、连接错误、超时；不把 400/401/404 等客户端错误计入。
- 扩展 `MetricsCollector`，暴露熔断器当前状态与熔断打开次数。
- 新增单元测试与集成测试，覆盖状态转换、半开探测、异常分类、Processor 集成等场景。
- 更新配置文档，说明熔断器相关环境变量与行为。

## Capabilities

### New Capabilities

- `circuit-breaker`：定义 Smart-Provider 在上游持续异常时如何快速失败、自动恢复，以及失败分类规则。

### Modified Capabilities

- `upstream-forwarding`：新增要求——上游转发层需将调用成功或失败结果反馈给熔断器，且只有上游/网络层错误才触发熔断计数。
- `request-pipeline`：新增要求——Processor 在请求出队后、限速器放行前检查熔断状态，熔断打开时立即返回错误，不占用限速窗口。
- `observability`：新增要求——指标端点需暴露熔断器当前状态（closed/open/half_open）与累计打开次数。

## Impact

- **新增代码**：`src/circuit_breaker/circuit_breaker.py`、`src/circuit_breaker/__init__.py`。
- **修改代码**：
  - `src/processor.py`：注入 CircuitBreaker，增加熔断检查与结果反馈逻辑；
  - `src/ingress/app.py`：创建 CircuitBreaker 并注入 Processor；
  - `src/observability/metrics.py`：增加熔断相关指标；
  - `src/config/schema.py`：必要时补充半开探测次数等可选配置。
- **新增测试**：`tests/test_circuit_breaker.py`，并在 `test_processor.py` 中补充集成用例。
- **文档更新**：`docs/configuration.md` 补充熔断器配置说明。
- **无破坏性变更**：默认 `circuit_breaker_enabled=false`，不启用时不影响现有行为。
