# Request-Pipeline Capability

## Purpose

定义 Smart-Provider 如何将进入系统的请求串接为完整处理管线：请求入队后由后台 Worker 在限速器控制下出队、异步转发，并通过 Future 将结果回传给请求接入层。同时定义管线的生命周期管理，包括启动、优雅关闭、队列排空与运行状态查询。
## Requirements
### Requirement: 请求处理管线编排请求入队、限速出队与结果回传

Smart-Provider SHALL 提供一个请求处理管线（Request Pipeline），将请求队列、限速器与上游转发层串接起来：请求入队后由后台 Worker 在限速器许可下出队并异步转发，结果通过异步机制回传给请求接入层。对于流式请求，管线 SHALL 提供 `submit_stream()` 接口，通过 `StreamHandle` 逐 chunk 回传结果。

#### Scenario: 请求入队后等待结果

- **WHEN** 客户端请求到达 Ingress 并成功入队
- **THEN** Ingress SHALL 通过管线等待该请求的转发结果，并将结果返回给客户端

#### Scenario: Worker 按限速器许可出队

- **WHEN** 队列中存在待处理请求且当前 RPM 窗口已满
- **THEN** Worker SHALL 等待限速器放行后再出队并转发

#### Scenario: Worker 将转发结果回传给 Ingress

- **WHEN** Worker 完成上游转发（成功或失败）
- **THEN** 管线 SHALL 通过 Future 或等效异步机制通知 Ingress，并附带结果或异常

#### Scenario: 流式请求通过 StreamHandle 回传 chunk

- **WHEN** 一个流式请求获得限速器放行
- **THEN** Worker SHALL 调用 `Forwarder.stream_async()` 并将每个 chunk 写入 `RequestContext.stream_handle`

#### Scenario: 流式请求完成时关闭 StreamHandle

- **WHEN** 上游流式响应结束或出错
- **THEN** Worker SHALL 调用 `StreamHandle.close()` 或 `StreamHandle.put_error()`，使 Ingress 端 SSE generator 正常结束

#### Scenario: 客户端取消时停止流式写入

- **WHEN** 客户端断开连接导致 `StreamHandle.cancel()` 被调用
- **THEN** Worker SHALL 停止向 `StreamHandle` 写入 chunk 并关闭通道

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

#### Scenario: 应用关闭时优雅停止管线

- **WHEN** Smart-Provider 应用关闭
- **THEN** 管线 SHALL 在配置的排空超时内继续处理队列中的已有请求，超时后停止后台 Worker

#### Scenario: 关闭期间不再接收新请求

- **WHEN** 管线进入关闭流程后
- **THEN** `submit()` 与 `submit_stream()` SHALL 拒绝新请求并抛出 ServiceUnavailableError，由 Ingress 层转换为 HTTP 503

### Requirement: 管线支持队列排空操作

Smart-Provider 的请求处理管线 SHALL 提供 `drain(timeout)` 操作，在指定超时内尽可能处理完队列中的请求。

#### Scenario: 排空空队列

- **WHEN** 调用 `drain(timeout)` 且队列为空
- **THEN** 操作 SHALL 立即返回

#### Scenario: 排空非空队列

- **WHEN** 调用 `drain(timeout)` 且队列中存在请求
- **THEN** Worker SHALL 继续出队并处理请求，直到队列为空或超时

#### Scenario: 排空超时

- **WHEN** `drain(timeout)` 的执行时间超过指定超时
- **THEN** 操作 SHALL 停止等待，剩余未处理请求被丢弃

### Requirement: 管线支持查询运行状态

Smart-Provider 的请求处理管线 SHALL 提供查询接口，供 Ingress 就绪探测使用。

#### Scenario: 查询 worker 是否运行

- **WHEN** Ingress 调用管线的运行状态查询接口
- **THEN** 系统 SHALL 返回 worker 是否正在运行

