# Configuration Capability

## Purpose

为 Smart-Provider 的运行时配置模型增加优雅关闭相关的配置项，使运维人员能够控制关闭阶段的队列排空超时。

## ADDED Requirements

### Requirement: 配置优雅关闭排空超时

Smart-Provider SHALL 支持配置服务关闭时等待队列排空的最大时间。

#### Scenario: 设置关闭排空超时

- **WHEN** 管理员配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 为 30000
- **THEN** 系统 SHALL 在关闭阶段最多等待 30000 毫秒处理队列中的请求

#### Scenario: 未配置时使用默认排空超时

- **WHEN** 管理员未配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS`
- **THEN** 系统 SHALL 使用默认值 30000 毫秒

#### Scenario: 配置无效的排空超时

- **WHEN** 管理员将 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 设置为 0 或负数
- **THEN** 系统 SHALL 在启动时拒绝该配置并提示错误
