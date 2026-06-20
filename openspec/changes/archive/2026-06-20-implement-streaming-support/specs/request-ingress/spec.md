# Request-Ingress Capability Delta

## ADDED Requirements

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
