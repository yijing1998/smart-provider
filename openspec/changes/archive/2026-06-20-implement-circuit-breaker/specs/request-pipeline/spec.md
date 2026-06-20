# Request-Pipeline Capability Delta

## MODIFIED Requirements

### Requirement: 请求处理管线编排请求入队、限速出队与结果回传

Smart-Provider SHALL 提供一个请求处理管线（Request Pipeline），将请求队列、限速器与上游转发层串接起来：请求入队后由后台 Worker 在限速器许可下出队并异步转发，结果通过异步机制回传给请求接入层。Worker 出队后应先检查熔断器状态；若熔断器打开，则直接返回错误而不占用限速窗口。

#### Scenario: 请求入队后等待结果

- **WHEN** 客户端请求到达 Ingress 并成功入队
- **THEN** Ingress SHALL 通过管线等待该请求的转发结果，并将结果返回给客户端

#### Scenario: Worker 按限速器许可出队

- **WHEN** 队列中存在待处理请求且当前 RPM 窗口已满
- **THEN** Worker SHALL 等待限速器放行后再出队并转发

#### Scenario: Worker 将转发结果回传给 Ingress

- **WHEN** Worker 完成上游转发（成功或失败）
- **THEN** 管线 SHALL 通过 Future 或等效异步机制通知 Ingress，并附带结果或异常

#### Scenario: 熔断器打开时快速失败

- **WHEN** 队列中存在待处理请求且熔断器处于 OPEN 状态
- **THEN** Worker SHALL 不调用限速器和上游转发，直接将该请求标记为失败并返回服务不可用错误

#### Scenario: 半开状态允许探测请求通过

- **WHEN** 熔断器处于 HALF_OPEN 状态且有请求到达
- **THEN** Worker SHALL 允许该请求通过限速器和上游转发，作为恢复探测
