## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: 使用 litellm SDK 异步调用上游

Smart-Provider 的上游转发层 SHALL 使用 litellm SDK 的 acompletion() 异步调用上游模型 API。

#### Scenario: 转发聊天补全请求

- **WHEN** 一个请求获得限速器放行
- **THEN** Forwarder SHALL 调用 litellm.acompletion() 将请求发送至目标上游

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
