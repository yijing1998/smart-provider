## ADDED Requirements

### Requirement: 请求按 FIFO 入队
Smart-Provider SHALL 将接收到的请求按到达顺序放入内部请求队列。

#### Scenario: 多个请求依次到达
- **WHEN** 多个客户端请求在短时间间隔内依次到达
- **THEN** 这些请求 SHALL 按照到达先后顺序进入队列

### Requirement: 队列容量上限
Smart-Provider SHALL 为请求队列设置最大容量，当队列已满时拒绝新的入队请求。

#### Scenario: 队列达到最大容量
- **WHEN** 队列中待处理请求数已达到配置的最大容量
- **THEN** 新到达的请求 SHALL 被立即拒绝，并返回队列已满的响应

### Requirement: 请求出队由限速器控制
Smart-Provider SHALL 仅在限速器允许时从队列中取出请求并交给上游转发层。

#### Scenario: 限速器未放行
- **WHEN** 当前时间窗口内已发送请求数达到 RPM 限制
- **THEN** 队列 SHALL 暂停出队，等待下一时间窗口
