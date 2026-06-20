## Context

配置管理实现已落地：

- `src/config/schema.py` 使用 `pydantic-settings.BaseSettings` 定义全部字段与组件视图。
- `src/config/loader.py` 提供 `load_config(**overrides)`。
- `tests/test_config.py` 覆盖默认值、环境变量、`.env` 文件、校验失败与组件视图。
- `openspec/specs/configuration/spec.md` 已同步。

但面向使用者的入口文档缺失：`README.md` 未说明如何配置，`docs/` 目录只有 `ingress.md`。本次变更补齐文档，使配置来源、环境变量、默认值、校验规则和维护扩展方式易于查找。

## Goals / Non-Goals

**Goals:**

- 在 `docs/configuration.md` 中提供完整的运维/使用者配置参考。
- 在 `docs/config-module.md` 中提供开发者维护与扩展指南。
- 在 `README.md` 中新增轻量“配置”入口，指向上述两篇文档。
- 确保文档中的默认值、校验规则与 `src/config/schema.py` 完全一致。

**Non-Goals:**

- 不修改配置 schema、加载逻辑或测试。
- 不引入新的配置字段或能力。
- 不在 README 中完整重复 `docs/configuration.md` 的表格。

## Decisions

### 1. 将文档拆分为使用者文档与开发者文档两篇

**决策**：新建 `docs/configuration.md`（运维/使用者）和 `docs/config-module.md`（开发者），而非合并成一篇。

**理由**：
- 使用者关心“怎么配、默认值是什么、启动命令是什么”，不关心代码结构。
- 开发者关心“模块拆分、组件视图、如何新增字段”，两者阅读目的不同。
- 两篇文档各自独立演进，避免一篇文档同时面向两个受众导致结构混乱。

**替代方案**：合并为一篇大文档。未采纳原因：会同时包含大量 env var 表格和代码设计说明，目录结构臃肿。

### 2. README 只做入口，不做完整参考

**决策**：在 `README.md` 中新增“配置”小节，只包含最小可运行示例和链接，不重复完整环境变量表。

**理由**：
- README 应保持入口属性，过长会降低可读性。
- 完整表格放在 `docs/configuration.md` 便于维护，避免后续配置变更时要同步多处。
- 链接能引导有需要的用户进入详细文档。

**替代方案**：将完整配置表嵌入 README。未采纳原因：与 docs 重复，维护成本高。

### 3. 文档中的默认值以 `src/config/schema.py` 为唯一事实来源

**决策**：所有默认值、校验范围、字段说明直接对应 `schema.py` 中的 `Field(default=..., ge=..., le=...)` 和注释。

**理由**：
- 避免文档与代码不一致。
- 新增字段时只需对照代码更新文档，逻辑清晰。

## Risks / Trade-offs

- **[风险] 文档与代码后续不一致** → 缓解：文档中明确“默认值来自 `src/config/schema.py`”，并在新增字段时同步更新文档。
- **[风险] 用户未注意到 docs/ 目录链接** → 缓解：README“配置”小节使用醒目标题，并直接给出最小 `.env` 示例，降低跳转成本。
- **[权衡] 两篇文档 vs 一篇文档** → 选择两篇。理由：受众分离，长期维护更清晰；短期成本只是多一个文件。
