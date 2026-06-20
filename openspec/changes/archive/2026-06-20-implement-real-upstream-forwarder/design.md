## Context

当前 `src/forwarder/forwarder.py` 中的 `Forwarder` 是一个 stub，直接返回固定响应。`RequestProcessor` 已经能够异步调用 `forward_async()` 并通过 Future 回传结果。`src/config/schema.py` 已包含 `ForwarderConfig`（`timeout_ms`、`max_retries`、`retry_backoff_ms`），但尚未被消费。

`openspec/specs/upstream-forwarding/spec.md` 已定义：

- 限速器放行后按顺序异步转发请求。
- 使用 `litellm.acompletion()` 调用上游。
- 支持超时与错误分类。
- 通过 Future 将结果通知 Ingress。

本次变更负责落地这些规格。

## Goals / Non-Goals

**Goals:**

- 实现 `LitellmForwarder`，使用 `litellm.acompletion()` 调用真实上游。
- 支持配置化超时、重试次数、退避时间。
- 将上游错误分类为 litellm 异常类型，供 Ingress 映射为对应 HTTP 状态码。
- 保留 `StubForwarder` 供测试使用。
- 更新 `create_app()` 默认使用真实 Forwarder。
- 提供完整单元测试，避免依赖真实 API。

**Non-Goals:**

- 不实现请求/响应 Token 计数（TPM 限速后续变更）。
- 不实现熔断器或动态退避策略（后续变更）。
- 不修改 Limiter、Queue、Processor 的核心逻辑。
- 不处理流式响应（Ingress 已明确拒绝 stream 请求）。

## Decisions

### 1. `Forwarder` 作为抽象基类，`StubForwarder` 与 `LitellmForwarder` 作为实现

**决策**：将当前 `Forwarder` 重命名为 `StubForwarder`，并新增抽象 `Forwarder` 基类（只定义 `forward_async` 接口）。`LitellmForwarder` 继承基类。

**理由**：
- 明确区分接口与实现。
- 测试代码可以继续继承 `Forwarder` 做自定义 stub（如 `FailingForwarder`）。
- 生产默认使用 `LitellmForwarder`，测试注入 `StubForwarder`。

**替代方案**：直接修改现有 `Forwarder` 为真实实现。未采纳原因：现有大量测试依赖默认 stub 行为，直接替换会导致测试失败且需要外部 API Key。

### 2. 使用 `asyncio.wait_for` 控制超时

**决策**：在 `LitellmForwarder.forward_async()` 内部使用 `asyncio.wait_for(litellm.acompletion(...), timeout=...)`。

**理由**：
- 超时边界清晰，与 litellm 内部超时解耦。
- 超时可以统一抛出 `litellm.exceptions.Timeout`，与 Ingress 的异常处理器对应。
- 便于测试：可以用 `unittest.mock.AsyncMock` 模拟一个永远挂起的协程来触发超时。

**替代方案**：将 `timeout` 传给 `litellm.acompletion()`。未采纳原因：不同 litellm provider 对 timeout 参数的支持可能不一致，`asyncio.wait_for` 更通用。

### 3. 重试可恢复错误

**决策**：对以下异常进行重试：

- `APIConnectionError`（连接失败）
- `RateLimitError`（429）
- `ServiceUnavailableError`（503）
- `InternalServerError`（500）

重试次数为 `max_retries`，总尝试次数为 `max_retries + 1`。退避时间为 `retry_backoff_ms * (2 ** attempt)`。

**理由**：
- 这些错误通常具有 transient 特性，重试有意义。
- 429 重试符合 Smart-Provider 处理上游限流的场景，但需配合退避避免加剧问题。
- 客户端错误（如 400/404）不retry，避免无意义调用。

**替代方案**：所有异常都重试。未采纳原因：4xx 客户端错误重试不会成功，浪费资源。

### 4. 错误分类直接复用 litellm 异常

**决策**：`LitellmForwarder` 不自行将 HTTP 状态码映射为异常，而是让 litellm 抛出的异常自然传播。

**理由**：
- litellm 已经根据上游响应生成了 `RateLimitError`、`ServiceUnavailableError` 等异常。
- Ingress 已有异常处理器，可直接映射到 429/502/503/504/500。

**替代方案**：在 Forwarder 内部统一包装为 `ForwardResult(error=...)`。未采纳原因：会丢失 HTTP 状态码语义，所有上游错误都变成 500。

### 5. `create_app()` 默认使用 `LitellmForwarder`

**决策**：`create_app()` 在 `forwarder` 参数未提供时，使用 `LitellmForwarder(cfg.forwarder)`。

**理由**：
- README 中的启动命令直接指向 `create_app`，生产环境需要真实转发。
- 测试代码可以通过 `forwarder=StubForwarder()` 注入 stub。

**替代方案**：保留默认 stub，新增 `create_production_app()`。未采纳原因：会增加入口复杂度，且容易让生产误用 stub。

### 6. 响应体转换为 JSON-serializable dict

**决策**：将 litellm 返回的 `ModelResponse` 通过 `model_dump(mode="json")` 转换为 dict，作为 `ForwardResult.body`。

**理由**：
- `JSONResponse` 需要可序列化对象。
- `ModelResponse` 是 Pydantic 模型，自然支持 `model_dump`。

**替代方案**：直接返回 `ModelResponse` 并在 Ingress 层序列化。未采纳原因：增加 Ingress 复杂度，Forwarder 应返回与 stub 一致的形状。

## Risks / Trade-offs

- **[风险] 测试需要 mock litellm** → 缓解：新增 `tests/test_forwarder.py` 全面 mock `litellm.acompletion`；Ingress 测试注入 `StubForwarder`。
- **[风险] 生产环境缺少 API Key 导致启动后调用失败** → 缓解：这是预期行为，litellm 会给出明确错误；文档已说明需要配置环境变量。
- **[风险] 429 重试可能加剧上游压力** → 缓解：重试次数有限且带指数退避；未来熔断器变更会进一步缓解。
- **[风险] 超时与 litellm 内部超时叠加** → 缓解：只使用 `asyncio.wait_for`，不额外传 timeout 给 litellm。
- **[权衡] 默认使用真实 Forwarder vs 保留默认 stub** → 选择真实 Forwarder。理由：生产入口正确；测试调整成本一次性且可控。

## Open Questions

- 是否需要为不同上游 provider 配置不同的 API Key 前缀？litellm 会自动读取标准环境变量（如 `OPENAI_API_KEY`），当前无需额外处理。
- 是否需要在 Forwarder 中记录上游 429 事件供后续熔断器使用？当前仅记录 warning 日志；熔断器变更时会引入结构化计数。
