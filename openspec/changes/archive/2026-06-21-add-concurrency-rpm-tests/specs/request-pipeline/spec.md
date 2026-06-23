# Request-Pipeline Capability

## Purpose

定义 Smart-Provider 如何将进入系统的请求串接为完整处理管线：请求入队后由后台 Worker 在限速器控制下出队、异步转发，并通过 Future 将结果回传给请求接入层。同时定义管线的生命周期管理，包括启动、优雅关闭、队列排空与运行状态查询。

## ADDED Requirements

### Requirement: 管线在高并发提交下保持行为一致

Smart-Provider 的请求处理管线 SHALL 在多个客户端并发调用 `submit()` 或 `submit_stream()` 时，仍然按 FIFO 顺序入队、按限速器许可出队，并正确返回结果或异常。

#### Scenario: 并发提交按 FIFO 排队

- **WHEN** 多个客户端请求在几乎同一时刻到达 Ingress 并调用 `submit()`
- **THEN** 这些请求 SHALL 按到达顺序进入队列，不被并发覆盖或乱序

#### Scenario: 并发提交下的请求等待超时

- **WHEN** 多个客户端请求同时到达，队列中已有请求等待，且 RPM 限制很低
- **THEN** 超过 `max_wait_time_ms` 的请求 SHALL 被标记为超时并返回 504 错误

#### Scenario: 并发提交下的成功结果返回

- **WHEN** 多个客户端请求并发提交并依次获得限速器放行
- **THEN** 每个客户端 SHALL 最终收到对应请求的响应，结果不混淆
