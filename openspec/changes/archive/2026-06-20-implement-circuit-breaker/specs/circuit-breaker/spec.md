# Circuit-Breaker Capability

## Purpose

定义 Smart-Provider 在上游 API 持续异常时如何保护自身：通过熔断器状态机监控上游调用结果，在连续失败达到阈值时快速失败新请求，并在上游恢复后自动重新闭合。

## ADDED Requirements

### Requirement: 熔断器维护 CLOSED、OPEN、HALF_OPEN 三种状态

Smart-Provider SHALL 提供一个熔断器组件，维护 CLOSED（闭合）、OPEN（打开）、HALF_OPEN（半开）三种状态，并根据上游调用结果在状态间转换。

#### Scenario: 初始状态为 CLOSED

- **WHEN** Smart-Provider 启动且熔断器启用
- **THEN** 熔断器初始状态 SHALL 为 CLOSED

#### Scenario: 连续失败达到阈值后转入 OPEN

- **WHEN** 上游连续返回失败且失败次数达到 `failure_threshold`
- **THEN** 熔断器 SHALL 从 CLOSED 转入 OPEN

#### Scenario: 超时后转入 HALF_OPEN

- **WHEN** 熔断器处于 OPEN 状态且持续时间超过 `recovery_timeout`
- **THEN** 熔断器 SHALL 转入 HALF_OPEN，允许下一个请求通过作为探测

#### Scenario: 探测成功后闭合

- **WHEN** 熔断器处于 HALF_OPEN 且探测请求成功
- **THEN** 熔断器 SHALL 转回 CLOSED

#### Scenario: 探测失败后重新打开

- **WHEN** 熔断器处于 HALF_OPEN 且探测请求失败
- **THEN** 熔断器 SHALL 重新转回 OPEN

### Requirement: 只有上游/网络层错误才计入熔断失败

Smart-Provider SHALL 仅将上游 API 返回的限流、服务端错误、连接错误和超时计入熔断失败计数；客户端请求错误 SHALL NOT 触发熔断计数。

#### Scenario: 上游返回 429 计入失败

- **WHEN** 上游返回 429 Too Many Requests
- **THEN** 熔断器 SHALL 记录一次失败

#### Scenario: 上游返回 503 计入失败

- **WHEN** 上游返回 503 Service Unavailable
- **THEN** 熔断器 SHALL 记录一次失败

#### Scenario: 上游连接超时计入失败

- **WHEN** 上游请求超时
- **THEN** 熔断器 SHALL 记录一次失败

#### Scenario: 客户端请求错误不计入失败

- **WHEN** 上游返回 400 Bad Request 或 404 Not Found
- **THEN** 熔断器 SHALL NOT 记录失败

### Requirement: 熔断器成功调用重置连续失败计数

Smart-Provider SHALL 在每次上游调用成功后重置连续失败计数。

#### Scenario: 部分失败后成功调用

- **WHEN** 上游连续失败 2 次后第 3 次调用成功
- **THEN** 连续失败计数 SHALL 重置为 0

### Requirement: 熔断器可通过配置启用与参数化

Smart-Provider SHALL 支持通过配置启用熔断器，并设置失败阈值与恢复超时时间。

#### Scenario: 启用熔断器

- **WHEN** `circuit_breaker_enabled` 设置为 true
- **THEN** 请求处理管线 SHALL 启用熔断检查

#### Scenario: 设置失败阈值

- **WHEN** `circuit_breaker_failure_threshold` 设置为 3
- **THEN** 连续失败 3 次后熔断器 SHALL 打开

#### Scenario: 设置恢复超时

- **WHEN** `circuit_breaker_recovery_timeout_ms` 设置为 30000
- **THEN** 熔断器打开至少 30000 毫秒后才允许进入半开状态
