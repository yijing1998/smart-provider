## ADDED Requirements

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
