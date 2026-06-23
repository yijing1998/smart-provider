## 1. 定义内部请求模型

- [x] 1.1 创建 `src/ingress/models.py`，定义 `SmartProviderCompletionRequest` Pydantic 模型
- [x] 1.2 正确声明 `tools`、`tool_choice`、`functions`、`function_call` 等 OpenAI 标准字段类型
- [x] 1.3 设置 `extra="allow"` 以透传未知字段

## 2. 实现 OpenAI 请求适配器

- [x] 2.1 创建 `src/ingress/adapters/openai.py`，实现 `adapt(raw_body: dict) -> SmartProviderCompletionRequest`
- [x] 2.2 适配器处理标准 OpenAI `tools` 对象数组
- [x] 2.3 适配器处理 `tool_choice`、`functions`、`function_call` 字段
- [x] 2.4 适配器在解析失败时抛出清晰的 `ValueError`/`ValidationError`

## 3. 修改 Ingress 请求解析流程

- [x] 3.1 修改 `src/ingress/app.py` 的 `chat_completions`，使用适配器替代直接的 `CompletionRequest(**raw_body)`
- [x] 3.2 基于 `SmartProviderCompletionRequest` 构建 `RequestContext` 和 `extra_body`
- [x] 3.3 保留现有 litellm 异常映射（BadRequestError、NotFoundError 等）
- [x] 3.4 移除临时调试日志（`Raw request body`）

## 4. 补测试

- [x] 4.1 新增 `tests/test_ingress_adapters.py`：覆盖 tools 对象数组、tool_choice、functions、额外字段透传
- [x] 4.2 更新 `tests/test_ingress.py`：添加 function calling 请求返回 200 的端到端测试
- [x] 4.3 更新 `tests/test_ingress.py`：确保无效请求仍返回 400

## 5. 验证与归档

- [x] 5.1 运行 `pytest tests/`，确认无破坏
- [x] 5.2 使用 opencode 实际请求验证 tools 兼容性
- [x] 5.3 运行 `openspec validate fix-openai-tools-compatibility`
- [x] 5.4 归档变更
