## ADDED Requirements

### Requirement: 使用 Pydantic Settings 加载配置

Smart-Provider SHALL 使用 Pydantic BaseModel 或 pydantic-settings 定义配置模型，并从环境变量或配置文件加载运行时参数。

#### Scenario: 从环境变量加载配置

- **WHEN** 启动 Smart-Provider 且存在以 SMART_PROVIDER_ 为前缀的环境变量
- **THEN** 系统 SHALL 将这些环境变量映射到对应的配置字段

#### Scenario: 配置类型校验

- **WHEN** 配置加载时某个字段类型不匹配或超出允许范围
- **THEN** 系统 SHALL 在启动阶段报错并阻止服务以无效配置运行

### Requirement: 配置字段支持范围校验

Smart-Provider 的配置模型 SHALL 对关键数值字段进行最小范围校验，例如 RPM 必须大于 0、端口必须在有效范围内、队列容量必须非负。

#### Scenario: 配置无效范围

- **WHEN** 管理员将 rate_limit_rpm 设置为 0 或负数
- **THEN** 系统 SHALL 拒绝该配置并提示错误

### Requirement: 配置与 technology-stack 一致

Smart-Provider 的配置管理实现 SHALL 遵循 technology-stack capability 中定义的技术约束，使用 Pydantic 进行数据验证。

#### Scenario: 审查配置模块实现

- **WHEN** 审查 src/config/ 模块的实现
- **THEN** 系统 SHALL 使用 Pydantic 模型或 pydantic-settings 表达配置，而不是裸字典或 dataclass
