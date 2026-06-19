# Ingress 模块

`src/ingress/` 实现了 Smart-Provider 的请求接入层，是客户端与内部队列之间的桥梁。

## 职责

- 暴露 OpenAI 兼容的 `POST /v1/chat/completions` 端点。
- 使用 litellm SDK 解析请求体、校验模型名称、分类异常并记录日志。
- 将客户端请求转换为项目内部 `RequestContext`。
- 将内部上下文提交给请求队列，并在队列已满时返回 503。
- 等待上游转发结果并返回给客户端。

## 复用的 litellm 能力

| 能力 | litellm 组件 | 说明 |
|------|--------------|------|
| 请求解析 | `litellm.types.completion.CompletionRequest` | 避免自行维护 OpenAI schema。 |
| 模型校验 | `litellm.get_model_info()` | 识别未知模型并提前拒绝。 |
| 异常分类 | `litellm.exceptions.*` | 统一错误类型并映射到 HTTP 状态码。 |
| 日志记录 | `logging.getLogger("litellm")` | 与 litellm 日志命名空间保持一致。 |

## 未复用（属于其它模块）

- `litellm.completion()` / `acompletion()`：上游转发由 `src/forwarder/` 负责。
- 速率限制：由 `src/limiter/` 负责。
- 持久化队列：由 `src/queue/` 负责。

## 启动方式

```bash
.venv/bin/python -m uvicorn src.ingress.app:create_app --factory --host 0.0.0.0 --port 8080
```

## 测试

```bash
.venv/bin/python -m pytest tests/test_ingress.py -v
```
