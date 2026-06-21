# Observability Capability

## Purpose

为 Smart-Provider 提供运行时可观测能力，包括核心指标暴露、关键事件日志记录、请求等待时间统计，以及 Prometheus exposition 格式的指标导出，帮助运维人员理解系统状态、评估限速效果，并为后续熔断器、TPM 限速等策略提供数据基础。
## Requirements
### Requirement: 暴露核心指标

Smart-Provider SHALL 暴露反映系统运行状态的核心指标，至少包括当前队列长度、已入队请求数、已处理请求数、上游 429 次数、上游 5xx 次数、流式请求开始次数和流式请求完成次数。

#### Scenario: 查询运行时指标

- **WHEN** 运维人员查询 Smart-Provider 的运行时指标
- **THEN** 系统 SHALL 返回当前队列长度、累计入队请求数、累计已处理请求数、累计上游 429 次数、累计上游 5xx 次数、累计流式请求开始次数和累计流式请求完成次数

#### Scenario: 指标随请求处理更新

- **WHEN** 一个请求完成入队、出队与上游转发
- **THEN** 队列长度、入队请求数、已处理请求数相应指标 SHALL 被更新

#### Scenario: 流式请求指标更新

- **WHEN** 一个流式请求成功入队
- **THEN** `streams_started_total` SHALL 增加 1

#### Scenario: 流式请求完成时更新指标

- **WHEN** 一个流式请求正常结束（StreamHandle 关闭）
- **THEN** `streams_completed_total` SHALL 增加 1

### Requirement: 记录关键事件日志

Smart-Provider SHALL 记录请求入队、出队、限速等待、转发成功与失败等关键事件。

#### Scenario: 请求完整生命周期

- **WHEN** 一个请求完成从入队到返回的全过程
- **THEN** 系统 SHALL 在该过程中至少记录请求入队、出队/放行、转发结果三个关键事件

### Requirement: 记录请求等待时间

Smart-Provider SHALL 记录每个请求在队列中等待的时间，以评估限速对延迟的影响。

#### Scenario: 统计等待时间

- **WHEN** 一个请求从入队到出队
- **THEN** 系统 SHALL 计算并记录该请求的等待时长，并维护等待时间的聚合统计（计数、总和、最大值、平均值）

### Requirement: 指标可通过 HTTP 端点访问

Smart-Provider SHALL 在配置启用时暴露一个 HTTP 端点，供运维人员查询运行时指标。

#### Scenario: 启用指标端点

- **WHEN** 管理员配置 `observability_metrics_enabled=true`
- **THEN** 系统 SHALL 暴露 `/metrics` 端点并返回当前指标快照

#### Scenario: 禁用指标端点

- **WHEN** 管理员未启用 `observability_metrics_enabled`
- **THEN** 系统 SHALL 不暴露 `/metrics` 端点

### Requirement: 暴露 Prometheus 格式的指标端点

Smart-Provider SHALL 在启用指标时，额外暴露 `/metrics/prometheus` 端点，返回 Prometheus 可抓取的文本格式。

#### Scenario: 启用时访问 Prometheus 端点

- **WHEN** 管理员配置 `observability_metrics_enabled=true` 并访问 `/metrics/prometheus`
- **THEN** 系统 SHALL 返回 Prometheus exposition 格式的指标文本

#### Scenario: 禁用时不可访问 Prometheus 端点

- **WHEN** 管理员未启用 `observability_metrics_enabled` 并访问 `/metrics/prometheus`
- **THEN** 系统 SHALL 返回 HTTP 404

### Requirement: 保留 JSON 指标端点

Smart-Provider SHALL 保留现有的 `/metrics` JSON 快照端点，行为与启用 Prometheus 端点之前保持一致。

#### Scenario: 同时存在两种指标端点

- **WHEN** 指标开关启用
- **THEN** `/metrics` SHALL 返回 JSON，`/metrics/prometheus` SHALL 返回 Prometheus 文本，两者数据一致

### Requirement: 暴露请求总耗时直方图

Smart-Provider SHALL 将从请求入队到结果返回的总耗时记录为 Prometheus Histogram。

#### Scenario: 记录成功请求总耗时

- **WHEN** 一个非流式请求完成入队、限速、转发并返回结果
- **THEN** 系统 SHALL 将该请求的总耗时记录到 `smart_provider_request_duration_seconds` Histogram

### Requirement: 暴露上游转发耗时直方图

Smart-Provider SHALL 将实际调用上游 API 的耗时记录为 Prometheus Histogram。

#### Scenario: 记录上游转发耗时

- **WHEN** 一个请求获得限速器放行并调用上游 API
- **THEN** 系统 SHALL 将上游调用耗时记录到 `smart_provider_forward_duration_seconds` Histogram

### Requirement: 暴露队列等待时间直方图

Smart-Provider SHALL 将请求在队列中的等待时间记录为 Prometheus Histogram，补充原有的 JSON 聚合统计。

#### Scenario: 记录队列等待耗时

- **WHEN** 一个请求从队列中出队
- **THEN** 系统 SHALL 将其等待时间记录到 `smart_provider_queue_wait_duration_seconds` Histogram

