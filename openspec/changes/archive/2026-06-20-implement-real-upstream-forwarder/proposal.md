## Why

Smart-Provider 的请求处理管线已经落地，但 `src/forwarder/forwarder.py` 仍是 stub，返回固定的 `pong` 响应。`openspec/specs/upstream-forwarding/spec.md` 要求使用 `litellm.acompletion()` 异步调用真实上游 API，并支持超时处理、错误分类与重试。只有替换为真实转发，Smart-Provider 才能从“本地演示”变成真正的模型 API 代理，验证平滑流量、降低 429 的核心价值。

## What Changes

- 在 `src/forwarder/forwarder.py` 中定义 `Forwarder` 抽象基类与 `StubForwarder` 实现（保留现有测试可用的 stub）。
- 新增 `LitellmForwarder`，使用 `litellm.acompletion()` 异步调用配置的上游 API Endpoint。
- 将 `RequestContext` 映射为 litellm 调用参数：模型、消息、上游地址、`extra_body` 中的可选参数。
- 使用 `ForwarderConfig` 中的 `timeout_ms`、`max_retries`、`retry_backoff_ms`：
  - 通过 `asyncio.wait_for` 控制单次调用超时。
  - 对可恢复错误（连接失败、5xx、429 等）进行有限重试，并按配置退避。
- 错误分类：
  - 上游 429 → `RateLimitError`
  - 上游 5xx / 连接错误 → `ServiceUnavailableError` / `APIConnectionError` / `InternalServerError`
  - 超时 → `Timeout`
- 更新 `src/ingress/app.py`：默认使用 `LitellmForwarder(cfg.forwarder)`，仍允许测试注入 stub。
- 更新 `tests/test_ingress.py`：对不依赖真实上游响应的测试统一注入 `StubForwarder`。
- 新增 `tests/test_forwarder.py`：使用 `unittest.mock` 模拟 `litellm.acompletion`，覆盖成功、超时、429、500、重试等路径。
- 修改 `openspec/specs/upstream-forwarding/spec.md`，补充重试次数与退避时间的要求。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `upstream-forwarding`：补充“上游转发层支持配置重试次数与退避时间”的需求及场景。

## Impact

- 修改文件：`src/forwarder/forwarder.py`、`src/forwarder/__init__.py`、`src/ingress/app.py`、相关测试。
- 新增文件：`tests/test_forwarder.py`。
- 无新增外部依赖（继续使用已声明的 `litellm`）。
- 部署影响：生产环境需要配置对应上游 Provider 的 API Key（如 `OPENAI_API_KEY`），由 litellm 读取。
