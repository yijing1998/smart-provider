## Context

Smart-Provider 当前在 `src/config/config.py` 中使用 `dataclass` 定义 `Config`，并通过手工 `from_dict` 方法从字典加载配置。这与 `openspec/specs/configuration/spec.md` 中要求的“使用 Pydantic / pydantic-settings、支持环境变量、启动时校验”不一致。同时，现有字段集合仅覆盖 `upstream_url`、`rate_limit_rpm`、`queue_max_size`、`forwarder_timeout_ms`、`server_port`、`client_id_header`，无法支撑路线图中的 TPM 限速、优先级队列、熔断器、分布式限速等能力。

本次变更旨在将配置管理组件升级为基于 Pydantic Settings 的实现：环境变量扁平加载、启动时校验、内部按组件视图分组，并为远期能力预留全局字段。

## Goals / Non-Goals

**Goals:**

- 使用 `pydantic-settings.BaseSettings` 重新定义 `Config`，支持 `SMART_PROVIDER_` 前缀的扁平环境变量。
- 支持 `.env` 文件作为可选配置来源。
- 对所有数值字段增加最小范围校验，非法配置在启动阶段失败。
- 将 `src/config/` 拆分为 `schema.py`、`loader.py`、`__init__.py`，明确数据模型与加载机制边界。
- 新增 `queue_max_wait_ms` 字段，并修正 `RequestContext.max_wait_time_ms` 的赋值来源。
- 为 TPM、重试退避、熔断器、可观测性开关、分布式限速器等远期能力预留 schema 字段，默认关闭。
- 补充 `src/config/` 的单元测试。

**Non-Goals:**

- 不实现运行时动态更新配置。
- 不实现按模型、按客户端、按 Endpoint 的差异化配置。
- 不实现熔断器、TPM 限速、分布式限速器、指标端点等远期能力本身（仅预留配置字段）。
- 不引入外部配置中心（如 Consul、Etcd）。

## Decisions

### 1. 使用 `pydantic-settings.BaseSettings` 替代 dataclass

**决策**：`Config` 继承 `pydantic_settings.BaseSettings`，通过 `model_config = SettingsConfigDict(env_prefix="SMART_PROVIDER_")` 加载环境变量。

**理由**：
- 与现有 FastAPI、litellm、pydantic 技术栈一致。
- 自动完成类型转换、环境变量映射、.env 支持，无需手工维护 `from_dict`。
- 可通过 `Field(ge=..., le=...)` 声明式表达范围校验。

**替代方案**：保留 dataclass + 手工 env 解析。未采纳原因：与现有 spec 冲突，且重复实现 pydantic-settings 已提供的通用能力。

### 2. 环境变量命名保持扁平

**决策**：所有环境变量名与 `Config` 顶层字段名一致，前缀为 `SMART_PROVIDER_`，例如 `SMART_PROVIDER_QUEUE_MAX_SIZE`。

**理由**：
- 运维人员无需记忆嵌套分隔符，与现有 dataclass 字段名自然对应。
- 内部组件视图通过 property 暴露（如 `config.queue`），实现加载层扁平、视图层分组。

**替代方案**：使用嵌套模型 + `__` 分隔符（如 `SMART_PROVIDER_QUEUE__MAX_SIZE`）。未采纳原因：与团队运维习惯不一致，且需要额外配置 `env_nested_delimiter`。

### 3. 组件视图通过 property 暴露

**决策**：`Config` 内部保持扁平字段，但提供 `queue`、`limiter`、`forwarder`、`circuit_breaker`、`observability`、`distributed_rate_limiter` 等 property，返回小型 Pydantic 模型。

**理由**：
- 组件构造函数可只依赖自己的配置切片（如 `RequestQueue(config=cfg.queue)`），降低耦合。
- 未来新增字段时，只需在 `Config` 和对应 property 中调整，组件接口保持稳定。

**替代方案**：组件直接读取 `cfg.queue_max_size` 等扁平字段。未采纳原因：组件会依赖全局 Config 的全部字段，不利于未来拆分和热更新扩展。

### 4. 删除 `Config.from_dict`

**决策**：移除 `Config.from_dict(data)` 类方法，统一使用 `Config(**data)`。

**理由**：
- 代码搜索未发现任何调用方。
- Pydantic 构造本身支持 dict unpacking，无需额外方法。

**影响**：这是一个 **BREAKING** 变更，外部调用方需改为 `Config(**data)`。

### 5. 拆分 `src/config/` 模块

**决策**：将配置模块拆分为三个文件：
- `schema.py`：定义 `BaseSettings` 与组件视图模型。
- `loader.py`：提供 `load_config(**overrides)` 工厂函数。
- `__init__.py`：导出公共接口 `Config`、`load_config`。

**理由**：
- 数据模型与加载机制解耦，未来支持文件配置、多 source 合并时改动范围更小。
- 公共接口保持稳定，调用方仍使用 `from src.config import Config, load_config`。

**替代方案**：单文件 `config.py`。未采纳原因：扩展版定位下 schema 会持续增长，早拆分成本低。

### 6. 远期字段默认关闭并标注 reserved

**决策**：将 `rate_limit_tpm`、`circuit_breaker_*`、`observability_*`、`distributed_rate_limiter_*` 等字段纳入 schema，默认值设为关闭或 `None`，并在注释/文档中标注为“reserved for future use”。

**理由**：
- 避免每次新增能力都回头修改配置 schema。
- 默认关闭确保当前行为不变。

**替代方案**：只包含当前会用到的字段。未采纳原因：与“扩展版”目标不符，且会导致未来变更范围扩大。

### 7. 新增 `python-dotenv` 依赖

**决策**：在 `pyproject.toml` 中添加 `python-dotenv>=1.0.0`，并在 `BaseSettings` 中启用 `.env` 文件读取。

**理由**：
- 满足 spec 中“从环境变量或配置文件加载”的要求。
- 本地开发体验更好，容器部署仍可仅使用环境变量。

**替代方案**：仅依赖环境变量。未采纳原因：spec 明确允许配置文件，且 `python-dotenv` 依赖极小。

### 8. 修正 `RequestContext.max_wait_time_ms` 语义

**决策**：将 `ingress/app.py` 中 `RequestContext.max_wait_time_ms` 的赋值从 `cfg.forwarder_timeout_ms` 改为 `cfg.queue_max_wait_ms`。

**理由**：
- `max_wait_time_ms` 的语义是请求在队列中等待的最长时间，而非上游 HTTP 调用超时。
- `forwarder_timeout_ms` 应仅用于上游转发层的 HTTP 超时配置。

## Risks / Trade-offs

- **[风险] Pydantic Settings 环境变量前缀与现有变量冲突** → 缓解：统一使用 `SMART_PROVIDER_` 前缀，避免与 litellm、FastAPI 等库的环境变量混淆。
- **[风险] 新增大量字段导致配置模型臃肿** → 缓解：远期字段默认关闭，组件视图按职责分组，文档明确标注 reserved。
- **[风险] 删除 `Config.from_dict` 破坏外部调用** → 缓解：项目当前版本为 `0.1.0`，代码内无调用方；在 proposal 中标记 BREAKING。
- **[风险] 范围校验过于严格导致旧部署失败** → 缓解：默认值保持与当前一致，仅对显式设置的非法值报错；校验规则采用最小范围（如 `>= 1`）。
- **[权衡] 远期字段现在进入 schema  vs 未来再加** → 选择现在进入。理由：扩展版目标明确，schema 先于实现就绪可降低后续变更成本。
- **[权衡] 组件视图增加少量代码量** → 选择保留视图。理由：降低组件与全局 Config 的耦合，未来扩展更稳定。

## Migration Plan

1. 在 `pyproject.toml` 添加 `python-dotenv>=1.0.0`。
2. 重写 `src/config/schema.py`、`src/config/loader.py`，保留 `from src.config import Config, load_config` 公共接口。
3. 删除 `src/config/config.py`（或保留为空文件过渡后删除）。
4. 修改 `src/ingress/app.py`：使用 `load_config()`，按需读取 `cfg.queue_max_wait_ms` 等字段。
5. 更新 `tests/test_config.py`（新建）与 `tests/test_ingress.py` 中受影响的构造调用。
6. 更新 `openspec/specs/configuration/spec.md` 以反映新增字段与校验规则。
7. 运行全部测试，确认启动时非法配置会被拒绝。

**Rollback**：回退到上一次提交即可恢复 dataclass 实现；由于公共接口 `Config(...)` 仍兼容，只要未依赖 `from_dict`，上层调用不受影响。

## Open Questions

- 是否需要为 `upstream_url` 增加 URL 格式校验（如必须包含 scheme）？当前仅做非空校验，避免对内部测试地址过度约束。
- `observability_log_level` 的取值集合是否严格限定为 `DEBUG/INFO/WARNING/ERROR/CRITICAL`？建议通过 Pydantic `Literal` 或自定义 validator 限定，但需考虑大小写兼容。
