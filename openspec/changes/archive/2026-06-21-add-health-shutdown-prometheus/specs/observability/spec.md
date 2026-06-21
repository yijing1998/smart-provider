# Observability Capability

## Purpose

在现有 JSON 指标快照的基础上，为 Smart-Provider 增加 Prometheus exposition 格式的指标导出能力，并补充请求耗时等更细粒度的可观测指标。

## ADDED Requirements

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

Smart-Provider SHALL 将请求在队列中的等待时间记录为 Prometheus Histogram，替代或补充原有的 JSON 聚合统计。

#### Scenario: 记录队列等待耗时

- **WHEN** 一个请求从队列中出队
- **THEN** 系统 SHALL 将其等待时间记录到 `smart_provider_queue_wait_duration_seconds` Histogram
