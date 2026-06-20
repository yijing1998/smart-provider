## Context

`src/observability/` 目前只有 `.gitkeep`。`openspec/specs/observability/spec.md` 已定义三项需求：

1. 暴露核心指标（队列长度、已处理请求数、上游 429/5xx 次数）。
2. 记录关键事件日志（入队、出队、转发成功/失败）。
3. 记录请求在队列中的等待时间。

配置 schema 中 `observability_log_level` 与 `observability_metrics_enabled` 已预留但未被消费。本次变更需要把可观测性能力接入到现有管线中。

## Goals / Non-Goals

**Goals:**

- 提供线程/协程安全的内存指标收集器。
- 在 Processor 和 Forwarder 中埋点，更新指标并输出日志。
- 按配置暴露 `/metrics` HTTP 端点。
- 按配置设置日志级别。
- 提供完整单元测试。

**Non-Goals:**

- 不引入外部时序数据库或 Prometheus 客户端库（保持零新增依赖）。
- 不实现分布式追踪。
- 不修改请求处理的核心逻辑或配置 schema。

## Decisions

### 1. MetricsCollector 为单例，使用 asyncio.Lock 保护

**决策**：`MetricsCollector` 作为单例类，内部计数器用 `asyncio.Lock` 保护，所有更新方法为 async。

**理由**：
- Processor 运行在 async Worker 中，async lock 不会阻塞事件循环。
- 单例保证 Processor 和 Forwarder 更新的是同一份指标。

**替代方案**：使用 `threading.Lock` + sync 方法。未采纳原因：项目核心路径都是 async，threading.Lock 会阻塞事件循环。

### 2. 指标快照为简单 dict，不暴露 Prometheus 格式

**决策**：`/metrics` 返回 JSON 对象，例如 `{"queue_size": 5, "requests_processed_total": 12, ...}`。

**理由**：
- 零依赖，实现简单。
- 后续如需 Prometheus，可以再加一个 `/metrics/prometheus` 端点或引入 `prometheus-client`。

**替代方案**：直接输出 Prometheus 文本格式。未采纳原因：需要额外格式处理，且非本次必要。

### 3. 日志使用 Python 标准 logging，命名空间为 `smart-provider`

**决策**：在 `src/observability/__init__.py` 或 `src/observability/logger.py` 中获取 `logging.getLogger("smart-provider")`，并在启动时设置级别为 `cfg.observability_log_level`。

**理由**：
- 标准 logging 足够记录事件。
- 使用独立命名空间，便于运维人员单独配置 handler/filter。

**替代方案**：使用结构化 JSON logger。未采纳原因：增加复杂度；标准 logging 消息已足够表达事件。

### 4. 等待时间统计仅记录“入队到出队”的时长

**决策**：在 Processor Worker 中，请求出队后立即计算 `wait_ms = now - enqueued_at`，记录到指标并写入日志。

**理由**：
- 这是评估限速器引入延迟的核心指标。
- 与 `max_wait_time_ms` 配置直接对应。

**替代方案**：也记录“入队到结果返回”的总时长。未采纳原因：总时长包含上游调用时间，受上游影响大，不能单独反映队列等待。

### 5. `/metrics` 端点仅在 `observability_metrics_enabled=True` 时注册

**决策**：`create_app()` 根据配置决定是否添加 `/metrics` 路由。

**理由**：
- 默认关闭，减少攻击面。
- 与配置字段语义一致。

**替代方案**：始终注册 `/metrics`。未采纳原因：与 `observability_metrics_enabled` 默认 false 的语义冲突。

### 6. Forwarder 中分类 429/5xx 并更新指标

**决策**：在 `LitellmForwarder.forward_async()` 的异常处理路径中，捕获 `RateLimitError` 和 `ServiceUnavailableError`/`InternalServerError`/`APIConnectionError`，分别调用 `record_upstream_429()` 和 `record_upstream_5xx()`，然后继续抛出异常。

**理由**：
- 复用 litellm 已有的异常分类。
- 指标更新不影响 Processor 后续的异常传播。

**替代方案**：在 Processor 中根据异常类型更新指标。未采纳原因：Forwarder 更贴近上游错误来源，职责更清晰。

## Risks / Trade-offs

- **[风险] 单例 MetricsCollector 在测试间共享状态** → 缓解：提供 `reset()` 方法，每个测试在 fixture 中调用。
- **[风险] 指标过多导致内存增长** → 缓解：本次仅维护少量计数器；不保存每条请求的等待时间明细，只保留统计量（count/sum/max）。
- **[风险] 日志输出过于频繁** → 缓解：使用标准 logging 级别控制；DEBUG 级详细日志，INFO 级只保留关键事件。
- **[权衡] 是否保存等待时间直方图** → 选择只保存 count/sum/max。理由：足够评估延迟，避免复杂度；后续可扩展为 histogram。

## Open Questions

- 是否需要暴露 `/health` 端点？本次不涉及，可在后续运维相关变更中考虑。
- 是否需要把指标也输出到日志？当前设计是分开的；后续如有需要可再统一。
