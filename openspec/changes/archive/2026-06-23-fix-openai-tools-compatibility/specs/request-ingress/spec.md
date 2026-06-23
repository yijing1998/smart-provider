## MODIFIED Requirements

### Requirement: 代理接收客户端请求

Smart-Provider SHALL 接收来自客户端的模型 API 请求，并通过适配层将其转换为内部请求模型后封装为内部上下文对象。

#### Scenario: 客户端发送有效请求

- **WHEN** 客户端向 Smart-Provider 发送一个符合目标上游 API 协议格式的请求
- **THEN** 请求接入层 SHALL 通过适配层成功接收该请求并生成唯一请求标识

#### Scenario: 客户端发送模型名

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中 `model` 为 `deepseek-ai/deepseek-v4-pro`
- **THEN** 请求接入层 SHALL 使用配置的 `upstream_litellm_provider` 自动拼接为 `openai/deepseek-ai/deepseek-v4-pro`，并通过模型校验

#### Scenario: 客户端发送的模型名已含斜杠

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中 `model` 为 `z-ai/glm-5.1`
- **THEN** 请求接入层 SHALL 仍然拼接为 `openai/z-ai/glm-5.1`，并通过模型校验

#### Scenario: 客户端发送 function calling 请求

- **WHEN** 客户端发送 `POST /v1/chat/completions` 且请求体中包含标准 OpenAI 格式的 `tools` 对象数组
- **THEN** 请求接入层 SHALL 通过适配层成功解析，不返回 400 Bad Request

### Requirement: Ingress 使用 litellm SDK 解析请求

Smart-Provider 的 Ingress SHALL 使用 litellm SDK 提供的请求类型或等效机制解析并验证请求语义，具体的客户端协议适配由独立的适配层负责。

#### Scenario: 解析聊天补全请求体

- **WHEN** 客户端发送 POST /v1/chat/completions
- **THEN** Ingress SHALL 先通过适配层将请求体归一化为内部稳定模型，再基于该模型进行后续校验和转发

### Requirement: Ingress 使用 litellm 异常类型分类错误

Smart-Provider 的 Ingress SHALL 使用 litellm.exceptions 下的异常类型对请求解析失败、模型校验失败、队列已满等错误进行分类。

#### Scenario: 请求体格式错误

- **WHEN** 客户端发送的请求体无法通过适配层解析为有效请求
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 BadRequestError 等价错误

#### Scenario: 模型校验失败

- **WHEN** 客户端请求的模型名在拼接 `upstream_litellm_provider` 前缀后仍不被 litellm 支持
- **THEN** Ingress SHALL 抛出或映射为 litellm 的 NotFoundError 等价错误
