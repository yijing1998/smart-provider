## 1. 项目与依赖准备

- [x] 1.1 初始化 Python 包结构，确认 `src/ingress/` 目录存在且可被导入。
- [x] 1.2 添加 litellm 与 FastAPI 相关依赖声明（如 `pyproject.toml` 或 `requirements.txt`）。
- [x] 1.3 创建 `src/config/` 中的配置读取桩（Ingress 实现仅需读取 `server.port`、`upstream.url`、`queue.maxSize`、`forwarder.timeout` 等配置）。

## 2. 内部请求上下文与队列接口桩

- [x] 2.1 在 `src/ingress/` 或项目公共位置定义内部请求上下文数据类。
- [x] 2.2 在 `src/queue/` 中创建队列接口桩，至少提供 `enqueue(context) -> EnqueueResult` 与 `is_full()`。
- [x] 2.3 在 `src/forwarder/` 中创建转发结果等待机制桩（如 Future 或回调接口），供 Ingress 同步等待结果。

## 3. Ingress 核心实现

- [x] 3.1 使用 FastAPI 在 `src/ingress/` 中创建应用并注册 `POST /v1/chat/completions` 端点。
- [x] 3.2 使用 litellm 的请求类型解析客户端请求体，捕获解析异常并映射为 litellm 异常类型。
- [x] 3.3 使用 litellm 的模型信息能力校验模型名称是否可识别。
- [x] 3.4 生成 requestId、clientId、enqueuedAt，构造内部请求上下文。
- [x] 3.5 调用队列入队接口；若队列已满，返回 503 错误。
- [x] 3.6 等待转发结果并将响应返回给客户端；若超时或上游错误，按 litellm 异常类型返回对应状态码。

## 4. 日志与错误处理

- [x] 4.1 集成 litellm 的日志或回调机制，记录请求接收、入队、错误事件。
- [x] 4.2 实现统一的异常处理器，将 litellm 异常映射为 HTTP 响应。
- [x] 4.3 对 `stream=true` 请求给出明确处理策略（如返回 501 暂不支持）。

## 5. 测试

- [x] 5.1 编写单元测试验证请求解析、模型校验、上下文构造与错误映射。
- [x] 5.2 使用 FastAPI TestClient 编写端点集成测试，验证请求入队与响应返回流程。
- [x] 5.3 验证队列满载时的 503 响应行为。

## 6. 文档与代码审查

- [x] 6.1 为 Ingress 模块添加模块级说明文档或 docstring。
- [x] 6.2 检查是否复用了 litellm 已提供的功能，避免重复实现。
- [x] 6.3 运行测试并修复问题，确保 Ingress 可独立启动与验证。
