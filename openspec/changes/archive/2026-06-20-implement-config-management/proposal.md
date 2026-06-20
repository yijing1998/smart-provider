## Why

当前 `src/config/config.py` 仍使用 `dataclass` 和手工 `from_dict` 实现，与 `openspec/specs/configuration/spec.md` 中“使用 Pydantic / pydantic-settings 加载配置、支持环境变量、启动时校验”的要求不符。同时，现有 `Config` 只覆盖了最小字段集合，无法容纳 TPM、熔断器、分布式限速等路线图中的扩展能力。本次变更将配置管理组件升级为基于 Pydantic Settings 的完整实现，并为未来能力预留全局配置骨架。

## What Changes

- 将 `src/config/config.py` 中的 `Config` 从 `dataclass` 迁移为 `pydantic-settings.BaseSettings`。
- 支持以 `SMART_PROVIDER_` 为前缀的扁平环境变量加载配置，并支持 `.env` 文件（新增 `python-dotenv` 依赖）。
- 为所有配置字段增加类型校验与最小范围校验，非法配置在启动阶段即报错。
- 删除未使用的 `Config.from_dict` 方法，统一使用 Pydantic 构造语义。
- 将 `src/config/` 拆分为 `schema.py`、`loader.py` 与 `__init__.py`，明确数据模型与加载机制的边界。
- 新增 `queue_max_wait_ms` 配置字段，并修正 `src/ingress/app.py` 中 `RequestContext.max_wait_time_ms` 的语义来源（由 `forwarder_timeout_ms` 改为 `queue_max_wait_ms`）。
- 在配置 schema 中为远期能力占位：TPM、重试退避、熔断器、可观测性开关、分布式限速器，默认关闭，当前代码不消费。
- 为 `src/config/` 补充单元测试，覆盖默认值、环境变量加载、范围校验失败等场景。
- 修改 `openspec/specs/configuration/spec.md`，明确新增字段、环境变量前缀、.env 支持及校验规则。

**BREAKING**: `Config.from_dict(dict)` 将被移除，外部调用方需改为 `Config(**dict)`。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `configuration`: 更新配置加载方式、字段集合与校验规则，明确 Pydantic Settings、扁平环境变量、.env 文件支持、范围校验及远期扩展字段。

## Impact

- 受影响代码：`src/config/`、`src/ingress/app.py`、相关单元测试。
- 依赖变化：`pyproject.toml` 新增 `python-dotenv>=1.0.0`。
- 部署影响：现有通过环境变量注入的配置行为保持不变；新增 `.env` 文件作为可选加载源。
