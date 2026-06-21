# Graceful-Shutdown Capability

## Purpose

定义 Smart-Provider 在收到关闭信号时的行为，确保服务能够停止接收新请求、尽量排空队列中的已有请求，再停止后台 Worker，从而降低滚动更新或缩容时的请求失败率。

## ADDED Requirements

### Requirement: 支持关闭超时配置

Smart-Provider SHALL 支持通过配置指定优雅关闭时的队列排空超时时间。

#### Scenario: 配置排空超时

- **WHEN** 管理员配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 为 30000
- **THEN** 系统 SHALL 在关闭阶段最多等待 30000 毫秒让队列中的请求被处理，超时后强制停止 Worker

#### Scenario: 未配置时使用默认值

- **WHEN** 管理员未配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS`
- **THEN** 系统 SHALL 使用默认值 30000 毫秒作为排空超时

### Requirement: 关闭期间拒绝新请求

Smart-Provider SHALL 在收到关闭信号后进入 shutting_down 状态，该状态下到达的新请求 SHALL 被立即拒绝，返回 HTTP 503，直到服务完全停止。

#### Scenario: 关闭中收到新请求

- **WHEN** 服务已进入 shutting_down 状态，且有新的聊天补全请求到达
- **THEN** 系统 SHALL 返回 HTTP 503，错误信息提示服务正在关闭

#### Scenario: 关闭中流式请求被拒绝

- **WHEN** 服务已进入 shutting_down 状态，且有新的流式请求到达
- **THEN** 系统 SHALL 返回 HTTP 503，不创建新的 StreamHandle

### Requirement: 关闭时排空队列中的请求

Smart-Provider SHALL 在关闭阶段继续处理队列中已存在的请求，直到队列为空或达到排空超时。

#### Scenario: 队列非空时正常关闭

- **WHEN** 服务关闭时队列中存在待处理请求，且排空超时未到
- **THEN** Worker SHALL 继续按 RPM 限速出队并转发这些请求

#### Scenario: 队列排空后关闭

- **WHEN** 服务关闭过程中队列变为空
- **THEN** 系统 SHALL 停止 Worker 并完成关闭

### Requirement: 关闭时尊重单个请求的剩余等待时间

Smart-Provider SHALL 在关闭阶段的队列排空过程中，跳过或拒绝那些已超过 `max_wait_time_ms` 的请求，避免无限等待。

#### Scenario: 队列中请求已超时

- **WHEN** 关闭阶段 Worker 取出一个请求，发现其已在队列中等待超过 `max_wait_time_ms`
- **THEN** 系统 SHALL 拒绝该请求并返回超时错误，不再转发到上游

### Requirement: 关闭时允许已建立的流式连接继续

Smart-Provider SHALL 在关闭阶段允许已经建立的流式连接继续推送 chunk 直至自然结束，但不再接受新的流式请求。

#### Scenario: 关闭前已建立的流式连接

- **WHEN** 服务进入 shutting_down 状态时，已存在正在推送的 SSE 连接
- **THEN** 系统 SHALL 继续推送剩余 chunk 直至 StreamHandle 关闭

### Requirement: 排空超时后强制停止

Smart-Provider SHALL 在达到配置的排空超时后，强制停止 processor worker，不再继续处理剩余队列请求。

#### Scenario: 排空超时到达

- **WHEN** 关闭阶段的等待时间超过 `shutdown_drain_timeout_ms`
- **THEN** 系统 SHALL 强制取消 Worker 任务，剩余未处理请求被丢弃
