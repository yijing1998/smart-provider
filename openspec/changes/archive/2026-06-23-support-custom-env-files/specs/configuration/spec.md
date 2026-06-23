## MODIFIED Requirements

### Requirement: 使用 Pydantic Settings 加载配置

Smart-Provider SHALL 使用 Pydantic BaseModel 或 pydantic-settings 定义配置模型，并从环境变量、`.env` 文件或用户显式指定的 env 文件加载运行时参数。

#### Scenario: 从环境变量加载配置

- **WHEN** 启动 Smart-Provider 且存在以 `SMART_PROVIDER_` 为前缀的环境变量
- **THEN** 系统 SHALL 将这些环境变量映射到对应的配置字段

#### Scenario: 从 .env 文件加载配置

- **WHEN** 启动目录下存在 `.env` 文件且包含 `SMART_PROVIDER_` 前缀的配置项
- **THEN** 系统 SHALL 读取该文件并将其作为配置来源，优先级次于显式环境变量

#### Scenario: 从 SMART_PROVIDER_ENV_FILE 指定的文件加载配置

- **WHEN** 用户设置了 `SMART_PROVIDER_ENV_FILE=prod.env` 且该文件存在
- **THEN** 系统 SHALL 从 `prod.env` 加载配置，并忽略默认的 `.env` 文件

#### Scenario: 从 --env-file CLI 参数指定的文件加载配置

- **WHEN** 用户启动时传入 `--env-file prod.env` 且该文件存在
- **THEN** 系统 SHALL 从 `prod.env` 加载配置，并忽略默认的 `.env` 文件以及 `SMART_PROVIDER_ENV_FILE` 环境变量

#### Scenario: 配置类型校验

- **WHEN** 配置加载时某个字段类型不匹配或超出允许范围
- **THEN** 系统 SHALL 在启动阶段报错并阻止服务以无效配置运行

#### Scenario: 显式指定的 env 文件不存在时启动失败

- **WHEN** 用户通过 `SMART_PROVIDER_ENV_FILE` 或 `--env-file` 指定了一个不存在的文件
- **THEN** 系统 SHALL 在启动阶段抛出错误并退出

#### Scenario: 未指定自定义文件且 .env 不存在时使用默认值

- **WHEN** 用户未设置 `SMART_PROVIDER_ENV_FILE` 或 `--env-file`，且工作目录下不存在 `.env` 文件
- **THEN** 系统 SHALL 使用默认值启动，不报错
