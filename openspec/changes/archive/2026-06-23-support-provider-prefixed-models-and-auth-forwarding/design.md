## Context

Smart-Provider 当前架构：

```
客户端请求
    │
    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ingress   │────▶│    Queue    │────▶│  Forwarder  │────▶ 上游 API
│             │     │ + Limiter   │     │             │
│ 模型校验     │     │             │     │ litellm     │
│ get_model_info│   │             │     │ acompletion │
└─────────────┘     └─────────────┘     └─────────────┘
```

当前问题：

1. **Ingress 模型校验过严**：调用 `litellm.get_model_info(model)`，只接受 litellm 静态价格表中的模型。对于 `openai/z-ai/glm-5.1` 这种 provider-prefixed 模型名，`get_model_info` 会失败，但 `litellm.acompletion()` 本身可以正常路由。
2. **Forwarder 未透传认证**：`litellm.acompletion()` 只收到 `model`、`messages`、`api_base`，没有收到 `api_key`，导致需要认证的 upstream（如 NVIDIA）会 401。

## Goals / Non-Goals

**Goals:**

- 让 Smart-Provider 接受并正确路由 litellm provider-prefixed 模型名。
- 让 Smart-Provider 将客户端 `Authorization` header 透传给上游 litellm 调用。
- 保持对现有非前缀模型名（如 `gpt-4o`）的校验行为不变。
- 保持流式与非流式两种转发路径行为一致。

**Non-Goals:**

- 不引入 litellm proxy 式的 model alias 映射功能。
- 不修改配置 schema 或增加新的环境变量。
- 不改变队列、限速器、熔断器行为。

## Decisions

### 1. 模型校验：provider 前缀用 `get_llm_provider`，无前缀回退 `get_model_info`

**决策**：在 `src/ingress/app.py` 中实现如下校验逻辑：

```python
from litellm import get_model_info, LITELLM_CHAT_PROVIDERS
from litellm.utils import get_llm_provider

def _validate_model(model: str) -> None:
    if "/" in model:
        try:
            _, provider, _, _ = get_llm_provider(model)
        except Exception as exc:
            raise NotFoundError(...)
        if provider not in LITELLM_CHAT_PROVIDERS:
            raise NotFoundError(...)
    else:
        try:
            get_model_info(model)
        except Exception as exc:
            raise NotFoundError(...)
```

**理由**：
- `get_llm_provider("openai/z-ai/glm-5.1")` 正确返回 `provider=openai`，说明 litellm 能路由该模型。
- `LITELLM_CHAT_PROVIDERS` 列出了 litellm 支持的聊天 provider，确保 provider 前缀有效。
- 无前缀模型仍走 `get_model_info`，保持向后兼容。

**替代方案**：直接移除模型校验。未采纳原因：用户明确要求不关闭校验；保留轻量校验仍可防止明显非法输入。

### 2. 认证透传：从 Authorization header 提取 Bearer token 作为 api_key

**决策**：在 `src/forwarder/forwarder.py` 的 `forward_async` 和 `stream_async` 中：

```python
api_key = None
auth = context.extra_headers.get("Authorization", "")
if auth.lower().startswith("bearer "):
    api_key = auth[7:].strip()

kwargs = {
    "model": context.model,
    "messages": context.messages,
    "api_base": context.upstream_target,
    "api_key": api_key,
}
```

**理由**：
- litellm `acompletion()` 接受 `api_key` 参数，这是最直接的方式。
- 仅提取 Bearer token，不传递其他可能干扰上游的 headers（如 `X-Client-Id`）。
- 与 litellm proxy 配置中 `api_key: os.environ/OPENAI_API_KEY` 语义等价。

**替代方案**：把 `extra_headers` 整体作为 `extra_headers` 参数传给 `acompletion()`。未采纳原因：
- `acompletion()` 没有 `headers` 参数，只有 `extra_headers`；
- 把 Smart-Provider 内部 header（如 `X-Client-Id`）传给上游可能造成副作用；
- `api_key` 是 litellm 推荐的标准方式。

### 3. 两个改动放在同一个 change

**决策**：将 ingress 校验修复和 forwarder 认证透传放在同一个 OpenSpec change。

**理由**：
- 两者共同解决“Smart-Provider 无法代理 NVIDIA NIM 这类自定义 endpoint”的同一个端到端问题。
- 单独修复任一个，端到端测试仍无法通过。

## Risks / Trade-offs

- **[风险] `get_llm_provider` 对未知 provider 抛出的异常类型不一致** → 缓解：统一包装为 `NotFoundError`。
- **[风险] Authorization header 格式不是 Bearer** → 缓解：仅当以 `Bearer ` 开头时才提取；否则 `api_key=None`，行为与当前一致（依赖 litellm 默认或环境变量）。
- **[风险] 透传 api_key 后，上游错误分类是否受影响** → 缓解：认证失败通常映射为 `AuthenticationError`，已被 ingress 的异常处理器捕获。
- **[权衡] 不支持 model alias** → 用户需直接发送 provider-prefixed 模型名（如 `openai/z-ai/glm-5.1`）。如需 alias，可后续单独实现。
