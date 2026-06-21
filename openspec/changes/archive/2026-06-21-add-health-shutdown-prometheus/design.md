# 健康检查、优雅关闭与 Prometheus 指标设计

## Context

Smart-Provider 目前拥有完整的核心代理能力：RPM 限速、流式响应、熔断器、上游转发。这些功能已通过单元测试验证。然而，服务尚未暴露健康检查端点，关闭时直接取消后台 Worker 会导致队列中的请求被丢弃，且指标仅以 JSON 快照形式通过 `/metrics` 返回，无法被 Prometheus 直接抓取。

本 change 在不影响现有业务功能的前提下，补齐三项运维基础能力，使 Smart-Provider 可以被负载均衡器探测、被 Prometheus 监控、被安全地滚动更新。

## Goals / Non-Goals

**Goals:**

- 提供 `/health` 与 `/ready` 端点，分别用于存活探测和就绪探测。
- 实现优雅关闭：停止接收新请求，在 30 秒默认超时内排空队列，再停止 Worker。
- 提供 `/metrics/prometheus` 端点，输出 Prometheus exposition 格式指标。
- 新增 `shutdown_drain_timeout_ms` 配置项。
- 保留现有 `/metrics` JSON 端点的行为不变。

**Non-Goals:**

- 不修改 RPM/TPM 限速逻辑。
- 不引入分布式状态或优先级队列。
- 不替换现有 `MetricsCollector` 的内部计数逻辑，仅在其上叠加 Prometheus 导出。
- 不提供 Docker 镜像构建（本 change 之后的独立 change 处理）。

## Decisions

### Decision 1：`/ready` 不依赖上游健康状态

**选择**：`/ready` 仅检查 processor worker 是否运行、服务是否未关闭、队列是否可接收请求，不调用上游 API。

**理由**：

- 健康检查本身不应消耗 RPM 配额。
- 上游故障是业务问题，应通过 Prometheus 告警处理，而不是让 K8s 把所有 Pod 都摘流。
- 熔断器打开时服务仍能正常工作（快速失败），不应标记为未就绪。

**替代方案**：将上游可用性纳入 `/ready`。被否决，因为会在上游故障时导致所有实例被摘流。

### Decision 2：优雅关闭采用“标记 + 排空 + 强制停止”三阶段

**选择**：

1. 收到关闭信号后，设置 `shutting_down` 标志。
2. 通过 middleware/dependency 让新请求返回 503。
3. 调用 `processor.drain(timeout)` 继续处理队列中的请求。
4. 超时后调用 `processor.stop()` 强制取消 Worker。

**理由**：

- 标记模式实现简单，且能立即拒绝新请求。
- 排空阶段尊重现有 `max_wait_time_ms`，避免处理已经超时的请求。
- 强制停止保证关闭不会无限阻塞。

**替代方案**：为每个请求维护独立取消令牌。被否决，因为实现复杂且收益有限。

### Decision 3：Prometheus 指标与 JSON 指标并存

**选择**：保留 `/metrics` JSON 端点，新增 `/metrics/prometheus` 端点。

**理由**：

- 现有测试和文档依赖 `/metrics` 的 JSON 输出，直接替换会造成 breaking change。
- Prometheus 社区标准路径是 `/metrics`，但为了避免冲突，使用 `/metrics/prometheus`。

**替代方案**：将 `/metrics` 改为 Prometheus 格式，JSON 移到 `/debug/metrics`。被否决，因为这会破坏现有行为。

### Decision 4：Prometheus 指标第一阶段不带高基数标签

**选择**：所有 Prometheus 指标不带 `client_id`、`model`、`request_id` 等动态标签。

**理由**：

- 第一阶段聚焦可观测性基础能力，避免标签基数爆炸导致 Prometheus 内存问题。
- 后续如果需要按客户端或模型分维度，可以在独立 change 中通过配置化标签实现。

### Decision 5：使用 `prometheus-client` 库

**选择**：使用官方 `prometheus-client` 生成 Prometheus 格式输出。

**理由**：

- 社区标准，维护活跃。
- 提供 Counter/Gauge/Histogram 等常用指标类型，与需求匹配。
- 生成 `generate_latest()` 输出简单直接。

## Risks / Trade-offs

- **风险**：优雅关闭期间，uvicorn 可能不再接收新连接，但已建立连接中的请求仍会进入 handler。
  - **缓解**：在 middleware 中检查 `shutting_down` 标志，对任何新请求返回 503。
- **风险**：排空超时设置过短，导致滚动更新时仍有大量请求失败。
  - **缓解**：提供可配置项，默认 30 秒，建议用户根据上游响应时间和队列长度调整。
- **风险**：流式请求在关闭阶段可能长时间占用 Worker。
  - **缓解**：第一阶段允许已建立的流式连接继续，后续可优化为带超时强制关闭。
- **风险**：Prometheus 指标与 JSON 指标数据不同步。
  - **缓解**：两者都从同一个 `MetricsCollector` 读取或更新，确保一致性。
- **风险**：新增 `prometheus-client` 依赖增加镜像体积。
  - **缓解**：依赖较小，且是生产环境必需。

## Migration Plan

1. 升级后，现有 `/metrics` JSON 端点行为不变。
2. 启用 `observability_metrics_enabled=true` 后，新增 `/metrics/prometheus` 端点可用。
3. 负载均衡器 / Kubernetes 可配置 `/health` 作为 liveness probe，`/ready` 作为 readiness probe。
4. 滚动更新时，Kubernetes 的 `terminationGracePeriodSeconds` 应大于 `shutdown_drain_timeout_ms`（建议至少 45-60 秒）。

## Open Questions

1. 是否需要为 `/metrics/prometheus` 增加 basic auth 或 TLS？（第一阶段不需要，后续根据部署环境决定。）
2. 是否需要将日志输出格式也改为结构化 JSON？（本 change 不包含，属于可观测性深化。）
3. 优雅关闭时，是否应主动通知队列中等待的 Future 返回 503 而不是等其自然超时？（第一阶段按现有超时逻辑处理。）
