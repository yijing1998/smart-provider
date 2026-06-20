## ADDED Requirements

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
