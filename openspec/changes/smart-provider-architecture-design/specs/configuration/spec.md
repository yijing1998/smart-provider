## ADDED Requirements

### Requirement: 配置上游目标地址
Smart-Provider SHALL 支持配置真实上游 API Endpoint 的地址。

#### Scenario: 启动时加载目标地址
- **WHEN** Smart-Provider 启动
- **THEN** 系统 SHALL 读取配置中的上游 API 地址，并用于后续请求转发

### Requirement: 配置 RPM 限制
Smart-Provider SHALL 支持配置目标上游 API 的 RPM 限制值。

#### Scenario: 设置 RPM 限制
- **WHEN** 管理员配置 RPM 限制为 60
- **THEN** 限速器 SHALL 以 60 作为每分钟最大请求数执行限速

### Requirement: 配置队列容量与超时
Smart-Provider SHALL 支持配置请求队列最大容量和上游请求超时时间。

#### Scenario: 设置队列与超时参数
- **WHEN** 管理员配置队列最大容量为 1000、上游超时时间为 30 秒
- **THEN** 系统 SHALL 按这些参数运行，队列超过 1000 时拒绝新请求，超过 30 秒未响应的请求标记为超时
