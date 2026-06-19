## ADDED Requirements

### Requirement: 列出运行时配置项
编码实现指导文档 SHALL 列出 Smart-Provider 所需的运行时配置项，并说明每项的语义、类型与示例值。

#### Scenario: 配置代理服务
- **WHEN** 部署 Smart-Provider
- **THEN** 文档 SHALL 说明 upstream.url、rateLimit.rpm、queue.maxSize、forwarder.timeout、server.port 等配置项

### Requirement: 说明配置加载方式
编码实现指导文档 SHALL 说明配置建议的加载方式与生效时机。

#### Scenario: 启动代理
- **WHEN** Smart-Provider 启动
- **THEN** 文档 SHALL 说明配置应在启动时读取并按当前值运行，动态更新可作为后续增强
