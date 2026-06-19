## Why

Smart-Provider 的架构设计与实现指导文档已经明确了“先排队，再放行”的核心思路，且 `src/ingress/` 已使用 Python + FastAPI + litellm SDK 完成初步实现。然而，当前 `openspec/specs/` 下的主规格文件中缺少统一的技术栈说明，导致队列、限速器、转发器、配置管理等模块在后续实现时缺乏技术约束，容易出现重复实现、依赖选择不一致或接口替换困难等问题。同时，Ingress 与 Forwarder 之间的同步/异步边界、配置的环境变量加载方式等关键设计也未在规格层固化。因此，需要系统性地在 OpenSpec 规格中补充并标准化 Smart-Provider 的技术栈，为后续模块实现与代码演进提供一致依据。

## What Changes

- 新增 `technology-stack` capability 规格，定义 Smart-Provider 在运行时、开发测试与部署交付中所采用的核心技术栈，以及模块默认实现与未来扩展点。
- 修改 `request-ingress` capability 规格，明确其应遵循 `technology-stack` 中定义的 Python + FastAPI + litellm SDK 技术约束。
- 修改 `upstream-forwarding` capability 规格，明确 Forwarder 应使用 litellm SDK 的 `acompletion()` 以异步方式调用上游 API，并通过异步机制将结果返回给 Ingress。
- 修改 `configuration` capability 规格，明确配置管理应使用 Pydantic Settings，支持从环境变量加载运行时参数。
- 更新 `pyproject.toml`，显式声明 `pydantic` 与 `pydantic-settings` 作为直接依赖，以支撑规格中定义的技术栈。

## Capabilities

### New Capabilities

- `technology-stack`：定义 Smart-Provider 全局技术栈约束，包括运行时语言、HTTP 框架、ASGI 服务器、数据验证、LLM SDK、测试框架、构建工具，以及队列、限速器、配置、可观测性等模块的默认实现与演进边界。

### Modified Capabilities

- `request-ingress`：补充 Ingress 实现所遵循的技术栈引用，明确使用 FastAPI 暴露端点、使用 litellm SDK 解析请求与分类异常。
- `upstream-forwarding`：补充 Forwarder 的异步实现要求，明确使用 litellm SDK 的 `acompletion()` 调用上游 API，并说明结果回传机制。
- `configuration`：补充配置管理使用 Pydantic Settings，支持环境变量加载与类型校验。

## Impact

- **规格文档**：`openspec/specs/technology-stack/spec.md` 新增；`openspec/specs/request-ingress/spec.md`、`openspec/specs/upstream-forwarding/spec.md`、`openspec/specs/configuration/spec.md` 的需求章节需要补充或调整。
- **依赖声明**：`pyproject.toml` 的 `dependencies` 中需要显式添加 `pydantic` 与 `pydantic-settings`。
- **实现侧影响**：本变更仅产出规格与依赖声明，不直接修改 `src/` 下的应用代码。但本规格将成为后续 `config`、`forwarder`、`limiter` 等模块实现时的参考依据。
- **兼容性**： Forwarder 从同步接口转向异步接口属于接口契约变化，后续实现时需同步调整 Ingress 中的调用方式；该变化在应用代码层面属于 **BREAKING** 调整，但当前 Forwarder 仍为 stub 实现，影响范围可控。
