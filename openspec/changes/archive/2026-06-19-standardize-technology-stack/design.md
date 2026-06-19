## Context

Smart-Provider 的核心目标是作为模型 API 请求代理，通过先排队再放行的机制平滑上游流量，降低触发 429 Too Many Requests 的概率。当前项目已具备以下状态：

- README.md 与早期架构设计文档已明确部署形态、核心组件与扩展路线。
- src/ingress/ 已使用 Python + FastAPI + litellm SDK 完成请求接入层的初步实现，能够解析 OpenAI 兼容请求、校验模型、构造内部上下文并提交队列。
- src/queue/、src/forwarder/、src/config/ 等模块仍以 stub 或最小实现存在，技术选型尚未在规格层固化。
- openspec/specs/ 下的主规格文件缺少统一的技术栈说明，Purpose 字段多为 TBD。

在此背景下，各模块后续实现时容易出现依赖选择不一致、接口替换困难、同步/异步边界模糊等问题。本变更旨在通过 OpenSpec 规格系统化地标准化技术栈，并明确几个关键设计决策，为后续编码提供清晰蓝图。

## Goals / Non-Goals

Goals:

- 在规格层定义 Smart-Provider 的全局技术栈，覆盖运行时、开发测试与部署交付。
- 明确 litellm SDK 的使用边界：作为 SDK 复用协议与异常能力，而非直接部署 litellm proxy。
- 明确 Forwarder 采用异步架构，使用 litellm.acompletion() 调用上游，并通过异步机制将结果返回给 Ingress。
- 明确配置管理采用 Pydantic Settings，支持从环境变量加载运行时参数。
- 在 pyproject.toml 中显式声明 pydantic 与 pydantic-settings 依赖。
- 为队列、限速器等模块的默认实现预留接口抽象，允许未来替换为外部存储或分布式方案。

Non-Goals:

- 本变更不修改 src/ 下的应用代码实现，仅产出规格与依赖声明。
- 本变更不实现队列、限速器、可观测性等未落地模块的具体代码。
- 本变更不引入 Redis、Kafka、Prometheus 等当前未确定的扩展依赖。
- 本变更不讨论流式响应 streaming 的完整实现策略，仅保留扩展空间。

## Decisions

### 1. 使用 Python 3.10 或更高版本作为运行时

决策：Smart-Provider 统一使用 Python 3.10+。

理由：
- 当前 Ingress 实现已基于 Python 3.10 特性。
- litellm、FastAPI、Pydantic v2 均对 Python 3.10+ 有良好支持。

替代方案：降级到 Python 3.9。未采纳原因：会失去现代类型注解语法便利，且主流依赖已逐步放弃 3.9 支持。

### 2. 使用 FastAPI + Uvicorn 作为 HTTP 层

决策：Ingress 使用 FastAPI 暴露 HTTP 端点，生产环境通过 Uvicorn 运行。

理由：
- FastAPI 原生支持异步处理与 OpenAPI 文档自动生成。
- Uvicorn 是 FastAPI 的事实标准 ASGI 服务器。
- 与 litellm proxy 的端点约定一致，客户端无需修改即可接入。

替代方案：Flask、Django、Starlette、直接使用 litellm proxy。未采纳原因：Flask 异步支持较弱；Django 过重；Starlette 缺少 FastAPI 的自动验证与文档能力；litellm proxy 会绕过自有的队列与限速器。

### 3. 将 litellm 作为 SDK 而非 proxy 使用

决策：Smart-Provider 使用 litellm SDK 提供的类型、工具函数、异常体系与上游调用能力，不直接部署 litellm proxy。

理由：
- litellm SDK 已提供 OpenAI 兼容的请求类型、模型信息校验、异常分类，避免自研协议栈。
- 若直接使用 litellm proxy，则排队、限速等核心控制逻辑会被 litellm 接管，Smart-Provider 失去存在价值。
- 统一异常类型便于 Ingress 与 Forwarder 共享错误分类。

替代方案：直接使用 litellm proxy，或完全自研 OpenAI 协议解析。未采纳原因：proxy 会替代核心控制；自研协议栈维护成本高且容易遗漏字段。

### 4. 使用 Pydantic + pydantic-settings 管理配置

决策：配置管理从 Python dataclass 迁移至 Pydantic BaseModel / pydantic-settings，支持环境变量加载与类型校验。

理由：
- FastAPI、litellm 已深度使用 Pydantic，技术栈统一。
- pydantic-settings 可直接从 .env 或环境变量读取配置，适合代理服务部署。
- 可对 rate_limit_rpm、queue_max_size、server_port 等字段做范围校验。

替代方案：保留 dataclass + 手动 from_dict。未采纳原因：手动实现环境变量映射与校验重复且容易出错；与现有技术栈不一致。

### 5. Forwarder 使用异步架构

决策：Forwarder 接口改为 async def forward，内部使用 litellm.acompletion() 调用上游，并通过 asyncio.Future 将结果异步返回给 Ingress。

理由：
- 上游 API 调用是 I/O 密集型操作，异步可避免阻塞事件循环，提升并发处理能力。
- litellm 提供 acompletion() 原生异步接口，与 FastAPI 异步端点一致。
- Ingress 入队后等待 Future 结果，可解耦请求入队与结果回传两个阶段。

替代方案：保持同步 completion()，由线程池执行。未采纳原因：线程池会增加复杂性与资源开销；异步是 FastAPI/litellm 生态的自然选择。

### 6. 队列与限速器保持接口抽象

决策：队列当前使用内存 FIFO，限速器当前使用内存滑动窗口，但二者均通过独立模块与接口封装，未来可在不破坏外部契约的前提下替换。

理由：
- 当前阶段实现复杂度最低，便于快速验证核心流程。
- 路线图包含优先级队列、分布式限速等扩展，接口抽象能降低未来替换成本。

替代方案：一开始就引入 Redis 实现队列与限速器。未采纳原因：当前并发与部署规模尚未证明需要外部存储；过早引入会增加运维复杂度。

### 7. 使用 pytest + httpx 进行测试

决策：单元测试与集成测试使用 pytest，HTTP 层测试使用 httpx（含 FastAPI TestClient）。

理由：
- pytest 是 Python 生态主流测试框架。
- FastAPI TestClient 基于 httpx，适合端点集成测试。
- 与当前 pyproject.toml 中的可选依赖一致。

## Risks / Trade-offs

- [风险] litellm 版本兼容性 -> 缓解：在 pyproject.toml 中锁定 litellm 主版本号，升级时回归 Ingress 与 Forwarder 测试。
- [风险] 异步链路调试复杂 -> 缓解：在 design 与 specs 中明确 Future/事件机制，后续实现时补充针对超时、取消、并发的单元测试。
- [风险] Pydantic v1/v2 混用 -> 缓解：显式声明 pydantic>=2.0.0，统一使用 v2 API。
- [风险] 队列/限速器接口过早抽象导致过度设计 -> 缓解：当前接口仅包含最小必要方法，不引入不必要的抽象层。
- [权衡] 同步 vs 异步队列接口 -> 选择：Queue 接口现在就用 async 签名，内存实现做同步兜底。这样未来替换 Redis 时接口不变，但当前实现会多一层 await 包装。
- [权衡] 配置字段范围校验严格程度 -> 选择：对关键字段做最小范围校验，不引入过于复杂的业务规则校验。
