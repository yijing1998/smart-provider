# Request-Pipeline Capability Delta

## MODIFIED Requirements

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
