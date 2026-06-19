# Technology-Stack Capability

## Purpose

定义 Smart-Provider 在运行时、开发测试与部署交付中所采用的核心技术栈，为各模块的实现提供一致的技术约束与演进边界，降低模块间集成成本，并避免重复实现已由成熟库提供的通用能力。

## Principles

- 优先复用，避免重复造轮子：OpenAI 兼容协议、模型信息、异常类型等通用能力应优先由 litellm SDK 提供。
- 保持对核心控制逻辑的所有权：队列、限速、转发策略由 Smart-Provider 自身实现，不将完整代理职责外包给 litellm proxy。
- 接口抽象，实现可替换：模块级默认实现应通过清晰接口封装，允许未来在不破坏外部契约的前提下替换为 Redis 等外部存储。
- 渐进式扩展：当前阶段仅将已确定或高度确定的技术纳入核心规格，未落地的扩展能力以扩展点形式记录，不强制引入。

## ADDED Requirements

### Requirement: 使用 Python 作为实现语言

Smart-Provider SHALL 使用 Python 3.10 或更高版本作为服务端实现语言。

#### Scenario: 运行时版本检查

- **WHEN** 部署或启动 Smart-Provider
- **THEN** 系统 SHALL 在 Python 3.10+ 环境下可正常运行

### Requirement: 使用 FastAPI 暴露 HTTP 接口

Smart-Provider 的请求接入层 SHALL 使用 FastAPI 框架暴露 OpenAI 兼容的 HTTP 端点。

#### Scenario: 客户端发送聊天补全请求

- **WHEN** 客户端向 Smart-Provider 发送 POST /v1/chat/completions
- **THEN** Ingress SHALL 通过 FastAPI 路由接收并处理该请求

### Requirement: 使用 Uvicorn 作为 ASGI 服务器

Smart-Provider 在生产环境启动时 SHALL 通过 Uvicorn 运行 FastAPI 应用。

#### Scenario: 服务启动

- **WHEN** 启动 Smart-Provider 服务
- **THEN** 系统 SHALL 使用 Uvicorn 作为 ASGI 服务器监听配置端口

### Requirement: 使用 Pydantic 进行数据验证与序列化

Smart-Provider SHALL 使用 Pydantic 对配置、请求体、响应体及模块间传递的数据结构进行验证与序列化。

#### Scenario: 请求体验证

- **WHEN** Ingress 接收到客户端请求体
- **THEN** 系统 SHALL 使用 Pydantic 模型校验字段类型与必填项

### Requirement: 使用 litellm SDK 处理模型协议与上游调用

Smart-Provider SHALL 使用 litellm SDK 提供的类型、工具函数、异常体系与上游调用能力，处理 OpenAI 兼容的聊天补全协议，而不是自行实现完整的协议解析、模型映射或错误码转换。

#### Scenario: 解析聊天补全请求

- **WHEN** 请求体到达 Ingress
- **THEN** Ingress SHALL 使用 litellm 提供的请求类型解析请求体

#### Scenario: 校验模型名称

- **WHEN** 请求中包含 model 字段
- **THEN** Ingress SHALL 使用 litellm 提供的模型信息能力校验模型是否可识别

#### Scenario: 调用上游 API

- **WHEN** 限速器放行一个请求
- **THEN** Forwarder SHALL 优先使用 litellm 的 acompletion() 调用上游模型 API

### Requirement: litellm 作为 SDK 而非 proxy 使用

Smart-Provider SHALL 将 litellm 作为 SDK 使用，而不是直接部署或代理 litellm proxy，以保留对请求队列、速率控制与转发策略的完整控制权。

#### Scenario: 架构边界澄清

- **WHEN** 设计或扩展 Smart-Provider 的部署形态
- **THEN** 系统 SHALL 由自身实现排队与限速逻辑，而不是通过 litellm proxy 的配置间接完成

### Requirement: 使用 pytest 与 httpx 进行自动化测试

Smart-Provider 的单元测试与集成测试 SHALL 使用 pytest 作为测试框架，使用 httpx 作为 HTTP 客户端。

#### Scenario: 端点集成测试

- **WHEN** 编写 Ingress 端点测试
- **THEN** 测试 SHALL 使用 pytest 组织，并通过 httpx-based TestClient 发起请求

### Requirement: 使用 setuptools 与 wheel 进行打包

Smart-Provider SHALL 使用 setuptools 与 wheel 作为构建与打包工具，依赖声明集中管理在 pyproject.toml 中。

#### Scenario: 构建分发包

- **WHEN** 构建 Smart-Provider 安装包
- **THEN** 系统 SHALL 通过 setuptools 与 wheel 生成标准 Python 分发包

### Requirement: 队列默认使用内存实现并支持未来替换

Smart-Provider 的请求队列当前阶段 SHALL 使用内存 FIFO 队列作为默认实现，但其接口应抽象为独立模块，允许未来替换为优先级队列或基于外部存储的队列。

#### Scenario: 当前默认队列

- **WHEN** 未配置外部队列后端时
- **THEN** 系统 SHALL 使用内存 FIFO 队列暂存请求上下文

#### Scenario: 未来队列扩展

- **WHEN** 需要引入优先级队列或持久化队列时
- **THEN** 新实现 SHALL 在保持 enqueue / dequeue 等核心接口不变的前提下替换默认实现

### Requirement: 限速器默认使用内存滑动窗口并支持未来替换

Smart-Provider 的 RPM 限速器当前阶段 SHALL 使用基于内存的滑动窗口算法，但其接口应抽象为独立模块，允许未来替换为基于 Redis 等共享存储的分布式限速器。

#### Scenario: 当前默认限速

- **WHEN** 系统以单实例运行时
- **THEN** 限速器 SHALL 基于内存滑动窗口统计最近一分钟内的请求数并决定是否放行

#### Scenario: 未来分布式限速

- **WHEN** 需要多实例共享限速状态时
- **THEN** 新实现 SHALL 在保持限速器对外接口不变的前提下替换存储后端

### Requirement: 可观测性使用标准日志与 litellm 回调命名空间

Smart-Provider 当前阶段 SHALL 使用 Python 标准库 logging 记录关键事件，并复用 litellm 的日志命名空间或回调机制；未来可扩展为结构化日志或 Prometheus 指标。

#### Scenario: 请求入队日志

- **WHEN** 一个请求成功入队
- **THEN** Ingress SHALL 通过日志记录 requestId、model、clientId 等关键字段

#### Scenario: 异常事件日志

- **WHEN** 发生请求解析失败、模型不存在或队列已满等异常
- **THEN** 系统 SHALL 通过日志或 litellm 回调机制记录事件类型与上下文

## Technology Summary

| 层级 | 技术/工具 | 用途 |
|------|----------|------|
| 语言运行时 | Python 3.10+ | 服务端实现语言 |
| HTTP 框架 | FastAPI | 暴露 OpenAI 兼容端点 |
| ASGI 服务器 | Uvicorn | 运行 FastAPI 应用 |
| 数据验证 | Pydantic | 请求体、配置、响应体验证 |
| 配置加载 | pydantic-settings | 从环境变量加载配置 |
| LLM SDK | litellm SDK | 协议解析、模型校验、异常分类、上游调用 |
| 队列（默认） | 内存 FIFO | 当前阶段请求缓冲 |
| 限速器（默认） | 内存滑动窗口 | 当前阶段 RPM 控制 |
| 日志/观测 | Python logging + litellm 回调命名空间 | 当前阶段事件记录 |
| 测试框架 | pytest | 单元测试与集成测试 |
| HTTP 测试客户端 | httpx | TestClient 与上游调用测试 |
| 构建工具 | setuptools + wheel | Python 包构建与分发 |

## Extension Points

以下技术能力当前阶段不强制引入，但在后续阶段可依据独立变更纳入：

- 分布式状态存储：Redis 等共享存储，用于多实例间的队列持久化或分布式限速。
- 优先级队列：在保持队列接口抽象的前提下，替换 FIFO 实现。
- 熔断器：基于上游错误率触发快速失败，避免无效请求堆积。
- 结构化日志 / 指标：JSON 日志、Prometheus 指标、OpenTelemetry 追踪等可观测性增强。
- 配置中心：Pydantic Settings、环境变量注入或外部配置服务。

## Notes

- 本规格定义的是当前默认 + 演进边界，而非永久锁定。当某个模块需要引入本规格未列出的新技术时，应通过 OpenSpec 变更流程更新本规格或新增对应 capability 规格。
- litellm 的版本应在 pyproject.toml 中锁定主版本号，升级时须回归 Ingress 与 Forwarder 相关测试。
