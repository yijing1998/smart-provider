# Health-Checks Capability

## Purpose

定义 Smart-Provider 的健康检查端点，使负载均衡器、容器编排系统（如 Kubernetes）和标准监控工具能够判断服务是否存活以及是否愿意接收流量。

## Requirements

### Requirement: 暴露存活探测端点

Smart-Provider SHALL 暴露 `/health` 端点，用于返回服务进程是否存活。该端点 SHALL 不调用上游 API，避免消耗 RPM 配额或受上游故障影响。

#### Scenario: 查询存活状态

- **WHEN** 负载均衡器向 `/health` 发送 GET 请求
- **THEN** 系统 SHALL 返回 HTTP 200 与 `{"status": "healthy"}`，且该过程不涉及上游 API 调用

#### Scenario: 上游故障时不影响存活探测

- **WHEN** 上游 API 不可用时，负载均衡器查询 `/health`
- **THEN** 系统 SHALL 仍然返回 HTTP 200，因为进程本身仍然存活

### Requirement: 暴露就绪探测端点

Smart-Provider SHALL 暴露 `/ready` 端点，用于返回服务是否愿意接收新请求。就绪判断 SHALL 基于服务内部状态，而不是上游 API 的健康状况。

#### Scenario: 服务正常运行时返回就绪

- **WHEN** processor worker 正在运行、服务未处于关闭状态、队列未满
- **THEN** 对 `/ready` 的 GET 请求 SHALL 返回 HTTP 200 与 `{"status": "ready"}`

#### Scenario: processor worker 未运行时返回未就绪

- **WHEN** processor worker 未启动或已异常退出
- **THEN** 对 `/ready` 的 GET 请求 SHALL 返回 HTTP 503，提示服务暂时不愿接收流量

#### Scenario: 服务关闭中时返回未就绪

- **WHEN** 服务收到关闭信号并进入 shutting_down 状态
- **THEN** 对 `/ready` 的 GET 请求 SHALL 返回 HTTP 503，提示服务正在关闭

#### Scenario: 熔断器打开时仍返回就绪

- **WHEN** 上游连续失败导致熔断器打开
- **THEN** 对 `/ready` 的 GET 请求 SHALL 仍然返回 HTTP 200，因为服务本身仍能正常处理请求（快速失败），上游状态属于业务监控范畴

### Requirement: 健康检查端点不受指标开关控制

Smart-Provider 的 `/health` 与 `/ready` 端点 SHALL 始终暴露，不依赖于 `observability_metrics_enabled` 配置。

#### Scenario: 指标开关关闭时仍可探测健康

- **WHEN** 管理员未启用 `observability_metrics_enabled`
- **THEN** `/health` 与 `/ready` 端点 SHALL 仍然可用
