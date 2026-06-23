## Why

Smart-Provider 使用 litellm 的 `CompletionRequest` 解析客户端请求，但该类型与 OpenAI 标准存在偏差（例如 `tools` 字段被声明为 `List[str]` 而非对象数组）。当 opencode 等严格遵循 OpenAI 规范的客户端发送 function calling 请求时，会在 ingress 层直接触发 Pydantic 校验错误并返回 400。为了隔离客户端协议格式与内部 litellm 数据格式之间的差异，需要引入一个可扩展的适配中间层，将各种客户端请求归一化为 Smart-Provider 内部使用的稳定表示。

## What Changes

- 新增客户端请求适配层（`src/ingress/adapters/`），负责将外部 OpenAI 兼容请求转换为内部可用的数据结构。
- 定义内部请求模型 `SmartProviderCompletionRequest`，正确支持 OpenAI 标准的 `tools`、`tool_choice`、`functions`、`function_call` 等字段，同时保留对其他字段的透传能力。
- 修改 `src/ingress/app.py` 的 `chat_completions`：不再直接对 litellm `CompletionRequest` 做完整校验，而是先通过适配层解析并归一化请求，再向下游传递。
- 为适配层添加单元测试，覆盖 opencode 实际发送的 tools 数组、message content parts 等场景。
- 更新 `tests/test_ingress.py` 中相关测试，确保 function calling 请求返回 200 而不是 400。

## Capabilities

### New Capabilities

- `client-request-adaptation`：将客户端发送的 OpenAI 兼容请求转换为 Smart-Provider 内部稳定请求表示，隔离客户端协议变化对内部代码的影响。

### Modified Capabilities

- `request-ingress`：调整请求解析的需求，明确 ingress 层通过适配层处理请求体，并支持 OpenAI 标准的 function calling 字段。

## Impact

- 新增代码：`src/ingress/adapters/` 目录及适配器实现、`src/ingress/models.py`（或等效内部请求模型）。
- 修改代码：`src/ingress/app.py` 的请求解析逻辑。
- 修改测试：`tests/test_ingress.py`、新增 `tests/test_ingress_adapters.py`。
- 行为变化：opencode 等客户端发送的标准 OpenAI function calling 请求可被正常接收并转发；未来新增客户端格式时可在适配层扩展，无需改动内部转发逻辑。
