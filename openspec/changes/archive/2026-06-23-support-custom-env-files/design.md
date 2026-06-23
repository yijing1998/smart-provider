## Context

Smart-Provider 使用 `pydantic-settings` 加载配置。`src/config/schema.py` 在 `SettingsConfigDict` 中硬编码了 `env_file=".env"`，`src/config/loader.py` 只是简单调用 `Config(**overrides)`。当前测试和文档均假设只有 `.env` 一种文件来源。

`pydantic-settings` 支持在实例化时通过 `_env_file` 参数覆盖 `env_file` 配置，也支持传入列表实现多文件加载。本次变更利用这一机制，在 `load_config()` 中动态决定读取哪些文件。

## Goals / Non-Goals

**Goals:**

- 支持通过 `SMART_PROVIDER_ENV_FILE` 环境变量指定单个 env 文件路径。
- 支持通过 `--env-file <path>` CLI 参数指定单个 env 文件路径。
- 明确优先级：`--env-file` > `SMART_PROVIDER_ENV_FILE` > 默认 `.env`。
- 显式指定的文件不存在时，服务启动阶段报错退出。
- 默认未指定时，行为与当前完全一致（加载 `.env`，不存在则静默忽略）。

**Non-Goals:**

- 不支持多个 `--env-file` 参数叠加。
- 不支持 `SMART_PROVIDER_ENV_FILE` 包含多个逗号分隔路径。
- 不改变 `Config()` 直接实例化的行为（仅 `load_config()` 支持自定义文件解析）。
- 不引入新的配置 schema 字段或依赖。

## Decisions

### 1. 在 `load_config()` 中解析文件来源，而非修改 `Config` 类

**决策**：保持 `Config.model_config` 中的 `env_file=".env"` 不变，在 `load_config()` 中根据环境变量和 CLI 参数计算实际文件路径，通过 `Config(_env_file=path, **overrides)` 传入。

**理由**：
- `Config` 类保持简单，继续按类定义行为加载 `.env`。
- `load_config()` 作为生产入口，承担环境感知和 CLI 解析职责。
- 测试可以分别覆盖：直接 `Config()` 测试默认行为，`load_config()` 测试自定义文件行为。

**替代方案**：在 `Config.__init__` 或 model_config 中动态解析。未采纳原因：会让模型类承担不属于它的环境/CLI 解析逻辑，且更难测试。

### 2. `--env-file` 不支持多次出现

**决策**：只解析命令行中第一次出现的 `--env-file <path>`（或 `--env-file=<path>`），多次出现时取第一个或报错。

**理由**：
- 用户已明确决定不支持多文件叠加，降低复杂度。
- uvicorn 自带的 `--env-file` 本身也只使用最后一个值，行为不一致会带来困惑；限定为单文件更易于文档说明。

**替代方案**：收集所有 `--env-file` 出现的位置并按顺序加载。未采纳原因：与 uvicorn 行为冲突，且用户已选择不支持。

### 3. 显式文件不存在时启动报错

**决策**：当 `SMART_PROVIDER_ENV_FILE` 或 `--env-file` 指定的文件不存在时，服务在启动阶段抛出异常并退出。

**理由**：
- 显式配置具有较强的用户意图，静默忽略会导致“配置未生效却启动成功”的隐蔽问题。
- 符合项目现有 fail-fast 的校验风格。

**替代方案**：显式文件不存在时也静默忽略。未采纳原因：会增加排查成本，与 fail-fast 原则冲突。

### 4. 默认 `.env` 不存在时仍静默忽略

**决策**：未指定自定义文件时，`.env` 不存在继续按当前行为处理（静默忽略，使用默认值/环境变量）。

**理由**：
- 保持完全向后兼容，避免破坏现有部署。
- `.env` 是可选的默认文件，不存在并不代表配置错误。

## Risks / Trade-offs

- **[风险] CLI 参数解析与 uvicorn 未来版本不兼容** → 缓解：使用简单的 `sys.argv` 扫描，只识别 `--env-file` 及其紧接值；不依赖 uvicorn 内部实现细节。
- **[风险] 用户混淆 uvicorn 自带 `--env-file` 与 Smart-Provider 的 `--env-file`** → 缓解：文档中明确说明两者都会被识别，且 Smart-Provider 读取的文件优先级高于 uvicorn 注入的环境变量；同时给出推荐用法。
- **[风险] `--env-file` 值出现在进程列表中可能泄露路径** → 缓解：这是 CLI 参数的通用限制，文档中建议使用 `SMART_PROVIDER_ENV_FILE` 环境变量方式以避免路径暴露在 `ps` 中。
- **[权衡] 单文件 vs 多文件** → 选择单文件。理由：用户已明确只需要单文件，实现和文档更简洁。
