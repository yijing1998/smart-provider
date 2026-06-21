# Configuration Capability

## Purpose

定义 Smart-Provider 的运行时配置模型、加载方式与校验规则，确保服务启动时能够正确读取上游地址、RPM 限制、队列容量、超时时间等关键参数。同时为 TPM 限速、熔断器、可观测性、分布式限速等路线图中的扩展能力预留全局配置字段。

## Requirements

### Requirement: 配置上游目标地址

Smart-Provider SHALL 支持配置真实上游 API Endpoint 的地址。

#### Scenario: 启动时加载目标地址

- **WHEN** Smart-Provider 启动
- **THEN** 系统 SHALL 读取配置中的上游 API 地址，并用于后续请求转发

### Requirement: 配置 RPM 限制

Smart-Provider SHALL 支持配置目标上游 API 的 RPM 限制值。

#### Scenario: 设置 RPM 限制

- **WHEN** 管理员配置 RPM 限制为 60
- **THEN** 限速器 SHALL 以 60 作为每分钟最大请求数执行限速

### Requirement: 配置队列容量与等待时间

Smart-Provider SHALL 支持配置请求队列最大容量和请求在队列中的最大等待时间。

#### Scenario: 设置队列容量与等待时间

- **WHEN** 管理员配置队列最大容量为 1000、队列最大等待时间为 30000 毫秒
- **THEN** 系统 SHALL 按这些参数运行，队列超过 1000 时拒绝新请求，超过最大等待时间的请求标记为等待超时

### Requirement: 配置上游转发超时

Smart-Provider SHALL 支持配置上游 API 请求的超时时间。

#### Scenario: 设置上游转发超时

- **WHEN** 管理员配置上游转发超时时间为 30000 毫秒
- **THEN** 上游转发层 SHALL 在调用上游 API 时以该时间作为超时阈值

### Requirement: 配置上游转发重试策略

Smart-Provider SHALL 支持配置上游请求失败后的重试次数与退避时间。

#### Scenario: 设置重试参数

- **WHEN** 管理员配置 `forwarder_max_retries` 为 3、`forwarder_retry_backoff_ms` 为 1000
- **THEN** 上游转发层 SHALL 在失败时最多重试 3 次，并以 1000 毫秒为基数进行退避

### Requirement: 配置滑动窗口宽度

Smart-Provider SHALL 支持配置 RPM 限速器的滑动窗口宽度。

#### Scenario: 设置窗口宽度

- **WHEN** 管理员配置 `rate_limit_window_seconds` 为 60
- **THEN** 限速器 SHALL 以 60 秒为窗口统计最近已发送请求数

### Requirement: 使用 Pydantic Settings 加载配置

Smart-Provider SHALL 使用 Pydantic BaseModel 或 pydantic-settings 定义配置模型，并从环境变量或配置文件加载运行时参数。

#### Scenario: 从环境变量加载配置

- **WHEN** 启动 Smart-Provider 且存在以 `SMART_PROVIDER_` 为前缀的环境变量
- **THEN** 系统 SHALL 将这些环境变量映射到对应的配置字段

#### Scenario: 从 .env 文件加载配置

- **WHEN** 启动目录下存在 `.env` 文件且包含 `SMART_PROVIDER_` 前缀的配置项
- **THEN** 系统 SHALL 读取该文件并将其作为配置来源，优先级次于显式环境变量

#### Scenario: 配置类型校验

- **WHEN** 配置加载时某个字段类型不匹配或超出允许范围
- **THEN** 系统 SHALL 在启动阶段报错并阻止服务以无效配置运行

### Requirement: 配置字段支持范围校验

Smart-Provider 的配置模型 SHALL 对关键数值字段进行最小范围校验，例如 RPM 必须大于 0、端口必须在有效范围内、队列容量必须非负、超时时间必须大于 0。

#### Scenario: 配置无效范围

- **WHEN** 管理员将 `rate_limit_rpm` 设置为 0 或负数
- **THEN** 系统 SHALL 拒绝该配置并提示错误

#### Scenario: 配置端口超出有效范围

- **WHEN** 管理员将 `server_port` 设置为 0 或 65536
- **THEN** 系统 SHALL 拒绝该配置并提示错误

#### Scenario: 配置队列容量为负数

- **WHEN** 管理员将 `queue_max_size` 设置为负数
- **THEN** 系统 SHALL 拒绝该配置并提示错误

### Requirement: 配置与 technology-stack 一致

Smart-Provider 的配置管理实现 SHALL 遵循 technology-stack capability 中定义的技术约束，使用 Pydantic 进行数据验证。

#### Scenario: 审查配置模块实现

- **WHEN** 审查 src/config/ 模块的实现
- **THEN** 系统 SHALL 使用 Pydantic 模型或 pydantic-settings 表达配置，而不是裸字典或 dataclass

### Requirement: 配置 TPM 限制值

Smart-Provider 的配置模型 SHALL 包含 TPM 限制字段，供未来按 Token 数限速使用。

#### Scenario: 配置 TPM 字段

- **WHEN** 管理员配置 `rate_limit_tpm` 为 4000000
- **THEN** 系统 SHALL 成功加载该配置，当前实现可保留但不强制消费该字段

### Requirement: 配置熔断器参数

Smart-Provider 的配置模型 SHALL 包含熔断器相关字段，供未来实现熔断器使用。

#### Scenario: 配置熔断器字段

- **WHEN** 管理员配置 `circuit_breaker_enabled=false`、`circuit_breaker_failure_threshold=5`、`circuit_breaker_recovery_timeout_ms=30000`
- **THEN** 系统 SHALL 成功加载这些字段，当前实现可保留但不强制消费

### Requirement: 配置可观测性参数

Smart-Provider 的配置模型 SHALL 包含日志级别与指标开关字段，供未来可观测性模块使用。

#### Scenario: 配置可观测性字段

- **WHEN** 管理员配置 `observability_log_level=INFO`、`observability_metrics_enabled=false`
- **THEN** 系统 SHALL 成功加载这些字段，当前实现可保留但不强制消费

### Requirement: 配置分布式限速器参数

Smart-Provider 的配置模型 SHALL 包含分布式限速器开关与后端地址字段，供未来多实例共享限速状态使用。

#### Scenario: 配置分布式限速器字段

- **WHEN** 管理员配置 `distributed_rate_limiter_enabled=false`、`distributed_rate_limiter_url=redis://localhost:6379`
- **THEN** 系统 SHALL 成功加载这些字段，当前实现可保留但不强制消费

### Requirement: 配置模型支持远期扩展字段

Smart-Provider 的配置模型 SHALL 为路线图中的扩展能力预留字段，且默认处于关闭或未启用状态，不影响当前行为。

#### Scenario: 默认不启用远期字段

- **WHEN** 管理员未配置任何熔断器、分布式限速器或可观测性相关字段
- **THEN** 系统 SHALL 使用默认值启动，且当前功能不受这些字段影响

### Requirement: 配置优雅关闭排空超时

Smart-Provider SHALL 支持配置服务关闭时等待队列排空的最大时间。

#### Scenario: 设置关闭排空超时

- **WHEN** 管理员配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 为 30000
- **THEN** 系统 SHALL 在关闭阶段最多等待 30000 毫秒处理队列中的请求

#### Scenario: 未配置时使用默认排空超时

- **WHEN** 管理员未配置 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS`
- **THEN** 系统 SHALL 使用默认值 30000 毫秒

#### Scenario: 配置无效的排空超时

- **WHEN** 管理员将 `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` 设置为 0 或负数
- **THEN** 系统 SHALL 在启动时拒绝该配置并提示错误
