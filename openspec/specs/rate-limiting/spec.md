# Rate-Limiting Capability

## Purpose

定义 Smart-Provider 的 RPM 限速能力，包括滑动窗口算法、可配置阈值、对外接口与并发安全语义。

## Requirements

### Requirement: RPM 限速基于滑动窗口
Smart-Provider SHALL 使用滑动时间窗口统计最近一分钟内已向上游发送的请求数，并据此决定是否放行新请求。

#### Scenario: 窗口内请求数未超限
- **WHEN** 最近一分钟内已发送请求数小于配置的 RPM 限制
- **THEN** 限速器 SHALL 允许下一个请求出队并转发

#### Scenario: 窗口内请求数已超限
- **WHEN** 最近一分钟内已发送请求数已达到配置的 RPM 限制
- **THEN** 限速器 SHALL 阻止下一个请求出队，直到有足够的时间窗口容量释放

### Requirement: RPM 限制值可配置
Smart-Provider SHALL 支持通过配置指定目标上游 API 的 RPM 限制值。

#### Scenario: 修改 RPM 配置
- **WHEN** 管理员将 RPM 限制值从 60 修改为 120
- **THEN** 限速器 SHALL 在新的时间窗口内按 120 的阈值执行限速判断

### Requirement: 限速器提供异步放行接口

Smart-Provider 的限速器 SHALL 提供可被请求处理 Worker 调用的异步接口，以便在窗口容量不足时等待，在容量释放后放行。

#### Scenario: 窗口已满时等待放行

- **WHEN** 当前时间窗口内已发送请求数达到 RPM 限制
- **THEN** 调用方 SHALL 能够通过限速器的异步接口等待，直到窗口容量释放后获得放行

#### Scenario: 窗口未届满时立即放行

- **WHEN** 当前时间窗口内已发送请求数小于 RPM 限制
- **THEN** 调用方 SHALL 立即获得放行，无需等待

### Requirement: 限速器提供即时查询接口

Smart-Provider 的限速器 SHALL 提供即时查询接口，供调用方在不阻塞的情况下判断当前是否可放行。

#### Scenario: 查询当前是否可放行

- **WHEN** 调用方查询限速器当前状态
- **THEN** 限速器 SHALL 立即返回当前是否允许下一个请求出队

### Requirement: 限速器支持并发调用

Smart-Provider 的限速器 SHALL 在并发调用下保持状态一致，避免多个 Worker 同时通过放行判断导致实际发送请求数超过 RPM 限制。

#### Scenario: 多个 Worker 同时请求放行

- **WHEN** 多个 Worker 在同一时刻请求放行
- **THEN** 限速器 SHALL 保证在窗口容量范围内的放行次数不超过 RPM 限制

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

### Requirement: 限速器支持全局最小请求间隔

Smart-Provider SHALL 在滑动窗口 RPM 限速之外，支持配置相邻两次放行之间的最小时间间隔，以平滑突发流量。

#### Scenario: 配置最小请求间隔

- **WHEN** 管理员配置 `rate_limit_min_interval_ms` 为 1000 毫秒
- **THEN** 限速器 SHALL 确保任意两次放行之间至少间隔 1000 毫秒

#### Scenario: 窗口有容量但间隔未到

- **WHEN** 当前时间窗口内仍有 RPM 容量，但距离上一次放行不足 `rate_limit_min_interval_ms`
- **THEN** 限速器 SHALL 等待至间隔满足后才放行下一个请求

#### Scenario: 窗口有容量且间隔已到

- **WHEN** 当前时间窗口内仍有 RPM 容量，且距离上一次放行已超过 `rate_limit_min_interval_ms`
- **THEN** 限速器 SHALL 立即放行下一个请求

#### Scenario: 未配置最小间隔时保持原有行为

- **WHEN** 管理员未配置 `rate_limit_min_interval_ms`（默认值为 `None`）
- **THEN** 限速器 SHALL 仅按 RPM 滑动窗口规则放行，不引入额外等待

#### Scenario: 并发请求仍遵守最小间隔

- **WHEN** 多个 Worker 同时请求放行，且已配置 `rate_limit_min_interval_ms`
- **THEN** 任意两次成功放行之间的时间差 SHALL 不小于配置的最小间隔
