# Request-Ingress Capability

## Purpose

扩展 Smart-Provider 的 Ingress 层，增加健康检查、就绪探测、Prometheus 指标端点，并在服务关闭期间拒绝新请求。

## ADDED Requirements

### Requirement: 暴露健康检查端点

Smart-Provider 的 Ingress SHALL 暴露 `/health` 端点，供外部探测服务是否存活。

#### Scenario: 访问存活探测端点

- **WHEN** 客户端发送 `GET /health`
- **THEN** Ingress SHALL 返回 HTTP 200 与 `{"status": "healthy"}`

### Requirement: 暴露就绪探测端点

Smart-Provider 的 Ingress SHALL 暴露 `/ready` 端点，供外部判断服务是否愿意接收流量。

#### Scenario: 服务就绪时访问

- **WHEN** processor worker 正在运行、服务未关闭、队列未满时访问 `GET /ready`
- **THEN** Ingress SHALL 返回 HTTP 200 与 `{"status": "ready"}`

#### Scenario: 服务未就绪时访问

- **WHEN** processor worker 未运行或服务处于 shutting_down 状态时访问 `GET /ready`
- **THEN** Ingress SHALL 返回 HTTP 503

### Requirement: 暴露 Prometheus 指标端点

Smart-Provider 的 Ingress SHALL 在指标启用时暴露 `/metrics/prometheus` 端点。

#### Scenario: 启用时访问 Prometheus 端点

- **WHEN** 指标开关启用且访问 `GET /metrics/prometheus`
- **THEN** Ingress SHALL 返回 Prometheus exposition 格式的指标文本

### Requirement: 关闭期间拒绝新请求

Smart-Provider 的 Ingress SHALL 在服务进入 shutting_down 状态后，对除健康检查外的所有新请求返回 HTTP 503。

#### Scenario: 关闭中收到聊天补全请求

- **WHEN** 服务处于 shutting_down 状态且收到 `POST /v1/chat/completions`
- **THEN** Ingress SHALL 返回 HTTP 503，不将其放入队列

#### Scenario: 关闭中仍可访问健康检查

- **WHEN** 服务处于 shutting_down 状态且收到 `GET /health` 或 `GET /ready`
- **THEN** Ingress SHALL 正常响应，以便编排系统能够探测到关闭状态

### Requirement: 健康检查端点不受指标开关控制

Smart-Provider 的 `/health` 与 `/ready` 端点 SHALL 始终暴露，不受 `observability_metrics_enabled` 配置影响。

#### Scenario: 指标关闭时访问健康端点

- **WHEN** `observability_metrics_enabled=false` 时访问 `/health` 或 `/ready`
- **THEN** Ingress SHALL 正常返回 200 或 503
