## Why

当前 Smart-Provider 只支持工作目录下的 `.env` 文件作为配置文件来源。在实际部署和 CI/CD 场景中，用户常常需要按环境使用不同名称的配置文件（如 `prod.env`、`smart-provider.env`），或通过 CLI 显式指定配置文件路径。本次变更让配置加载支持自定义 env 文件名，提升部署灵活性。

## What Changes

- 修改 `src/config/loader.py`：
  - 支持通过环境变量 `SMART_PROVIDER_ENV_FILE` 指定配置文件路径（替代默认 `.env`）。
  - 支持通过 CLI 参数 `--env-file <path>` 指定配置文件路径（替代默认 `.env`）。
  - 优先级：`--env-file` > `SMART_PROVIDER_ENV_FILE` > 默认 `.env`。
  - 当显式指定的配置文件不存在时，启动阶段报错并退出（fail-fast）。
- 保持 `.env` 作为默认行为，未指定自定义文件时完全向后兼容。
- 更新 `tests/test_config.py`：新增自定义 env 文件加载、优先级、缺失文件报错等测试。
- 更新 `docs/configuration.md`：说明自定义 env 文件的用法、优先级与缺失行为。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `configuration`：扩展配置加载能力，除 `.env` 外，支持通过 `SMART_PROVIDER_ENV_FILE` 环境变量和 `--env-file` CLI 参数指定其他 env 文件名，并明确优先级与缺失处理规则。

## Impact

- 修改代码：`src/config/loader.py`
- 新增测试：`tests/test_config.py`
- 更新文档：`docs/configuration.md`
- 无 API、依赖或部署行为变化；默认 `.env` 行为保持不变。
