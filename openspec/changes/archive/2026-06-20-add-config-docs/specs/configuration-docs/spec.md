## ADDED Requirements

### Requirement: 提供配置参考文档

Smart-Provider SHALL 为运维人员与开发者提供配置管理参考文档，并在 `README.md` 中提供入口链接。

#### Scenario: 运维人员查找环境变量说明

- **WHEN** 运维人员打开 `docs/configuration.md`
- **THEN** 文档 SHALL 包含所有 `SMART_PROVIDER_` 前缀环境变量、默认值、校验规则、`.env` 示例与启动校验说明

#### Scenario: 开发者查找模块扩展说明

- **WHEN** 开发者打开 `docs/config-module.md`
- **THEN** 文档 SHALL 包含 `src/config/` 模块职责划分、组件视图说明、新增字段流程与 reserved 字段约定

#### Scenario: README 提供配置入口

- **WHEN** 新用户阅读 `README.md`
- **THEN** `README.md` SHALL 包含“配置”小节，给出最小示例并链接到 `docs/configuration.md` 与 `docs/config-module.md`
