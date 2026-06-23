## Context

Smart-Provider 当前在 `src/ingress/app.py` 中直接使用 litellm 的 `CompletionRequest` 解析客户端发来的 `/v1/chat/completions` 请求体。该类型对 OpenAI 标准字段的建模存在偏差，例如 `tools` 被声明为 `List[str]`，而 OpenAI 标准中 `tools` 是对象数组（`{"type": "function", "function": {...}}`）。当 opencode 这类严格遵循 OpenAI 协议的客户端发送 function calling 请求时，Pydantic 校验直接失败，Ingress 返回 400 Bad Request。

同时，未来可能接入其他客户端（如不同版本的 opencode、其他 AI IDE、自定义客户端），它们对请求字段的表达方式可能存在差异。如果直接在 Ingress 层依赖 litellm 的内部类型，任何客户端协议变化都会穿透到核心代码。

## Goals / Non-Goals

**Goals:**

- 引入一个客户端请求适配中间层，将外部 OpenAI 兼容请求归一化为 Smart-Provider 内部稳定的请求表示。
- 使 opencode 发送的标准 OpenAI function calling 请求（含 `tools`/`tool_choice`/`functions`/`function_call`）能够被正常接收并转发。
- 保持对现有非 function calling 请求的完全兼容。
- 适配层应可扩展，未来新增客户端格式时可通过添加适配器实现，无需修改 Ingress 核心逻辑。

**Non-Goals:**

- 不修改上游 forwarder 的接口或转发逻辑。
- 不实现 litellm proxy 式的 model alias 映射。
- 不引入新的队列、限速器、熔断器行为。
- 当前阶段不实现对非 OpenAI 协议（如 Anthropic、Gemini）的适配。

## Decisions

### 1. 新增内部请求模型 `SmartProviderCompletionRequest`

**决策**：在 `src/ingress/models.py` 中定义一个 Pydantic 模型，正确声明 OpenAI 标准字段：

- `model: str`
- `messages: list[...]`（使用宽松但有效的消息类型，支持 text/image/tool/function 消息）
- `stream: bool | None = None`
- `tools: list[ChatCompletionToolParam] | None = None`
- `tool_choice: str | dict | None = None`
- `functions: list | None = None`
- `function_call: str | dict | None = None`
- `extra = "allow"` 透传其他字段

**理由**：
- 完全匹配 OpenAI Chat Completion API 的字段类型。
- 通过 `model_dump(exclude_unset=True)` 可直接生成 `extra_body` 所需的字典。
- 内部代码只依赖这个稳定模型，不再受 litellm 内部类型变化影响。

**替代方案**：继续使用 litellm `CompletionRequest` 并尝试 monkey-patch 其字段类型。未采纳原因：monkey-patch 脆弱，litellm 升级后容易失效，且会让代码难以维护。

### 2. 适配层放在 `src/ingress/adapters/`

**决策**：新增 `src/ingress/adapters/openai.py`，提供 `adapt(raw_body: dict) -> SmartProviderCompletionRequest`。未来新增客户端格式时，可在同一目录下新增模块。

**理由**：
- 将协议转换逻辑与 Ingress 路由/错误处理解耦。
- 目录结构清晰，便于扩展。

**替代方案**：把适配逻辑直接写在 `chat_completions` 函数里。未采纳原因：会导致 Ingress 函数膨胀，且难以支持未来多种客户端格式。

### 3. Ingress 层保留 litellm 异常映射

**决策**：适配层校验失败时抛出 `ValueError` 或 Pydantic `ValidationError`，Ingress 层将其捕获并映射为 litellm 的 `BadRequestError`。

**理由**：
- 保持现有错误响应格式不变（OpenAI 兼容的 400 错误）。
- 与 spec 中“使用 litellm 异常类型分类错误”的要求一致。

## Risks / Trade-offs

- **[风险] 自定义模型与 OpenAI 未来 schema 不同步** → 缓解：使用 `extra = "allow"` 透传未知字段，即使模型字段不完整也不会拒绝请求；定期对照 OpenAI 文档更新模型。
- **[风险] messages 类型过于严格导致某些客户端消息被拒** → 缓解：消息字段使用较宽松的联合类型，必要时可降级为 `list[dict]` 仅做浅层结构校验。
- **[权衡] 增加一层抽象 vs. 直接修复 litellm 类型** → 抽象层带来的维护成本低于长期依赖 litellm 内部类型；且为后续多客户端支持打下基础。
