# Rate-Limiting Capability

## Purpose

定义 Smart-Provider 的 RPM 限速能力，包括滑动窗口算法、可配置阈值、对外接口与并发安全语义。

## ADDED Requirements

### Requirement: 并发 HTTP 请求下的 RPM 上限不被突破

Smart-Provider SHALL 确保在单 Worker 架构下，多个 HTTP 客户端并发发送请求时，任意滑动时间窗口内实际转发到上游的请求数不超过配置的 RPM 限制。

#### Scenario: 突发并发请求遵守 RPM 上限

- **WHEN** 20 个客户端在同一时刻向 Smart-Provider 发送请求，且 RPM 限制为 5
- **THEN** 任意 1 秒滑动窗口内，上游实际接收到的请求数 SHALL 不超过 5

#### Scenario: 持续并发负载保持速率稳定

- **WHEN** 客户端以固定间隔持续 10 秒发送请求，且 RPM 限制为 10
- **THEN** 任意 1 秒滑动窗口内，上游实际接收到的请求数 SHALL 不超过 10，且总处理数接近 100

### Requirement: 流式与非流式请求共享 RPM 配额

Smart-Provider SHALL 在并发场景下将流式请求与非流式请求统一计入 RPM 滑动窗口，两者共同受 RPM 上限约束。

#### Scenario: 混合并发请求共享配额

- **WHEN** 3 个流式请求与 7 个非流式请求同时到达，且 RPM 限制为 5
- **THEN** 任意 1 秒滑动窗口内，上游实际接收到的总请求数（含流式）SHALL 不超过 5
