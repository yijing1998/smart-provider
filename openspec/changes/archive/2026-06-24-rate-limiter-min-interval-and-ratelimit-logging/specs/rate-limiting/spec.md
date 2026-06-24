## ADDED Requirements

### Requirement: 限速器支持全局最小请求间隔

Smart-Provider SHALL 在滑动窗口 RPM 限速之外，支持配置相邻两次放行之间的最小时间间隔，以平滑突发流量。

#### Scenario: 配置最小请求间隔

- **WHEN** 管理员配置 `rate_limit_min_interval_ms` 为 1000 毫秒
- **THEN** 限速器 SHALL 确保任意两次放行之间至少间隔 1000 毫秒

#### Scenario: 窗口有容量但间隔未到

- **WHEN** 当前时间窗口内仍有 RPM 容量，但距离上一次放行不足 `rate_limit_min_interval_ms`
- **THEN** 限速器 SHALL 等待至间隔满足后才放行下一个请求

#### Scenario: 窗口有容量且间隔已到

- **WHEN** 当前时间窗口内仍有 RPM 容量，且距离上一次放行已超过 `rate_limit_min_interval_ms`
- **THEN** 限速器 SHALL 立即放行下一个请求

#### Scenario: 未配置最小间隔时保持原有行为

- **WHEN** 管理员未配置 `rate_limit_min_interval_ms`（默认值为 `None`）
- **THEN** 限速器 SHALL 仅按 RPM 滑动窗口规则放行，不引入额外等待

#### Scenario: 并发请求仍遵守最小间隔

- **WHEN** 多个 Worker 同时请求放行，且已配置 `rate_limit_min_interval_ms`
- **THEN** 任意两次成功放行之间的时间差 SHALL 不小于配置的最小间隔
