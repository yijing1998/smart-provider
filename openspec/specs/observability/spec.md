# Observability Capability

## Purpose

TBD

## Requirements

### Requirement: 暴露核心指标
Smart-Provider SHALL 暴露反映系统运行状态的核心指标，至少包括当前队列长度、已处理请求数、上游 429 次数和上游 5xx 次数。

#### Scenario: 查询运行时指标
- **WHEN** 运维人员查询 Smart-Provider 的运行时指标
- **THEN** 系统 SHALL 返回当前队列长度、累计处理请求数、累计上游 429 次数和累计上游 5xx 次数

### Requirement: 记录关键事件日志
Smart-Provider SHALL 记录请求入队、出队、限速等待、转发成功与失败等关键事件。

#### Scenario: 请求完整生命周期
- **WHEN** 一个请求完成从入队到返回的全过程
- **THEN** 系统 SHALL 在该过程中至少记录请求入队、出队/放行、转发结果三个关键事件

### Requirement: 记录请求等待时间
Smart-Provider SHALL 记录每个请求在队列中等待的时间，以评估限速对延迟的影响。

#### Scenario: 统计等待时间
- **WHEN** 一个请求从入队到出队
- **THEN** 系统 SHALL 计算并记录该请求的等待时长
