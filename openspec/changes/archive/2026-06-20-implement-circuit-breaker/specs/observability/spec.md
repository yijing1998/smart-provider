# Observability Capability Delta

## MODIFIED Requirements

### Requirement: 暴露核心指标

Smart-Provider SHALL 暴露反映系统运行状态的核心指标，至少包括当前队列长度、已入队请求数、已处理请求数、上游 429 次数、上游 5xx 次数、熔断器当前状态以及熔断器累计打开次数。

#### Scenario: 查询运行时指标

- **WHEN** 运维人员查询 Smart-Provider 的运行时指标
- **THEN** 系统 SHALL 返回当前队列长度、累计入队请求数、累计已处理请求数、累计上游 429 次数、累计上游 5xx 次数、熔断器当前状态与累计打开次数

#### Scenario: 指标随请求处理更新

- **WHEN** 一个请求完成入队、出队与上游转发
- **THEN** 队列长度、入队请求数、已处理请求数相应指标 SHALL 被更新

#### Scenario: 熔断器状态变化时更新指标

- **WHEN** 熔断器从 CLOSED 转入 OPEN
- **THEN** 指标 SHALL 反映当前状态为 open，且累计打开次数增加 1

#### Scenario: 半开状态可见

- **WHEN** 熔断器处于 HALF_OPEN 状态
- **THEN** 指标 SHALL 反映当前状态为 half_open
