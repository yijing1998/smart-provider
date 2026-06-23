# Request-Ingress Capability

## Purpose

定义客户端请求如何进入 Smart-Provider，包括协议适配、请求校验、上下文封装、健康检查与就绪探测端点、Prometheus 指标端点，以及服务关闭期间的请求拒绝行为；同时明确 Ingress 层所应遵循的技术栈约束。
## Requirements
### Requirement: 代理接收客户端请求

Smart-Provider SHALL 接收来自客户端的模型 API 请求，通过适配层将其转换为内部请求模型，然后将请求封装为内部上下文对象。

#### Scenario: 客户端发送有效请求

- **WHEN** 客户端向 Smart-Provider 发送一个符合目标上游 API 协议格式的请求
- **THEN** 请求接入层 SHALL 通过适配层成功接收该请求并生成唯一请求标识

#### Scenario: 客户端发送模型名

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中 `model` 为 `deepseek-ai/deepseek-v4-pro`
- **THEN** 请求接入层 SHALL 使用配置的 `upstream_litellm_provider` 自动拼接为 `openai/deepseek-ai/deepseek-v4-pro`，并通过模型校验

#### Scenario: 客户端发送的模型名已含斜杠

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中 `model` 为 `z-ai/glm-5.1`
- **THEN** 请求接入层 SHALL 仍然拼接为 `openai/z-ai/glm-5.1`，并通过模型校验

#### Scenario: 客户端发送 function calling 请求

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中包含标准 OpenAI 格式的 `tools` 对象数组
- **THEN** 请求接入层 SHALL 通过适配层成功解析，不返回 400 Bad Request

### Requirement: 请求上下文包含必要元数据

Smart-Provider SHALL 在请求上下文中记录请求进入系统的时间、请求标识以及客户端来源信息。

#### Scenario: 记录请求元数据

- **WHEN** 一个请求到达 Smart-Provider
- **THEN** 生成的内部上下文 SHALL 包含请求 ID、入队时间戳和客户端标识

### Requirement: 协议透传

Smart-Provider SHALL 在不修改请求语义的前提下，将客户端请求转发给上游转发层。

#### Scenario: 透传请求内容

- **WHEN** 请求接入层将请求交给上游转发层
- **THEN** 请求体、请求头和目标路径 SHALL 保持与客户端原始请求一致

#### Scenario: 透传自定义请求参数

- **WHEN** 客户端请求体中包含 `chat_template_kwargs` 等非核心参数
- **THEN** 请求接入层 SHALL 将其包含在 `extra_body` 中传递给上游转发层

### Requirement: Ingress 遵循 technology-stack 规格

Smart-Provider 的 Ingress SHALL 遵循 technology-stack capability 中定义的技术栈约束。

#### Scenario: Ingress 技术栈一致性检查

- **WHEN** 审查或实现 Ingress 模块
- **THEN** Ingress SHALL 使用 technology-stack 中指定的 Python、FastAPI、Pydantic 与 litellm SDK 实现

### Requirement: Ingress 使用 FastAPI 暴露端点

Smart-Provider 的 Ingress SHALL 使用 FastAPI 框架暴露 HTTP 端点，生产环境通过 Uvicorn 运行。

#### Scenario: 启动 Ingress 服务

- **WHEN** 启动 Smart-Provider 的 HTTP 服务
- **THEN** 系统 SHALL 通过 FastAPI 注册路由，并通过 Uvicorn 监听请求

### Requirement: Ingress 使用 litellm SDK 解析请求

Smart-Provider 的 Ingress SHALL 使用 litellm SDK 提供的请求类型或等效机制解析并验证请求语义，具体的客户端协议适配由独立的适配层负责。

#### Scenario: 解析聊天补全请求体

- **WHEN** 客户端发送 POST /v1/chat/completions
- **THEN** Ingress SHALL 先通过适配层将请求体归一化为内部稳定模型，再基于该模型进行后续校验和转发

### Requirement: Ingress 使用 litellm 异常类型分类错误

Smart-Provider 的 Ingress SHALL 使用 litellm.exceptions 下的异常类型对请求解析失败、模型校验失败、队列已满等错误进行分类。

#### Scenario: 请求体格式错误

- **WHEN** 客户端发送的请求体无法通过适配层解析为有效请求
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 BadRequestError 等价错误

#### Scenario: 模型校验失败

- **WHEN** 客户端请求的模型名在拼接 `upstream_litellm_provider` 前缀后仍不被 litellm 支持
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 NotFoundError 等价错误

### Requirement: Ingress 支持流式聊天补全请求

Smart-Provider 的 Ingress SHALL 接收 `stream=true` 的聊天补全请求，并以 `text/event-stream` 格式返回上游流式响应。

#### Scenario: 流式请求返回 SSE

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且 `stream=true`
- **THEN** Ingress SHALL 返回 `StreamingResponse`，媒体类型为 `text/event-stream`

#### Scenario: 流式请求出错时返回 SSE error 事件

- **WHEN** 流式请求在队列等待、限速或上游调用阶段失败
- **THEN** Ingress SHALL 返回一个 SSE `event: error` 帧，并在最后发送 `data: [DONE]`

#### Scenario: 客户端断开时取消流式处理

- **WHEN** 客户端在接收 SSE 过程中断开连接
- **THEN** Ingress SHALL 调用 `StreamHandle.cancel()` 通知 Worker 停止 upstream 流式调用

### Requirement: 暴露健康检查端点

Smart-Provider 的 Ingress SHALL 暴露 `/health` 端点，供外部探测服务是否存活。

#### Scenario: 访问存活探测端点

- **WHEN** 客户端发送 `GET /health`
- **THEN** Ingress SHALL 返回 HTTP 200 与 `{"status": "healthy"}`

### Requirement: 暴露就绪探测端点

Smart-Provider 的 Ingress SHALL 暴露 `/ready` 端点，供外部判断服务是否愿意接收流量。

#### Scenario: 服务就绪时访问

- **WHEN** processor worker 正在运行、服务未关闭、队列未满时访问 `GET /ready`
- **THEN** Ingress SHALL 返回 HTTP 200 与 `{"status": "ready"}`

#### Scenario: 服务未就绪时访问

- **WHEN** processor worker 未运行或服务处于 shutting_down 状态时访问 `GET /ready`
- **THEN** Ingress SHALL 返回 HTTP 503

### Requirement: 暴露 Prometheus 指标端点

Smart-Provider 的 Ingress SHALL 在指标启用时暴露 `/metrics/prometheus` 端点。

#### Scenario: 启用时访问 Prometheus 端点

- **WHEN** 指标开关启用且访问 `GET /metrics/prometheus`
- **THEN** Ingress SHALL 返回 Prometheus exposition 格式的指标文本

### Requirement: 关闭期间拒绝新请求

Smart-Provider 的 Ingress SHALL 在服务进入 shutting_down 状态后，对除健康检查外的所有新请求返回 HTTP 503。

#### Scenario: 关闭中收到聊天补全请求

- **WHEN** 服务处于 shutting_down 状态且收到 `POST /v1/chat/completions`
- **THEN** Ingress SHALL 返回 HTTP 503，不将其放入队列

#### Scenario: 关闭中仍可访问健康检查

- **WHEN** 服务处于 shutting_down 状态且收到 `GET /health` 或 `GET /ready`
- **THEN** Ingress SHALL 正常响应，以便编排系统能够探测到关闭状态

### Requirement: 健康检查端点不受指标开关控制

Smart-Provider 的 `/health` 与 `/ready` 端点 SHALL 始终暴露，不受 `observability_metrics_enabled` 配置影响。

#### Scenario: 指标关闭时访问健康端点

- **WHEN** `observability_metrics_enabled=false` 时访问 `/health` 或 `/ready`
- **THEN** Ingress SHALL 正常返回 200 或 503

