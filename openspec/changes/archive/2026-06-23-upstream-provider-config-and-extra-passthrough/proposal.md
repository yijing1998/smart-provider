## Why

当前 Smart-Provider 要求客户端使用 litellm 的 provider-prefixed 模型名（如 `openai/deepseek-ai/deepseek-v4-pro`）才能通过模型校验，但 NVIDIA 等上游文档给出的是裸模型名（如 `deepseek-ai/deepseek-v4-pro`）。这破坏了 Smart-Provider“对客户端透明”的定位。同时，Ingress 的 `_extra_body()` 只透传固定字段，导致 NVIDIA 示例中的 `chat_template_kwargs` 等自定义参数被丢弃。本次变更通过配置化上游 provider 并透传所有非核心请求参数，解决这两个兼容性问题。

## What Changes

- 更新 `src/config/schema.py`：
  - 新增 `upstream_litellm_provider` 字段，默认值为 `openai`。
  - 校验该值必须在 `LITELLM_CHAT_PROVIDERS` 中。
- 更新 `src/ingress/app.py`：
  - 当客户端请求中的模型名不含 `/` 时，自动在前面拼接 `upstream_litellm_provider/`。
  - 使用拼接后的模型名进行校验并放入 `RequestContext.model`。
  - 重构 `_extra_body()`：转发 `CompletionRequest` 中除 Smart-Provider 控制字段外的所有字段。
- 更新 `tests/test_config.py`：新增 `upstream_litellm_provider` 默认值、环境变量、非法值校验测试。
- 更新 `tests/test_ingress.py`：新增裸模型名自动加前缀测试、自定义参数透传测试。
- 更新 `docs/configuration.md`：说明 `SMART_PROVIDER_UPSTREAM_LITELLM_PROVIDER` 用途。
- 更新 `.env.example`：新增 `SMART_PROVIDER_UPSTREAM_LITELLM_PROVIDER` 示例。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `configuration`：新增 `upstream_litellm_provider` 配置项，并校验其合法性。
- `request-ingress`：
  - 对裸模型名自动拼接配置的 upstream litellm provider 前缀。
  - 透传所有非核心请求参数（如 `chat_template_kwargs`）到上游。

## Impact

- 修改代码：`src/config/schema.py`、`src/ingress/app.py`
- 修改测试：`tests/test_config.py`、`tests/test_ingress.py`
- 更新文档：`docs/configuration.md`、`.env.example`
- 行为变化：客户端可直接使用 NVIDIA 文档中的裸模型名；自定义 OpenAI 请求参数不会被丢弃。
