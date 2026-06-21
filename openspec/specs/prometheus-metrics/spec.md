# Prometheus-Metrics Capability

## Purpose

定义 Smart-Provider 如何以 Prometheus exposition 格式暴露运行时指标，使其能够被 Prometheus 等标准监控系统抓取和告警。

## Requirements

### Requirement: 暴露 Prometheus 指标端点

Smart-Provider SHALL 在配置启用指标时，暴露 `/metrics/prometheus` 端点，返回 Prometheus 可解析的文本格式指标。

#### Scenario: 启用 Prometheus 指标端点

- **WHEN** 管理员配置 `observability_metrics_enabled=true`
- **THEN** 系统 SHALL 暴露 `/metrics/prometheus` 端点，并返回所有已注册指标

#### Scenario: 禁用 Prometheus 指标端点

- **WHEN** 管理员未启用 `observability_metrics_enabled`
- **THEN** 系统 SHALL 不暴露 `/metrics/prometheus` 端点

### Requirement: Prometheus 端点与 JSON 指标端点并存

Smart-Provider SHALL 在启用指标时同时提供 `/metrics`（JSON 格式）和 `/metrics/prometheus`（Prometheus 格式），两者互不替代。

#### Scenario: 同时访问两种格式

- **WHEN** 指标开关启用时，分别访问 `/metrics` 和 `/metrics/prometheus`
- **THEN** `/metrics` SHALL 返回 JSON 快照，`/metrics/prometheus` SHALL 返回 Prometheus exposition 文本

### Requirement: 暴露队列相关 Prometheus 指标

Smart-Provider SHALL 将队列状态以 Prometheus Gauge 形式暴露。

#### Scenario: 查询队列大小

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_queue_size` Gauge，表示当前队列中的请求数

### Requirement: 暴露请求处理相关 Prometheus 指标

Smart-Provider SHALL 将请求处理统计以 Prometheus Counter 形式暴露。

#### Scenario: 查询累计入队请求数

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_requests_enqueued_total` Counter

#### Scenario: 查询累计已处理请求数

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_requests_processed_total` Counter

### Requirement: 暴露上游错误相关 Prometheus 指标

Smart-Provider SHALL 将上游 API 返回的 429 与 5xx/连接错误以 Prometheus Counter 形式暴露。

#### Scenario: 查询上游 429 次数

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_upstream_429_total` Counter

#### Scenario: 查询上游 5xx 次数

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_upstream_5xx_total` Counter

### Requirement: 暴露请求等待时间直方图

Smart-Provider SHALL 将请求在队列中的等待时间以 Prometheus Histogram 形式暴露。

#### Scenario: 查询等待时间分布

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_queue_wait_duration_seconds` Histogram

### Requirement: 暴露请求总耗时直方图

Smart-Provider SHALL 将从请求入队到返回结果的总耗时以 Prometheus Histogram 形式暴露。

#### Scenario: 查询请求总耗时分布

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_request_duration_seconds` Histogram

### Requirement: 暴露熔断器状态指标

Smart-Provider SHALL 将熔断器当前状态以 Prometheus Gauge 形式暴露，并将熔断次数以 Counter 形式暴露。

#### Scenario: 查询熔断器状态

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_circuit_breaker_state` Gauge，0 表示 closed，1 表示 half_open，2 表示 open

#### Scenario: 查询熔断器打开次数

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_circuit_breaker_opens_total` Counter

### Requirement: 暴露流式请求相关 Prometheus 指标

Smart-Provider SHALL 将流式请求的开始次数和完成次数以 Prometheus Counter 形式暴露。

#### Scenario: 查询流式请求统计

- **WHEN** Prometheus 抓取 `/metrics/prometheus`
- **THEN** 响应中 SHALL 包含 `smart_provider_streams_started_total` 和 `smart_provider_streams_completed_total` Counter

### Requirement: Prometheus 指标标签基数可控

Smart-Provider 的第一阶段 Prometheus 指标实现 SHALL 不使用高基数标签（如 request_id、client_id、model），避免 Prometheus 内存爆炸。

#### Scenario: 审查指标标签

- **WHEN** 审查 `/metrics/prometheus` 的输出
- **THEN** 指标标签 SHALL 为空或仅包含固定低基数标签
