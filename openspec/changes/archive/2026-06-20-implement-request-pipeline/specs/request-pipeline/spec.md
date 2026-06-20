## ADDED Requirements

### Requirement: 请求处理管线编排请求入队、限速出队与结果回传

Smart-Provider SHALL 提供一个请求处理管线（Request Pipeline），将请求队列、限速器与上游转发层串接起来：请求入队后由后台 Worker 在限速器许可下出队并异步转发，结果通过异步机制回传给请求接入层。

#### Scenario: 请求入队后等待结果

- **WHEN** 客户端请求到达 Ingress 并成功入队
- **THEN** Ingress SHALL 通过管线等待该请求的转发结果，并将结果返回给客户端

#### Scenario: Worker 按限速器许可出队

- **WHEN** 队列中存在待处理请求且当前 RPM 窗口已满
- **THEN** Worker SHALL 等待限速器放行后再出队并转发

#### Scenario: Worker 将转发结果回传给 Ingress

- **WHEN** Worker 完成上游转发（成功或失败）
- **THEN** 管线 SHALL 通过 Future 或等效异步机制通知 Ingress，并附带结果或异常

### Requirement: 管线支持请求等待超时

Smart-Provider 的请求处理管线 SHALL 支持配置请求在队列中的最大等待时间，超过该时间的请求应被标记为等待超时并返回错误响应。

#### Scenario: 请求在队列中等待超过最大时间

- **WHEN** 一个请求在队列中等待的时间超过 `max_wait_time_ms`
- **THEN** 管线 SHALL 取消该请求的等待并返回超时错误

### Requirement: 管线支持启动与停止生命周期

Smart-Provider 的请求处理管线 SHALL 支持显式启动与停止，以便在应用启动时创建后台 Worker，在应用关闭时优雅停止。

#### Scenario: 应用启动时启动管线

- **WHEN** Smart-Provider 应用启动
- **THEN** 管线 SHALL 启动后台 Worker 并开始处理队列中的请求

#### Scenario: 应用关闭时停止管线

- **WHEN** Smart-Provider 应用关闭
- **THEN** 管线 SHALL 停止后台 Worker，避免未完成的任务泄漏
