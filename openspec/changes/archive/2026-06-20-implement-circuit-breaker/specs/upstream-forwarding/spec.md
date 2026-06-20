# Upstream-Forwarding Capability Delta

## ADDED Requirements

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
