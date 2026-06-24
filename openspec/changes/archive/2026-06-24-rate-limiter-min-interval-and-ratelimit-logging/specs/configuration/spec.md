## ADDED Requirements

### Requirement: 配置最小请求间隔

Smart-Provider SHALL 支持配置 RPM 限速器的全局最小请求间隔，用于控制相邻两次向上游发送请求的最短时间差。

#### Scenario: 通过环境变量配置最小间隔

- **WHEN** 管理员设置 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS=500`
- **THEN** 系统 SHALL 在启动时将该值加载为 `rate_limit_min_interval_ms`，并传递给限速器

#### Scenario: 最小间隔默认不启用

- **WHEN** 管理员未设置 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS`
- **THEN** 系统 SHALL 使用默认值 `None`，表示不启用最小间隔约束

#### Scenario: 最小间隔配置值校验

- **WHEN** 管理员配置 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS=-100`
- **THEN** 系统 SHALL 在启动阶段拒绝该配置并提示错误
