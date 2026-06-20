## Why

`2026-06-20-implement-config-management` 已完成并实现落地，代码、测试与 `openspec/specs/configuration/spec.md` 均已同步。但 `README.md` 中没有配置说明，`docs/` 目录也缺少面向使用者和开发者的配置参考文档，导致新用户无法快速了解 `SMART_PROVIDER_` 前缀、`.env` 文件支持、默认值与校验规则。本次变更补齐这一文档缺口。

## What Changes

- 在 `docs/` 目录下新建 `configuration.md`，面向运维与使用者：
  - 说明配置加载优先级（环境变量 > `.env` 文件 > 默认值）。
  - 列出所有 `SMART_PROVIDER_` 前缀环境变量，包含默认值、校验规则与字段说明。
  - 给出 `.env` 文件示例与常见启动校验错误说明。
  - 提供默认启动命令。
- 在 `docs/` 目录下新建 `config-module.md`，面向开发者：
  - 说明 `src/config/schema.py`、`loader.py`、`__init__.py` 的职责边界。
  - 解释组件视图（`config.queue`、`config.limiter` 等）的设计意图。
  - 说明如何新增配置字段以及 reserved 字段的约定。
  - 给出扩展配置模块时的测试与同步建议。
- 在 `README.md` 中新增“配置”入口小节，给出最小运行示例，并链接到 `docs/configuration.md` 与 `docs/config-module.md`。

## Capabilities

### New Capabilities

- `configuration-docs`：提供配置管理相关参考文档，包括面向运维/使用者的 `docs/configuration.md`、面向开发者的 `docs/config-module.md`，以及 `README.md` 中的配置入口链接。

### Modified Capabilities

无。本次变更不修改现有产品能力的需求定义。

## Impact

- 新增文档文件：`docs/configuration.md`、`docs/config-module.md`。
- 更新文档文件：`README.md`（新增配置入口小节）。
- 无代码、API、依赖或部署行为变化。
