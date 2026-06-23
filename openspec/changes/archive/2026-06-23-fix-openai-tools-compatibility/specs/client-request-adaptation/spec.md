## ADDED Requirements

### Requirement: 适配 OpenAI 标准聊天补全请求

Smart-Provider SHALL 提供一个适配器，将客户端发送的 OpenAI 兼容 `/v1/chat/completions` 请求转换为内部稳定的请求模型。

#### Scenario: 请求包含标准 tools 对象数组

- **WHEN** 客户端请求体中包含 `tools`，且每个 tool 为 `{"type": "function", "function": {"name": ..., "parameters": ...}}` 格式
- **THEN** 适配器 SHALL 成功解析并保留该结构，不将其误判为字符串列表

#### Scenario: 请求包含 tool_choice

- **WHEN** 客户端请求体中包含 `tool_choice`，其值为 `"auto"`、`"none"`、特定 tool 名字典或对象
- **THEN** 适配器 SHALL 正确接收并透传该字段

#### Scenario: 请求包含 functions 和 function_call

- **WHEN** 客户端请求体中包含 `functions` 对象数组或 `function_call` 字符串/对象
- **THEN** 适配器 SHALL 正确接收并透传这些字段

#### Scenario: 请求包含额外未知字段

- **WHEN** 客户端请求体中包含 Smart-Provider 内部模型未显式声明的字段（如 `response_format`、`prediction`）
- **THEN** 适配器 SHALL 保留这些字段，供后续透传到上游

### Requirement: 适配层可扩展以支持多种客户端格式

Smart-Provider 的适配层 SHALL 设计为可插拔结构，以便未来为不同客户端格式提供独立适配器。

#### Scenario: 新增客户端格式

- **WHEN** 未来需要支持一种新的客户端请求格式
- **THEN** 开发人员 SHALL 只需新增适配器实现，而无需修改 Ingress 核心路由逻辑

### Requirement: 适配失败时返回清晰的错误信息

Smart-Provider SHALL 在适配器无法解析请求体时返回可识别的错误。

#### Scenario: 请求体格式严重错误

- **WHEN** 客户端请求体缺失必要字段或字段类型完全无法解析
- **THEN** 适配器 SHALL 抛出可被 Ingress 映射为 `BadRequestError` 的异常
