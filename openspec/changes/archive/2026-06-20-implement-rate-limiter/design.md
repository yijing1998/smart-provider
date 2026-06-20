## Context

当前 `src/limiter/` 为空，仅存在 `.gitkeep`。`openspec/specs/rate-limiting/spec.md` 已经定义：

- 使用滑动时间窗口统计最近一分钟内已发送请求数。
- 根据配置的 RPM 限制决定是否放行。
- RPM 限制值可配置。

但规格未定义限速器对外接口与并发语义。本次变更需要在不改动 Ingress、Queue、Forwarder 的前提下，实现一个可独立测试、可被后续 Worker 调用的限速器模块。

## Goals / Non-Goals

**Goals:**

- 实现基于滑动时间窗口的 RPM 限速器。
- 提供异步接口 `async acquire()` 与同步查询 `is_allowed()`。
- 保证并发安全，支持多 worker 同时请求放行。
- 通过 `Config.limiter` 组件视图读取配置。
- 提供完整单元测试。

**Non-Goals:**

- 不实现按客户端、按模型、按 Endpoint 的差异化限速。
- 不实现 TPM 限速。
- 不实现与 Queue / Forwarder / Ingress 的集成（后续变更处理）。
- 不实现分布式共享限速状态（当前为单进程内存实现）。

## Decisions

### 1. 使用滑动窗口而非固定窗口

**决策**：`SlidingWindowRateLimiter` 内部维护一个按时间排序的已放行请求时间戳列表（或计数器桶），判断时剔除窗口外的旧记录。

**理由**：
- 与 `openspec/specs/rate-limiting/spec.md` 要求一致。
- 避免固定窗口在边界处出现双倍突发流量。

**替代方案**：令牌桶。未采纳原因：规格明确使用滑动窗口；令牌桶更侧重平滑突发，而 sliding window 更直接对应“最近一分钟已发送请求数”。

### 2. 接口设计：`async acquire()` + `is_allowed()`

**决策**：
- `is_allowed() -> bool`：立即返回当前是否可放行，不等待。
- `async acquire() -> None`：如果当前不可放行，则异步等待直到窗口容量释放；若当前可放行，立即返回并记录本次放行。

**理由**：
- `is_allowed` 便于 Worker 做非阻塞轮询或快速拒绝。
- `acquire` 便于 Worker 做阻塞式流量控制，代码更简洁。
- 异步接口与未来 async worker / async forwarder 一致。

**替代方案**：仅提供同步 `try_acquire()`。未采纳原因：后续 Worker 需要等待放行，异步等待更自然，避免忙等。

### 3. 并发安全使用 `asyncio.Lock`

**决策**：在 `acquire()` 和 `is_allowed()` 内部使用 `asyncio.Lock` 保护共享状态（时间戳列表）。

**理由**：
- 后续 Worker 大概率运行在 async 事件循环中。
- `asyncio.Lock` 不会阻塞事件循环线程。

**替代方案**：使用 `threading.Lock`。未采纳原因：项目整体采用 async（FastAPI + litellm.acompletion），`threading.Lock` 在 async 代码中会造成线程阻塞。

### 4. 配置通过 `Config.limiter` 注入

**决策**：`SlidingWindowRateLimiter` 构造函数接收 `LimiterConfig`（即 `config.limiter`），而不是直接读取环境变量。

**理由**：
- 与现有组件视图设计一致，降低与全局 `Config` 的耦合。
- 便于测试时注入不同的 RPM / 窗口配置。

### 5. 窗口精度：秒级桶 vs 逐时间戳

**决策**：使用逐时间戳列表（或双端队列）记录每次放行的时间点，判断时过滤窗口外记录。

**理由**：
- 实现直观，内存占用在 RPM 范围内可接受（最多保存窗口内的请求数条记录）。
- 精度高，不受桶大小影响。

**替代方案**：秒级计数桶。未采纳原因：虽然内存更省，但实现稍复杂，且当前阶段 RPM 不会极高。

## Risks / Trade-offs

- **[风险] 并发竞争激烈时性能下降** → 缓解：所有状态操作在 `asyncio.Lock` 内完成，单次判断为 O(n)，n 为窗口内请求数；对于典型 RPM（<10k）可接受。未来如成为瓶颈，可优化为桶计数或令牌桶。
- **[风险] 单进程内存状态无法支持多实例** → 缓解：本次变更有意限定为单进程实现；分布式限速在路线图第 5 阶段，届时会引入外部存储。
- **[风险] `acquire()` 无限等待导致请求悬挂** → 缓解：本次实现提供基础 `acquire()`；调用方（后续 Worker）可配合 `asyncio.wait_for` 或请求等待超时机制控制最长等待时间。
- **[权衡] 是否在本次变更中集成 Queue / Forwarder** → 选择不集成。理由：降低变更复杂度，先让 Limiter 可独立测试和 review；集成变更作为下一步。
