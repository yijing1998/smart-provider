## 1. Ingress 模型校验修复

- [x] 1.1 在 `src/ingress/app.py` 中实现 `_validate_model()`，支持 provider-prefixed 模型名（使用 `litellm.utils.get_llm_provider` + `LITELLM_CHAT_PROVIDERS`），无前缀时回退 `litellm.get_model_info`
- [x] 1.2 替换原有的 `get_model_info(completion_request.model)` 直接调用为 `_validate_model()`
- [x] 1.3 在 `tests/test_ingress.py` 新增测试：provider-prefixed 模型名通过校验、无效 provider 前缀被拒绝、无前缀未知模型仍被拒绝

## 2. Forwarder 认证透传修复

- [x] 2.1 在 `src/forwarder/forwarder.py` 中新增辅助函数，从 `context.extra_headers["Authorization"]` 提取 Bearer token
- [x] 2.2 在 `forward_async()` 中将提取的 token 作为 `api_key` 传给 `litellm.acompletion()`
- [x] 2.3 在 `stream_async()` 中同样传递 `api_key`
- [x] 2.4 在 `tests/test_forwarder.py` 新增测试：验证 `api_key` 被正确提取和传递

## 3. 端到端验证

- [x] 3.1 启动 Smart-Provider 并使用 `/tmp/opencode/smart-provider.env`
- [x] 3.2 使用 curl 测试 `openai/z-ai/glm-5.1` 非流式请求通过 Smart-Provider 到达 NVIDIA
- [x] 3.3 使用 curl 测试 `openai/z-ai/glm-5.1` 流式请求
- [x] 3.4 运行完整测试套件 `pytest tests/`，确认无破坏

## 4. 文档更新

- [x] 4.1 更新 `docs/quickstart.md`：说明支持 provider-prefixed 模型名和 Authorization 透传

## 5. OpenSpec 归档

- [x] 5.1 运行 `openspec validate support-provider-prefixed-models-and-auth-forwarding` 确认变更通过验证
- [x] 5.2 归档变更
