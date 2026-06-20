# Observability Capability Delta

## MODIFIED Requirements

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
