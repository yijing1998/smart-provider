## ADDED Requirements

### Requirement: 透传客户端认证信息

Smart-Provider 的上游转发层 SHALL 将客户端请求 `Authorization` header 中的 Bearer token 作为 `api_key` 参数传给 `litellm.acompletion()`，使需要认证的 upstream 能够正常调用。

#### Scenario: 客户端提供 Authorization header

- **WHEN** 客户端请求包含 `Authorization: Bearer <token>`
- **THEN** Forwarder SHALL 提取 `<token>` 并作为 `api_key` 传给 `litellm.acompletion()`

#### Scenario: 客户端未提供 Authorization header

- **WHEN** 客户端请求未包含 `Authorization` header
- **THEN** Forwarder SHALL 将 `api_key=None` 传给 `litellm.acompletion()`，由 litellm 使用默认机制（如环境变量）获取密钥

## MODIFIED Requirements

### Requirement: 使用 litellm SDK 异步调用上游

Smart-Provider 的上游转发层 SHALL 使用 litellm SDK 的 acompletion() 异步调用上游模型 API。

#### Scenario: 转发聊天补全请求

- **WHEN** 一个请求获得限速器放行
- **THEN** Forwarder SHALL 调用 litellm.acompletion() 将请求发送至目标上游

#### Scenario: 非流式转发携带 api_key

- **WHEN** `Forwarder.forward_async()` 被调用且上下文中包含 `Authorization: Bearer <token>`
- **THEN** 传给 `litellm.acompletion()` 的参数 SHALL 包含 `api_key=<token>`

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

#### Scenario: 流式转发携带 api_key

- **WHEN** `Forwarder.stream_async()` 被调用且上下文中包含 `Authorization: Bearer <token>`
- **THEN** 传给 `litellm.acompletion()` 的参数 SHALL 包含 `api_key=<token>` 且 `stream=True`
