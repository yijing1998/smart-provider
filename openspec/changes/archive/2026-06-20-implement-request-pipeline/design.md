## Context

当前组件状态：

- `src/ingress/app.py`：接收请求、解析校验、生成 `RequestContext`、调用 `RequestQueue.enqueue()`、直接调用 `Forwarder.forward()` 返回。
- `src/queue/queue.py`：基于 list 的 FIFO stub，仅支持同步 `enqueue`/`dequeue`。
- `src/limiter/rate_limiter.py`：已实现 `SlidingWindowRateLimiter`，支持 `async acquire()` 与 `is_allowed()`。
- `src/forwarder/forwarder.py`：同步 stub，返回固定 `pong` 响应。
- `openspec/specs/upstream-forwarding/spec.md`、`request-queue/spec.md`、`response-return/spec.md` 已定义异步转发、Future 回传、限速器控制出队等行为，但代码尚未实现。

本次变更目标是把这些独立组件串成一条可运行的请求处理管线。

## Goals / Non-Goals

**Goals:**

- 实现后台 Worker（`RequestProcessor`），按限速器许可从队列取出请求并异步转发。
- 通过 `asyncio.Future` 将转发结果回传给 Ingress。
- 支持请求在队列中的最大等待超时检查。
- 将 Queue 改为支持 `async dequeue()` 的实现。
- 将 Forwarder 接口改为异步，但先保留 stub 响应。
- 通过 FastAPI `lifespan` 管理 Processor 生命周期。
- 提供完整单元测试。

**Non-Goals:**

- 不实现真实上游调用（`litellm.acompletion()`）——后续变更处理。
- 不实现多 Worker 并发转发（本次使用单 Worker，保持 FIFO 与简单性）。
- 不实现请求取消传播到上游（超时仅取消 Future，已发出的上游调用不追回）。
- 不实现 observability 指标与日志（保留现有日志）。

## Decisions

### 1. 新增独立 `RequestProcessor` 模块

**决策**：在 `src/processor.py` 中实现 `RequestProcessor`，由它持有 Queue、Limiter、Forwarder 引用并运行后台 Worker 循环。

**理由**：
- 把“组件协调”从 Ingress 中抽离，Ingress 只负责接收请求和等待结果。
- 未来扩展多 Worker、优先级队列、熔断器时，改动范围集中在 Processor。

**替代方案**：在 Ingress 端点里直接 `await limiter.acquire()` 然后转发。未采纳原因：这会让 HTTP handler 长时间持有连接，且不符合规格中 Worker + Future 的设计。

### 2. 单 Worker 循环

**决策**：Processor 内部只运行一个 Worker task，依次执行 dequeue -> acquire -> forward -> set result。

**理由**：
- 阶段 1 核心是 RPM 限速，天然是串行出队；单 Worker 保证 FIFO，避免并发带来的顺序复杂问题。
- 实现简单，测试容易。

**替代方案**：启动多个 Worker task。未采纳原因：会增加并发竞争、破坏 FIFO、提升测试复杂度；多实例并发可在后续阶段按需引入。

### 3. dequeue 在 acquire 之前

**决策**：Worker 循环顺序为 `await queue.dequeue()`，然后 `await limiter.acquire()`，再转发。

**理由**：
- 如果先 `acquire()` 再 `dequeue()`，当队列为空时会浪费一个许可（已记录时间戳但没有请求可发）。
- 先 dequeue 可以确保获得许可时一定有事可做；Limiter 仍然控制“请求何时真正离开队列并发送”，符合规格精神。

**替代方案**：先 acquire 后 dequeue，并增加 permit 释放机制。未采纳原因：当前 Limiter 没有释放接口，添加会增加复杂度。

### 4. Future 注册表由 Processor 维护

**决策**：`RequestProcessor.submit(context)` 创建 `asyncio.Future` 并注册到 `self._futures[context.request_id]`，返回该 Future；Ingress 等待 Future；Worker 设置结果后从注册表移除。

**理由**：
- `RequestContext` 保持为纯请求数据，不携带异步原语。
- 注册表便于超时/取消时清理。

**替代方案**：把 Future 放到 `RequestContext` 中。未采纳原因：污染请求模型，且 context 可能在日志、序列化中传播。

### 5. Ingress 使用 `asyncio.wait_for` 控制等待超时

**决策**：Ingress 端点用 `asyncio.wait_for(processor.submit(context), timeout=context.max_wait_time_ms / 1000)` 等待结果，超时后抛出 `TimeoutError`，再映射为 504。

**理由**：
- 统一在入口层做等待超时兜底。
- 超时后 Future 会被 `wait_for` 自动取消，Worker 后续设置结果时发现 Future 已取消可忽略。

**替代方案**：完全由 Processor 检查等待超时。未采纳原因：Processor 检查的是“从入队到出队”的等待，Ingress 层还需要覆盖“出队后到结果返回”的转发耗时；`wait_for` 更通用。

### 6. Queue 基于 `asyncio.Queue`

**决策**：将 `RequestQueue` 内部存储从 list 替换为 `asyncio.Queue`，保留 `enqueue()`、`size()`、`is_full()` 同步接口，新增 `async dequeue()`。

**理由**：
- `asyncio.Queue` 天然支持异步阻塞 dequeue，避免自旋。
- 保持现有测试接口（`max_size`、`enqueue`、`size`）不变。

**替代方案**：保留 list + `asyncio.Event`。未采纳原因：`asyncio.Queue` 更标准、更简洁。

### 7. Forwarder 先保留 stub，但接口异步化

**决策**：把 `Forwarder.forward()` 改为 `async def forward_async()`，当前实现仍返回固定响应；真实 `litellm.acompletion()` 调用在后续变更接入。

**理由**：
- 让 Processor 和 Ingress 的异步接口一次到位。
- 本次可以专注于管线集成，不被上游调用细节分散。

## Risks / Trade-offs

- **[风险] Future 注册表内存泄漏** → 缓解：Worker 设置结果/异常后 `pop`；`wait_for` 超时会取消 Future，Worker 忽略已取消 Future。
- **[风险] 单 Worker 成为吞吐瓶颈** → 缓解：阶段 1 目标是限速而非高吞吐；真实上游 LLM 调用本身延迟高，单 Worker 在 RPM 限制下通常不会成为瓶颈。后续可扩展。
- **[风险] 等待超时后上游仍被调用** → 缓解：本次接受此行为；后续可通过请求取消信号或上游 abort 优化。
- **[风险] `asyncio.Queue.qsize()` 在某些平台不可靠** → 缓解：仅用于日志/调试，不用于核心逻辑；核心逻辑依赖 `put_nowait` 抛出的 `QueueFull` 异常。
- **[权衡] 是否现在实现真实上游调用** → 选择延后。理由：降低本次变更风险，先验证管线骨架。

## Open Questions

- `RequestProcessor` 文件命名用 `processor.py` 还是 `engine.py`？两者皆可，`processor.py` 更直接表达“处理请求”的职责。
- 是否需要为 Processor 提供注入的 `limiter`？是的，与 Queue/Forwarder 一样，便于测试。
