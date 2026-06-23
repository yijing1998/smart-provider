## Context

Smart-Provider 当前行为：

```
客户端请求
    model=deepseek-ai/deepseek-v4-pro
            │
            ▼
    ingress: get_model_info("deepseek-ai/deepseek-v4-pro")
            │
            ▼
    不在 litellm 静态表 → 404
```

用户期望行为（与 litellm proxy 一致）：

```
客户端请求
    model=deepseek-ai/deepseek-v4-pro
            │
            ▼
    Smart-Provider: 配置 provider=openai
            │
            ▼
    内部使用 openai/deepseek-ai/deepseek-v4-pro 调 litellm
            │
            ▼
    NVIDIA 返回响应
```

另外，当前 `_extra_body()` 只透传固定字段，导致 NVIDIA 推荐的 `chat_template_kwargs` 等参数被丢弃。

## Goals / Non-Goals

**Goals:**

- 新增 `upstream_litellm_provider` 配置，默认 `openai`。
- 对客户端发来的模型名**无条件**拼接 provider 前缀。
- 透传所有非 Smart-Provider 控制的请求参数到上游。
- 保持对现有客户端请求（如 `gpt-4o`）的兼容。

**Non-Goals:**

- 不实现 litellm proxy 式的 model alias 映射。
- 不改变 forwarder 模块接口。
- 不新增队列、限速器、熔断器行为。

## Decisions

### 1. 新增 `upstream_litellm_provider` 配置字段

**决策**：在 `Config` 顶层新增 `upstream_litellm_provider: str = Field(default="openai")`，并在 pydantic validator 中校验其属于 `LITELLM_CHAT_PROVIDERS`。

**理由**：
- 明确、可配置，用户能针对 Azure、NVIDIA 等不同上游设置不同 provider。
- fail-fast：启动时即发现非法 provider。

**替代方案**：从 `upstream_url` 推断 provider。未采纳原因：不可靠，很多 OpenAI-compatible endpoint 的 URL 无法明确推断 provider。

### 2. 在 ingress 层拼接 provider 前缀

**决策**：在 `chat_completions` 中，完成请求体解析后无条件拼接：

```python
model = f"{cfg.upstream_litellm_provider}/{completion_request.model}"
_validate_model_name(model)
```

将拼接后的 `model` 存入 `RequestContext.model`。

**理由**：
- 客户端完全不需要了解 litellm provider 前缀，Smart-Provider 统一管理。
- 后续校验和转发都使用同一个模型名，避免多处重复拼接。
- 对 forwarder 透明，无需修改 forwarder。

**替代方案**：根据是否包含 `/` 决定是否拼接。未采纳原因：用户明确要求无条件拼接，避免客户端需要感知 litellm  provider 前缀。

### 3. 透传非核心请求参数

**决策**：重写 `_extra_body()`：

```python
_CONTROLLED_FIELDS = {"model", "messages", "stream"}

def _extra_body(completion_request: CompletionRequest) -> dict[str, Any]:
    body = completion_request.model_dump(exclude_unset=True)
    return {k: v for k, v in body.items() if k not in _CONTROLLED_FIELDS}
```

**理由**：
- 简单、通用，自动支持所有 OpenAI 标准参数和上游自定义参数。
- `model`、`messages`、`stream` 由 Smart-Provider 控制，其余全部透传。

**替代方案**：继续维护白名单并补充 `chat_template_kwargs`。未采纳原因：白名单永远跟不上上游新参数，维护成本高。

**风险缓解**：
- 某些 litellm 内部字段（如 `base_url`、`api_key`、`api_version`）在 `CompletionRequest` 中也可能被设置。如果客户端在请求体里传这些，会被透传到 litellm.acompletion 的 `extra_body` 中，可能与 Smart-Provider 的控制冲突。但这些字段通常不会出现在客户端请求体中；即便出现，也应由 Smart-Provider 控制，因此需要把 `base_url`、`api_key`、`api_version`、`timeout`、`model_list` 也加入排除列表。

### 4. 排除 litellm 内部字段

**决策**：排除字段包括：`model`、`messages`、`stream`、`base_url`、`api_key`、`api_version`、`timeout`、`model_list`。

**理由**：这些字段与 Smart-Provider 的运行机制或上游目标冲突，不应由客户端请求体决定。

## Risks / Trade-offs

- **[风险] 客户端传入 `base_url`/`api_key` 等字段会改变上游目标** → 缓解：通过排除列表显式过滤。
- **[风险] 上游 provider 配置错误导致模型调错** → 缓解：启动时校验 provider 合法性；文档中说明用途。
- **[风险] 透传所有字段后，某些字段与 litellm 版本不兼容** → 缓解：litellm 会自行处理未知字段或抛出 BadRequestError，Smart-Provider 原样返回错误。
- **[权衡] 默认 `openai` 对 Azure 用户不友好** → 缓解：Azure 用户需显式设置 `SMART_PROVIDER_UPSTREAM_LITELLM_PROVIDER=azure`。
