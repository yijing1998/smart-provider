# 熔断器设计文档

## Context

Smart-Provider 当前以单进程形态运行，所有客户端请求通过同一个内存队列和单一后台 Worker 处理。上游转发层已具备重试能力，但重试只能在瞬时故障时生效；当上游 API 进入持续不可用状态（如连续返回 429、503 或连接超时）时，重试反而会加剧请求堆积，最终导致队列满、所有新请求被拒绝。

本变更引入熔断器模式：当上游连续失败达到阈值时，系统自动停止向上游发送请求，直接对新请求返回服务不可用错误；经过一段恢复时间后，系统进入半开状态，允许一个探测请求验证上游是否恢复，从而决定是否重新闭合。

## Goals / Non-Goals

**Goals：**

- 在上游持续异常时保护 Smart-Provider 自身，避免无效请求占满队列。
- 实现可配置、可测试的熔断器状态机，支持 CLOSED / OPEN / HALF_OPEN 三种状态。
- 与现有 Processor、Forwarder、Observability 模块集成，默认关闭时不影响现有行为。
- 只将上游/网络层错误计入熔断失败计数，避免客户端错误误触发熔断。

**Non-Goals：**

- 支持多进程/分布式熔断状态共享（项目已明确单进程、不横向扩展）。
- 支持按模型、客户端或上游 endpoint 细分的熔断粒度（首期只做全局熔断）。
- 实现自适应阈值或机器学习式的动态熔断策略。
- 替换现有重试逻辑，熔断器与重试将共存。

## Decisions

### 1. 熔断器位置：由 Processor 持有，Forwarder 不直接感知

- **选择**：`CircuitBreaker` 作为独立组件由 `RequestProcessor` 持有，在请求出队后、限速器放行前检查状态；`LitellmForwarder` 不直接调用熔断器，而是由 Processor 根据 Forwarder 抛出的异常统一更新熔断状态。
- **理由**：
  - Processor 是管线 orchestrator，统一处理成功/失败结果最自然。
  - 避免 Forwarder 与熔断器产生循环依赖。
  - 重试由 Forwarder 内部完成，Processor 只感知最终结果，因此一次重试耗尽只计一次失败，符合直觉。
- **替代方案**：在 Forwarder 内部嵌入熔断检查。放弃原因：请求已经占用 limiter 资源才被发现熔断，无法快速失败。

### 2. 检查时机：出队后、限速前

- **选择**：`Processor._run()` 在 `await self._queue.dequeue()` 之后、`await self._limiter.acquire()` 之前调用 `can_execute()`。
- **理由**：
  - 熔断打开时请求立即失败，不占用 RPM 窗口，把有限的上游容量留给恢复后的探测请求。
  - 也比检查队列等待超时更早，减少无效处理。
- **注意**：队列中已有的请求不会被清出，只影响新 dequeue 的请求。

### 3. 失败计数规则：连续失败达到阈值即熔断

- **选择**：使用连续失败次数（consecutive failures）作为熔断触发条件。
- **理由**：
  - 实现简单，无需维护时间窗口或滑动计数。
  - 单进程、单上游场景下，连续失败通常直接反映上游真实状态。
- **替代方案**：时间窗口内失败率。放弃原因：增加了复杂度，对单进程收益有限。

### 4. 什么异常算失败

- **选择**：仅以下 litellm 异常计入熔断失败：
  - `RateLimitError`（429）
  - `ServiceUnavailableError`（503）
  - `InternalServerError`（500）
  - `APIConnectionError`
  - `Timeout`
- **不计入**：`BadRequestError`、`NotFoundError`、`AuthenticationError` 等客户端/认证类错误。
- **理由**：熔断器目的是保护上游不被过载/故障场景拖垮，客户端错误不应导致服务拒绝其他正常请求。

### 5. 半开状态探测策略：惰性单探测

- **选择**：熔断器从 OPEN 转入 HALF_OPEN 后，只允许下一个到达的请求作为探测；若探测成功则闭合，失败则重新打开。
- **理由**：
  - 不需要主动发送探测请求，避免在没有真实流量时打扰上游。
  - 单探测最简单，避免半开状态涌入多个请求再次压垮上游。
- **替代方案**：定时主动探测。放弃原因：需要额外线程/任务，与当前单 Worker 架构不符。

### 6. 配置项复用已有预留字段

- **选择**：复用 `Config` 中已预留的：
  - `circuit_breaker_enabled`
  - `circuit_breaker_failure_threshold`
  - `circuit_breaker_recovery_timeout_ms`
- **不新增字段**：首期不增加 `half_open_max_calls` 等高级配置，保持默认单探测即可。

### 7. 指标扩展

- **选择**：在 `MetricsCollector` 中新增：
  - `circuit_breaker_state`：当前状态字符串（`closed` / `open` / `half_open`）
  - `circuit_breaker_opens_total`：累计打开次数
- **理由**：运维人员可通过 `/metrics` 观察熔断历史与当前状态，为调整阈值提供依据。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
 连续失败阈值设置过低，导致正常波动也触发熔断 | 默认 threshold=5，并提供配置项；后续根据真实流量调优。 |
| 熔断后所有请求立即失败，对客户端造成突发 503 | 这是预期行为，优于队列满导致的全面无响应；客户端应实现退避。 |
| 半开探测请求本身失败，延长了恢复时间 | 单探测策略已最小化影响；恢复超时后可再次探测。 |
| Processor 与熔断器集成后，单元测试复杂度上升 | 增加 `tests/test_circuit_breaker.py` 专注状态机测试；Processor 集成测试使用 StubForwarder 模拟失败。 |
| 当前 `MetricsCollector` 为单例，并发测试需 reset | 熔断器指标更新同样遵循该模式；测试 fixture 中 reset。 |

## Migration Plan

1. **部署**：新代码默认 `circuit_breaker_enabled=false`，无需额外操作即可平滑升级。
2. **启用**：管理员设置 `SMART_PROVIDER_CIRCUIT_BREAKER_ENABLED=true` 并调整阈值。
3. **回滚**：关闭 `circuit_breaker_enabled` 或回退到上一版本，现有非流式请求管线行为不变。

## Open Questions

1. 默认 `failure_threshold` 取 3 还是 5？当前倾向 3，对单进程更敏感。
2. 熔断打开时返回的异常消息是否需要包含恢复超时提示？当前建议简单返回 "Circuit breaker is open"。
3. 是否需要为熔断状态变化记录结构化日志？当前计划在 `smart-provider` logger 中记录 OPEN / HALF_OPEN / CLOSED 转换事件。
