## 1. 配置扩展

- [x] 1.1 在 `src/config/schema.py` 新增 `upstream_litellm_provider` 字段，默认 `openai`
- [x] 1.2 添加 pydantic validator 校验 `upstream_litellm_provider` 属于 `LITELLM_CHAT_PROVIDERS`
- [x] 1.3 更新 `tests/test_config.py`：默认值、环境变量加载、非法值报错
- [x] 1.4 更新 `.env.example` 和 `docs/configuration.md`

## 2. Ingress 模型名自动加前缀

- [x] 2.1 在 `src/ingress/app.py` 的 `chat_completions` 中，无条件将模型名拼接为 `upstream_litellm_provider/<client-model>`
- [x] 2.2 使用拼接后的模型名进行 `_validate_model_name()` 校验并存入 `RequestContext.model`
- [x] 2.3 更新 `tests/test_ingress.py`：任意客户端模型名均被加前缀、自定义 upstream provider 也被正确使用

## 3. Ingress 请求参数全透传

- [x] 3.1 重构 `src/ingress/app.py` 的 `_extra_body()`，转发除 Smart-Provider 控制字段外的所有已设置字段
- [x] 3.2 明确排除字段：`model`、`messages`、`stream`、`base_url`、`api_key`、`api_version`、`timeout`、`model_list`
- [x] 3.3 更新 `tests/test_ingress.py`：验证 `chat_template_kwargs` 等自定义参数被透传到 `extra_body`

## 4. 验证与归档

- [x] 4.1 运行 `pytest tests/`，确认无破坏
- [x] 4.2 端到端测试：使用裸模型名 `deepseek-ai/deepseek-v4-pro` 通过 Smart-Provider 调 NVIDIA
- [x] 4.3 运行 `openspec validate upstream-provider-config-and-extra-passthrough`
- [x] 4.4 归档变更
