## Why

用户尝试通过 Smart-Provider 代理 NVIDIA NIM 提供的模型（如 `z-ai/glm-5.1`、`minimaxai/minimax-m3`、`moonshotai/kimi-k2.6`）时，请求在 ingress 层被以 `Model 'z-ai/glm-5.1' is not recognized` 拒绝。这些模型在 litellm proxy 中可以通过 `openai/z-ai/glm-5.1` 等 provider-prefixed 名称正常路由，但 Smart-Provider 使用 `litellm.get_model_info()` 做静态表校验，无法理解这种格式。本次变更修复模型校验逻辑，并同步修复 forwarder 未将 `Authorization` 透传给上游的问题，使 Smart-Provider 能正确代理自定义 OpenAI-compatible endpoint。

## What Changes

- 修改 `src/ingress/app.py` 的模型校验逻辑：
  - 对带 provider 前缀的模型名（如 `openai/z-ai/glm-5.1`），使用 `litellm.utils.get_llm_provider()` 解析并校验 provider 是否有效。
  - 对不带前缀的模型名，保持现有 `litellm.get_model_info()` 校验作为向后兼容。
- 修改 `src/forwarder/forwarder.py`：
  - 从 `RequestContext.extra_headers` 中提取 `Authorization` Bearer token，作为 `api_key` 参数传给 `litellm.acompletion()`。
  - 流式与非流式转发均需传递。
- 更新 `tests/test_ingress.py` 和 `tests/test_forwarder.py`：
  - 新增 provider-prefixed 模型校验测试。
  - 新增 Authorization / api_key 透传测试。
- 更新 `docs/configuration.md` 和/或 `docs/quickstart.md`：
  - 说明支持 provider-prefixed 模型名。
  - 说明 Authorization 会被透传给上游。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `request-ingress`：扩展模型校验要求，使其支持 litellm provider-prefixed 模型名（如 `openai/z-ai/glm-5.1`），而不是仅依赖 `get_model_info` 静态表。
- `upstream-forwarding`：扩展转发要求，使其将客户端 `Authorization` header 中的 token 作为 `api_key` 透传给上游 `litellm.acompletion()` 调用。

## Impact

- 修改代码：`src/ingress/app.py`、`src/forwarder/forwarder.py`
- 修改测试：`tests/test_ingress.py`、`tests/test_forwarder.py`
- 更新文档：`docs/configuration.md` 或 `docs/quickstart.md`
- 无配置 schema 变更，无运行时依赖变更。
