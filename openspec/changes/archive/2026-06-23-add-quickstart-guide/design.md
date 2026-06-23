## Context

Smart-Provider 的核心入口（`POST /v1/chat/completions`）、配置加载（`src/config`）和健康检查端点（`/health`、`/ready`）均已实现并通过测试。现有文档覆盖了架构、完整配置和模块设计，但缺少一份从零到首个请求成功的连贯指南。

本次变更仅涉及文档与示例文件，不改动代码逻辑。

## Goals / Non-Goals

**Goals:**

- 新增 `docs/quickstart.md`，让使用者在 5 分钟内完成首次部署与首个请求验证。
- 新增 `.env.example`，提供可直接复制修改的配置模板。
- 在 `README.md` 中新增“快速开始”入口，链接到 `docs/quickstart.md`。
- 确保 quickstart 中的默认值、端点路径、请求格式与当前代码一致。

**Non-Goals:**

- 不修改配置 schema、加载逻辑或请求处理逻辑。
- 不引入 Docker、Kubernetes 等部署方式。
- 不在 quickstart 中完整重复 `docs/configuration.md` 的表格。

## Decisions

### 1. 文档独立成篇，README 只做入口

**决策**：新建 `docs/quickstart.md`，而不是在 `README.md` 中展开完整步骤。

**理由**：
- README 适合作为项目入口，过长会降低可读性。
- quickstart 需要包含多组命令和说明，独立成篇便于维护和引用。
- 后续可在 `docs/` 目录扩展更多运维文档（如部署指南、监控指南）。

**替代方案**：将 quickstart 内容直接写入 README。未采纳原因：README 会过长，且 `docs/` 目录已经承担详细文档职责。

### 2. 同时提供 `.env.example` 文件

**决策**：在项目根目录新增 `.env.example`，包含常用配置项的示例值和注释。

**理由**：
- 用户复制 `.env.example` 为 `.env` 即可运行，降低配置门槛。
- 示例文件中的注释可以解释字段含义，减少首次阅读 `docs/configuration.md` 的压力。
- 与 `docs/quickstart.md` 中的 `.env` 示例保持一致，避免文档与示例文件冲突。

### 3. quickstart 示例直接对接真实上游 API

**决策**：quickstart 中的 `curl` 示例使用真实模型 API（如 OpenAI），并说明 `Authorization` 请求头会透传给上游。

**理由**：
- 使用者的首要目标是“让 Smart-Provider 真正代理我的请求”，真实示例最直接。
- `src/ingress/context.py` 已将 `extra_headers` 传入转发层，用户只需按正常 OpenAI 调用方式提供 `Authorization`。
- 若使用 mock 示例，用户还需要额外理解 mock 场景，增加认知负担。

**替代方案**：使用本地 stub forwarder 示例。未采纳原因：不符合使用者场景，且需要修改运行方式。

### 4. 包含流式请求与健康检查示例

**决策**：在 quickstart 中补充 `stream=true` 的 `curl` 示例，以及 `/health`、`/ready` 的调用说明。

**理由**：
- 流式响应是 Smart-Provider 已支持的能力，使用者可能直接需要。
- 健康检查端点是部署和验证服务可用性的常用手段，值得在入门文档中提及。
- 这两个示例不会显著增加文档长度，但能覆盖更多首次使用场景。

## Risks / Trade-offs

- **[风险] 文档中的命令随代码变化而过期** → 缓解：命令尽量使用稳定的入口（`src.ingress.app:create_app`、环境变量前缀 `SMART_PROVIDER_`），并在变更涉及启动方式时同步更新 quickstart。
- **[风险] 用户没有真实 API key，无法完成 curl 示例** → 缓解：文档中明确说明需要模型 API 访问密钥，并提示用户替换示例中的占位符；同时健康检查端点不依赖密钥即可验证。
- **[权衡] quickstart 的详细程度** → 选择“刚好能跑通首个请求 + 链接到完整配置”。理由：既降低入门门槛，又避免与 `docs/configuration.md` 重复。
