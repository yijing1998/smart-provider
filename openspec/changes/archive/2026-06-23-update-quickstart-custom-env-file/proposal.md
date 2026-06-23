## Why

`support-custom-env-files` 已实现通过 `SMART_PROVIDER_ENV_FILE` 和 `--env-file` 自定义 env 配置文件的能力，并在 `docs/configuration.md` 中详细说明。但 `docs/quickstart.md` 作为新用户的首要入口，仍然只介绍默认 `.env` 的使用方式，未体现这一新能力。本次变更同步更新 quickstart 文档与相关入口，确保新用户能快速发现自定义配置文件的用法。

## What Changes

- 更新 `docs/quickstart.md`：
  - 在“配置环境变量”步骤后新增“使用自定义配置文件（可选）”小节。
  - 给出 `SMART_PROVIDER_ENV_FILE` 和 `--env-file` 两种用法的可运行示例。
  - 说明优先级与链接到 `docs/configuration.md`。
- 更新 `README.md`：
  - 在“快速开始”摘要的 4 步示例后增加一句提示，指向 `docs/quickstart.md` 中的自定义配置文件说明。
- 更新 `openspec/specs/quickstart-guide/spec.md`：
  - 新增或修改需求，要求 quickstart 文档包含自定义 env 文件的使用说明。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `quickstart-guide`：扩展快速入门文档的要求，使其包含自定义 env 配置文件（`SMART_PROVIDER_ENV_FILE` 与 `--env-file`）的使用说明，并在 `README.md` 快速开始入口中体现该能力。

## Impact

- 更新文档文件：`docs/quickstart.md`、`README.md`
- 更新规格文件：`openspec/specs/quickstart-guide/spec.md`
- 无代码、API、依赖或部署行为变化。
