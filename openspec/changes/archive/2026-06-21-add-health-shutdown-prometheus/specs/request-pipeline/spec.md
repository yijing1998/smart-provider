# Request-Pipeline Capability

## Purpose

扩展 Smart-Provider 的请求处理管线生命周期，使其支持优雅关闭阶段的队列排空，并在关闭期间停止接收新请求。

## MODIFIED Requirements

### Requirement: 管线支持启动与停止生命周期

Smart-Provider 的请求处理管线 SHALL 支持显式启动与停止，以便在应用启动时创建后台 Worker，在应用关闭时优雅停止。

#### Scenario: 应用启动时启动管线

- **WHEN** Smart-Provider 应用启动
- **THEN** 管线 SHALL 启动后台 Worker 并开始处理队列中的请求

#### Scenario: 应用关闭时优雅停止管线

- **WHEN** Smart-Provider 应用关闭
- **THEN** 管线 SHALL 在配置的排空超时内继续处理队列中的已有请求，超时后停止后台 Worker

#### Scenario: 关闭期间不再接收新请求

- **WHEN** 管线进入关闭流程后
- **THEN** `submit()` 与 `submit_stream()` SHALL 拒绝新请求并抛出 ServiceUnavailableError，由 Ingress 层转换为 HTTP 503

### Requirement: 管线支持队列排空操作

Smart-Provider 的请求处理管线 SHALL 提供 `drain(timeout)` 操作，在指定超时内尽可能处理完队列中的请求。

#### Scenario: 排空空队列

- **WHEN** 调用 `drain(timeout)` 且队列为空
- **THEN** 操作 SHALL 立即返回

#### Scenario: 排空非空队列

- **WHEN** 调用 `drain(timeout)` 且队列中存在请求
- **THEN** Worker SHALL 继续出队并处理请求，直到队列为空或超时

#### Scenario: 排空超时

- **WHEN** `drain(timeout)` 的执行时间超过指定超时
- **THEN** 操作 SHALL 停止等待，剩余未处理请求被丢弃

### Requirement: 管线支持查询运行状态

Smart-Provider 的请求处理管线 SHALL 提供查询接口，供 Ingress 就绪探测使用。

#### Scenario: 查询 worker 是否运行

- **WHEN** Ingress 调用管线的运行状态查询接口
- **THEN** 系统 SHALL 返回 worker 是否正在运行
