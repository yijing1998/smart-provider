# Upstream-Forwarding Capability

## Purpose

定义 Smart-Provider 如何以可控速率将请求转发至真实上游模型 API，包括异步调用、超时处理、错误分类与结果回传机制。
## Requirements
### Requirement: 按放行顺序异步转发请求

Smart-Provider SHALL 在限速器放行后，按顺序以异步方式将请求转发至配置的上游 API Endpoint。

#### Scenario: 请求获得放行

- **WHEN** 限速器允许一个请求出队
- **THEN** 上游转发层 SHALL 以异步方式将该请求发送至目标上游 API Endpoint

### Requirement: 维护异步上游连接状态

Smart-Provider SHALL 以异步方式管理与上游 API 的连接，并支持合理的超时设置。

#### Scenario: 上游响应超时

- **WHEN** 上游 API 在配置的超时时间内未返回响应
- **THEN** 上游转发层 SHALL 将该请求标记为超时，并将超时结果返回给客户端

### Requirement: 使用 litellm SDK 异步调用上游

Smart-Provider 的上游转发层 SHALL 使用 litellm SDK 的 acompletion() 异步调用上游模型 API。

#### Scenario: 转发聊天补全请求

- **WHEN** 一个请求获得限速器放行
- **THEN** Forwarder SHALL 调用 litellm.acompletion() 将请求发送至目标上游

#### Scenario: 非流式转发携带 api_key

- **WHEN** `Forwarder.forward_async()` 被调用且上下文中包含 `Authorization: Bearer <token>`
- **THEN** 传给 `litellm.acompletion()` 的参数 SHALL 包含 `api_key=<token>`

### Requirement: 通过异步机制将结果返回给 Ingress

Smart-Provider 的上游转发层 SHALL 在获得上游响应后，通过异步机制（如 asyncio.Future）将结果通知给等待中的 Ingress。

#### Scenario: 转发成功

- **WHEN** 上游 API 返回成功响应
- **THEN** Forwarder SHALL 通过 Future 设置结果，Ingress 收到结果后返回给客户端

#### Scenario: 转发失败

- **WHEN** 上游 API 返回错误或发生异常
- **THEN** Forwarder SHALL 通过 Future 设置异常或错误结果，Ingress 据此返回错误响应

### Requirement: 复用 litellm 异常类型分类上游错误

Smart-Provider SHALL 将上游返回的错误按类型分类，至少区分限流类错误（429）与其他服务端错误（5xx），并复用 litellm.exceptions 中的异常类型。

#### Scenario: 上游返回 429

- **WHEN** 上游 API 返回 429 Too Many Requests
- **THEN** 系统 SHALL 记录该事件，并可作为调整限速策略或触发退避的依据

#### Scenario: 上游返回 5xx

- **WHEN** 上游 API 返回 5xx 服务端错误
- **THEN** 系统 SHALL 将该错误映射为 litellm 的 InternalServerError 或 ServiceUnavailableError 等价类型

### Requirement: 上游转发层支持配置重试次数

Smart-Provider 的上游转发层 SHALL 支持配置请求失败后的最大重试次数。

#### Scenario: 配置最大重试次数

- **WHEN** 管理员配置 `forwarder_max_retries` 为 3
- **THEN** 上游转发层 SHALL 在首次调用失败后最多再重试 3 次

#### Scenario: 重试次数耗尽后返回错误

- **WHEN** 上游 API 持续返回 500 且 `forwarder_max_retries` 为 1
- **THEN** 上游转发层 SHALL 在两次尝试均失败后向上游抛出或返回错误，不再继续重试

### Requirement: 上游转发层支持配置重试退避时间

Smart-Provider 的上游转发层 SHALL 支持配置重试退避基数，并在每次重试时按指数退避增加等待时间。

#### Scenario: 按退避基数等待后重试

- **WHEN** 管理员配置 `forwarder_retry_backoff_ms` 为 1000
- **THEN** 上游转发层 SHALL 在第一次重试前至少等待 1000 毫秒，后续重试等待时间按指数增长

### Requirement: 上游转发结果用于驱动熔断器

Smart-Provider 的上游转发层 SHALL 通过返回结果或抛出异常的方式，将每次上游调用的成败及错误类型反馈给请求处理管线，以便管线更新熔断器状态。

#### Scenario: 上游调用成功

- **WHEN** `Forwarder.forward_async()` 成功返回 `ForwardResult`
- **THEN** 请求处理管线 SHALL 能够识别为一次成功调用

#### Scenario: 上游调用返回限流错误

- **WHEN** `Forwarder.forward_async()` 抛出 `RateLimitError`
- **THEN** 请求处理管线 SHALL 能够识别为一次上游限流失败

#### Scenario: 上游调用返回服务端错误

- **WHEN** `Forwarder.forward_async()` 抛出 `ServiceUnavailableError` 或 `InternalServerError`
- **THEN** 请求处理管线 SHALL 能够识别为一次上游服务端失败

#### Scenario: 上游调用超时

- **WHEN** `Forwarder.forward_async()` 抛出 `Timeout`
- **THEN** 请求处理管线 SHALL 能够识别为一次上游超时失败

#### Scenario: 客户端错误不触发熔断计数

- **WHEN** `Forwarder.forward_async()` 抛出 `BadRequestError` 或 `NotFoundError`
- **THEN** 请求处理管线 SHALL 能够识别为客户端错误，不更新熔断失败计数

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

### Requirement: 透传客户端认证信息

Smart-Provider 的上游转发层 SHALL 将客户端请求 `Authorization` header 中的 Bearer token 作为 `api_key` 参数传给 `litellm.acompletion()`，使需要认证的 upstream 能够正常调用。

#### Scenario: 客户端提供 Authorization header

- **WHEN** 客户端请求包含 `Authorization: Bearer <token>`
- **THEN** Forwarder SHALL 提取 `<token>` 并作为 `api_key` 传给 `litellm.acompletion()`

#### Scenario: 客户端未提供 Authorization header

- **WHEN** 客户端请求未包含 `Authorization` header
- **THEN** Forwarder SHALL 将 `api_key=None` 传给 `litellm.acompletion()`，由 litellm 使用默认机制（如环境变量）获取密钥

