## ADDED Requirements

### Requirement: 按放行顺序转发请求
Smart-Provider SHALL 在限速器放行后，按顺序将请求转发至配置的上游 API Endpoint。

#### Scenario: 请求获得放行
- **WHEN** 限速器允许一个请求出队
- **THEN** 上游转发层 SHALL 将该请求发送至目标上游 API Endpoint

### Requirement: 维护上游连接状态
Smart-Provider SHALL 管理与上游 API 的连接，并支持合理的超时设置。

#### Scenario: 上游响应超时
- **WHEN** 上游 API 在配置的超时时间内未返回响应
- **THEN** 上游转发层 SHALL 将该请求标记为超时，并将超时结果返回给客户端

### Requirement: 错误分类
Smart-Provider SHALL 将上游返回的错误按类型分类，至少区分限流类错误（429）与其他服务端错误（5xx）。

#### Scenario: 上游返回 429
- **WHEN** 上游 API 返回 429 Too Many Requests
- **THEN** 系统 SHALL 记录该事件，并可作为调整限速策略或触发退避的依据
