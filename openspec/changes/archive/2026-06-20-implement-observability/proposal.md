## Why

Smart-Provider 的核心请求处理管线（Ingress、Queue、Limiter、Processor、Forwarder）已经落地并能调用真实上游 API。但当前系统对运行时状态几乎不可见：队列有多长、已经处理多少请求、上游 429/5xx 出现了多少次、每个请求在队列中等待多久，都没有统一记录与暴露。`openspec/specs/observability/spec.md` 已定义可观测性需求，且配置 schema 中已预留 `observability_log_level` 与 `observability_metrics_enabled` 字段。本次变更将实现可观测性模块，让运维人员能够观察系统运行状态、评估限速效果，并为后续熔断器、TPM 限速等阶段提供数据基础。

## What Changes

- 新增 `src/observability/metrics.py`：实现 `MetricsCollector` 单例，维护以下内存指标：
  - `queue_size`：当前队列长度。
  - `requests_enqueued_total`：累计入队请求数。
  - `requests_processed_total`：累计完成处理请求数。
  - `upstream_429_total`：累计上游 429 次数。
  - `upstream_5xx_total`：累计上游 5xx 次数。
  - `request_wait_time_ms`：请求在队列中等待时间的统计（计数/总和/最大）。
- 在 `src/processor.py` 中接入指标与日志：
  - 入队时记录 `requests_enqueued_total` 与 `queue_size`。
  - 出队时计算等待时间，记录 `requests_processed_total`、`request_wait_time_ms`，并输出结构化日志。
  - 转发成功/失败时输出日志。
- 在 `src/forwarder/forwarder.py` 的 `LitellmForwarder` 中：
  - 对上游 429/5xx 异常调用 `MetricsCollector.record_upstream_429/5xx()`。
  - 输出包含异常类型的日志。
- 在 `src/ingress/app.py` 中新增 `/metrics` 端点，当 `cfg.observability_metrics_enabled` 为 True 时返回 JSON 指标快照。
- 根据 `cfg.observability_log_level` 在应用启动时设置 `smart-provider` logger 级别。
- 新增 `tests/test_observability.py` 验证指标计数器、等待时间统计与 `/metrics` 端点。
- 修改 `openspec/specs/observability/spec.md`，将 Purpose 从 TBD 补全，并细化指标与日志要求。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `observability`：补全 Purpose，细化核心指标、关键事件日志、等待时间记录的需求与场景。

## Impact

- 新增文件：`src/observability/metrics.py`（可能还包括 `__init__.py`）、`tests/test_observability.py`。
- 修改文件：`src/processor.py`、`src/forwarder/forwarder.py`、`src/ingress/app.py`、`openspec/specs/observability/spec.md`。
- 无破坏性 API 变更。
- 默认 `observability_metrics_enabled=false`，`/metrics` 端点默认不暴露；日志级别默认 INFO。
