# 增加运维基础能力：健康检查、优雅关闭与 Prometheus 指标

## Why

Smart-Provider 的核心代理能力（RPM 限速、流式响应、熔断器）已经实现并通过测试，但当前服务缺少运行在生产环境所需的基础运维能力：没有健康检查端点供负载均衡器探测，关闭时会直接丢弃队列中的请求，且指标仅以 JSON 快照形式暴露，无法被 Prometheus 等标准监控系统采集。本 change 将补齐这三项基础能力，使 Smart-Provider 可以被安全地部署、滚动升级和监控。

## What Changes

- 新增 `/health` 存活探测端点，返回服务进程是否存活，**不调用上游 API**。
- 新增 `/ready` 就绪探测端点，返回 processor worker 是否运行、服务是否处于关闭中、队列是否可接收新请求。
- 新增优雅关闭机制：
  - 收到关闭信号后标记 shutting_down 状态，新请求返回 503。
  - 等待队列中已有请求被处理完毕后再停止 worker。
  - 默认排空超时为 30 秒，可通过 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 配置。
  - 排空过程中尊重单个请求的剩余等待时间，已超时的请求不再转发。
- 新增 `/metrics/prometheus` 端点，返回 Prometheus exposition 格式的指标。
- 保留现有 `/metrics` JSON 指标端点，行为不变。
- 在现有指标（队列大小、请求数、上游错误、等待时间、熔断器状态、流式请求数）基础上，补充 `request_duration_seconds`、`forward_duration_seconds` 等 Prometheus 直方图指标。
- 新增 `prometheus-client` 生产依赖。

## Capabilities

### New Capabilities

- `health-checks`：定义 `/health` 与 `/ready` 端点的语义、返回格式和探测失败条件。
- `graceful-shutdown`：定义关闭信号处理、shutting_down 状态、队列排空策略和超时配置。
- `prometheus-metrics`：定义 Prometheus 指标命名、类型、标签规范以及 `/metrics/prometheus` 端点的输出格式。

### Modified Capabilities

- `configuration`：新增 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 配置项，用于控制优雅关闭时的队列排空超时。
- `observability`：在现有 JSON 快照指标之外，增加 Prometheus 指标导出能力；明确现有指标如何映射为 Prometheus Counter/Gauge/Histogram。
- `request-ingress`：新增 `/health`、`/ready`、`/metrics/prometheus` 端点；新增关闭期间拒绝新请求的行为。
- `request-pipeline`：扩展 processor 生命周期，新增 `drain(timeout)` 操作以支持优雅关闭期间的队列排空。

## Impact

- **代码文件**：
  - `src/ingress/app.py`：新增端点、关闭状态中间件。
  - `src/processor.py`：新增 drain 与关闭协作逻辑。
  - `src/config/schema.py`：新增 shutdown drain timeout 配置字段。
  - `src/observability/metrics.py`：集成 Prometheus 指标注册与更新。
  - `pyproject.toml`：新增 `prometheus-client` 依赖。
- **API 变化**：新增三个端点，现有 `/metrics` JSON 端点行为不变，**非 breaking**。
- **行为变化**：关闭服务时会等待队列排空而非直接取消 worker；关闭期间新请求会收到 503。
- **测试**：需要为健康检查、优雅关闭、Prometheus 指标格式新增测试。
- **部署影响**：负载均衡器 / K8s 可以开始使用 `/health` 和 `/ready` 作为探针；Prometheus 可以开始抓取 `/metrics/prometheus`。
