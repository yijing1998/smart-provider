## ADDED Requirements

### Requirement: 记录上游 429 响应头

Smart-Provider SHALL 在收到上游返回的 429 响应时，将响应头中所有与限流相关的字段原样记录到可观测日志中，以辅助运维人员判断 429 的具体原因。

#### Scenario: 上游返回 x-ratelimit 头

- **WHEN** 上游返回 429 且响应头包含 `x-ratelimit-remaining-requests`、`x-ratelimit-reset-requests` 等字段
- **THEN** 系统 SHALL 在 429 日志的 `extra` 字段中以原始键值形式输出这些响应头

#### Scenario: 上游返回 retry-after 头

- **WHEN** 上游返回 429 且响应头包含 `retry-after`
- **THEN** 系统 SHALL 在 429 日志的 `extra` 字段中原样输出 `retry-after` 字段

#### Scenario: 上游未返回限流头

- **WHEN** 上游返回 429 但响应头中不存在任何 `ratelimit` 或 `retry-after` 字段
- **THEN** 系统 SHALL 在 429 日志的 `extra` 字段中输出空的限流头字典，且不抛出异常

#### Scenario: 限流头大小写不敏感

- **WHEN** 上游返回 429 且响应头中的限流字段为大写或混合大小写形式（如 `X-RateLimit-Remaining-Requests` 或 `Retry-After`）
- **THEN** 系统 SHALL 正确识别并原样记录这些字段
