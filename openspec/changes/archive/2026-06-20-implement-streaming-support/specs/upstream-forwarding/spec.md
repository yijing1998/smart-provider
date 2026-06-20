# Upstream-Forwarding Capability Delta

## ADDED Requirements

### Requirement: 上游转发层支持流式调用

Smart-Provider 的上游转发层 SHALL 提供 `stream_async()` 接口，以异步迭代器方式调用上游模型 API 的流式补全接口，并逐 chunk 返回结果。

#### Scenario: 转发流式聊天补全请求

- **WHEN** `Forwarder.stream_async()` 被调用且传入包含 `stream=true` 的上下文
- **THEN** Forwarder SHALL 调用上游流式接口并逐 chunk yield 结果

#### Scenario: 流式 chunk 保持上游结构

- **WHEN** 上游返回 chat.completion.chunk 对象
- **THEN** Forwarder SHALL 将每个 chunk 转换为 dict 后 yield，不修改其字段结构

#### Scenario: 流式调用异常传播

- **WHEN** 上游流式调用过程中抛出异常
- **THEN** Forwarder.stream_async() SHALL 将该异常抛出给调用方
