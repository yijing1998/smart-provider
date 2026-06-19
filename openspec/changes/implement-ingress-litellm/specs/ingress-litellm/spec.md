## ADDED Requirements

### Requirement: 暴露 OpenAI 兼容端点
Smart-Provider 的 Ingress SHALL 暴露 `POST /v1/chat/completions` 端点，接收 OpenAI 兼容的聊天补全请求。

#### Scenario: 客户端发送聊天补全请求
- **WHEN** 客户端向 `POST /v1/chat/completions` 发送符合 OpenAI 格式的请求
- **THEN** Ingress SHALL 接收该请求并进入后续处理流程

### Requirement: 使用 litellm 解析请求
Smart-Provider 的 Ingress SHALL 使用 litellm 提供的请求类型或工具解析客户端请求体，而不是自行实现 OpenAI 请求 schema。

#### Scenario: 解析请求体
- **WHEN** 请求体到达 Ingress
- **THEN** Ingress SHALL 使用 litellm SDK 将其解析为结构化的补全请求对象

### Requirement: 校验模型名称
Smart-Provider 的 Ingress SHALL 使用 litellm 提供的模型信息能力校验请求中的模型名称是否可识别。

#### Scenario: 模型名称无效
- **WHEN** 请求体中的 model 字段指向 litellm 无法识别的模型
- **THEN** Ingress SHALL 返回错误响应，且该请求不进入队列

### Requirement: 构造内部请求上下文
Smart-Provider 的 Ingress SHALL 将客户端请求转换为项目内部请求上下文，并生成唯一 requestId 与入队时间戳。

#### Scenario: 请求通过校验
- **WHEN** 请求成功通过解析与模型校验
- **THEN** Ingress SHALL 生成内部上下文，其中至少包含 requestId、clientId、enqueuedAt、model、messages、stream

### Requirement: 将上下文提交给队列
Smart-Provider 的 Ingress SHALL 调用请求队列的入队接口提交内部上下文；若队列已满，则返回队列已满的错误响应。

#### Scenario: 队列已满
- **WHEN** 队列的入队接口返回容量已满
- **THEN** Ingress SHALL 返回表示服务暂时无法接受的错误响应

### Requirement: 等待并返回转发结果
Smart-Provider 的 Ingress SHALL 在请求入队后等待上游转发结果，并将该结果返回给客户端。

#### Scenario: 转发成功
- **WHEN** 上游转发层返回成功响应
- **THEN** Ingress SHALL 将该响应原样返回给发起请求的客户端

### Requirement: 使用 litellm 异常类型分类错误
Smart-Provider 的 Ingress SHALL 使用 litellm 提供的异常类型对解析失败、校验失败、队列已满、上游错误等场景进行分类。

#### Scenario: 请求体格式错误
- **WHEN** 客户端发送的请求体无法被 litellm 请求类型解析
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 BadRequestError 等价错误

### Requirement: 使用 litellm 记录日志
Smart-Provider 的 Ingress SHALL 通过 litellm 的日志或回调机制记录请求接收、入队、错误等关键事件。

#### Scenario: 请求入队
- **WHEN** 一个请求成功入队
- **THEN** Ingress SHALL 通过 litellm 日志机制记录该事件，包含 requestId 与 model
