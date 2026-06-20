# Request-Ingress Capability

## Purpose

定义客户端请求如何进入 Smart-Provider，包括协议适配、请求校验、上下文封装，以及 Ingress 层所应遵循的技术栈约束。
## Requirements
### Requirement: 代理接收客户端请求
Smart-Provider SHALL 接收来自客户端的模型 API 请求，并将请求封装为内部上下文对象。

#### Scenario: 客户端发送有效请求
- **WHEN** 客户端向 Smart-Provider 发送一个符合目标上游 API 协议格式的请求
- **THEN** 请求接入层 SHALL 成功接收该请求并生成唯一请求标识

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

Smart-Provider 的 Ingress SHALL 使用 litellm SDK 提供的请求类型解析客户端请求体，而不是自行实现 OpenAI 请求 schema。

#### Scenario: 解析聊天补全请求体

- **WHEN** 客户端发送 POST /v1/chat/completions
- **THEN** Ingress SHALL 使用 litellm 提供的 CompletionRequest 或等效类型解析请求体

### Requirement: Ingress 使用 litellm 异常类型分类错误

Smart-Provider 的 Ingress SHALL 使用 litellm.exceptions 下的异常类型对请求解析失败、模型校验失败、队列已满等错误进行分类。

#### Scenario: 请求体格式错误

- **WHEN** 客户端发送的请求体无法被 litellm 请求类型解析
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 BadRequestError 等价错误

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

