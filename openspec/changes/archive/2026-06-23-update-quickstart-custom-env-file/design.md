## Context

`support-custom-env-files` 已实现并提交：

- `src/config/loader.py` 支持通过 `SMART_PROVIDER_ENV_FILE` 环境变量和 `--env-file` CLI 参数指定自定义 env 文件。
- `docs/configuration.md` 已新增“自定义 env 文件”章节，详细说明用法、优先级和缺失处理。
- `docs/quickstart.md` 当前仍按旧流程编写，仅在第 2 步介绍默认 `.env`。

本次变更属于文档同步，不涉及代码改动。

## Goals / Non-Goals

**Goals:**

- 在 `docs/quickstart.md` 中简要介绍自定义 env 文件用法，不破坏原有 5 分钟上手流程。
- 在 `README.md` 快速开始入口中提示用户可自定义配置文件。
- 同步更新 `openspec/specs/quickstart-guide/spec.md`，使其反映 quickstart 的新内容要求。

**Non-Goals:**

- 不修改配置加载逻辑或测试。
- 不在 quickstart 中完整重复 `docs/configuration.md` 的详细说明。
- 不引入新的部署方式或示例。

## Decisions

### 1. 在 quickstart 中采用“可选小节”形式

**决策**：保留主流程使用 `.env`，在第 2 步之后新增“使用自定义配置文件（可选）”小节，给出两个可运行示例并说明优先级。

**理由**：
- 首次使用者仍可沿 `.env` 路径完成首个请求，不被额外信息干扰。
- 有多环境需求的用户能在同一页直接看到用法，无需跳转。
- “可选”标签明确告知这是进阶用法，不增加入门认知负担。

**替代方案**：将 `.env` 和自定义文件并列为主流程。未采纳原因：会拉长第 2 步，削弱 quickstart 的“快速”属性。

### 2. README 中只加一句提示，不展开

**决策**：在 README 的 4 步快速开始代码块后增加一句简短提示，例如“如需使用其他配置文件名，参见 docs/quickstart.md”。

**理由**：
- README 需要保持紧凑，不宜展开多个示例。
- 感兴趣的用户可以通过链接进入详细 quickstart。

**替代方案**：在 README 中也加入自定义文件示例。未采纳原因：会让 README 快速开始片段过长。

### 3. OpenSpec 规格以新增场景为主

**决策**：在 `quickstart-guide` capability 中新增一个场景，要求文档说明自定义 env 文件用法，而不是修改原有“`.env` 配置”场景。

**理由**：
- 原有场景仍然有效，`.env` 仍是默认推荐方式。
- 新增场景独立表达新能力，规格更清晰。

## Risks / Trade-offs

- **[风险] quickstart 变长导致首次用户阅读成本上升** → 缓解：使用“可选”小节和链接，主流程保持简短。
- **[风险] 自定义文件示例与 configuration.md 不一致** → 缓解：示例直接从 configuration.md 摘录，更新时两处对照检查。
- **[风险] README 提示被忽略** → 缓解：提示放在 4 步示例之后、链接之前，位置自然。
