# streaming-support Specification

## Purpose
TBD - created by archiving change implement-streaming-support. Update Purpose after archive.
## Requirements
### Requirement: Smart-Provider 支持流式聊天补全请求

Smart-Provider SHALL 支持客户端发送 `stream=true` 的聊天补全请求，并以 Server-Sent Events（SSE）格式逐 chunk 返回上游响应。

#### Scenario: 客户端发送 stream=true 请求

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中 `stream=true`
- **THEN** Smart-Provider SHALL 返回 `text/event-stream` 响应，而不是 503

#### Scenario: SSE 输出包含多个 chunk

- **WHEN** 上游返回多个流式 chunk
- **THEN** Smart-Provider SHALL 每个 chunk 以 `data: {...}\n\n` 格式发送

#### Scenario: SSE 流正常结束

- **WHEN** 上游流式响应结束
- **THEN** Smart-Provider SHALL 发送 `data: [DONE]\n\n` 作为结束标记

### Requirement: 流式请求受 RPM 限速器保护

Smart-Provider SHALL 在放行流式请求前获取 RPM 限速器许可，使流式请求同样消耗每分钟请求数配额。

#### Scenario: 流式请求在 RPM 窗口已满时等待

- **WHEN** 客户端发送流式请求且当前 RPM 窗口已满
- **THEN** 该请求 SHALL 在队列中等待，直到限速器放行

### Requirement: 流式请求受熔断器保护

Smart-Provider SHALL 在放行流式请求前检查熔断器状态；熔断器打开时，流式请求 SHALL 返回服务不可用错误。

#### Scenario: 熔断器打开时发送流式请求

- **WHEN** 熔断器处于 OPEN 状态且客户端发送流式请求
- **THEN** Smart-Provider SHALL 返回包含 `Circuit breaker is open` 的 SSE error 事件

### Requirement: 客户端断开时停止上游流式调用

Smart-Provider SHALL 在客户端断开连接后停止向上游继续请求 chunk，并关闭流式通道。

#### Scenario: 客户端中途断开

- **WHEN** 客户端在流式响应过程中断开连接
- **THEN** Worker SHALL 停止调用上游流式接口，并关闭 `StreamHandle`

### Requirement: 流式 chunk 保持上游原始结构

Smart-Provider SHALL 在不修改 chunk 语义的前提下，将上游返回的 chunk 透传给客户端。

#### Scenario: 上游返回标准 OpenAI chunk

- **WHEN** 上游返回 OpenAI 兼容的 chat.completion.chunk 对象
- **THEN** Smart-Provider SHALL 将该对象序列化后直接发送给客户端

