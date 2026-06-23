# test-tooling Specification

## Purpose

定义 Smart-Provider 测试运行环境的维护要求，确保测试依赖与上游推荐保持一致、测试输出干净可维护。

## Requirements
### Requirement: 测试依赖使用 httpx2 以避免弃用警告

Smart-Provider SHALL 使用 `httpx2` 作为测试 HTTP 客户端依赖，以消除 `starlette.testclient` 对 `httpx` 的弃用警告。

#### Scenario: pytest 输出无 StarletteDeprecationWarning

- **WHEN** 开发者运行 `pytest tests/`
- **THEN** 测试输出 SHALL 不包含 `Using \`httpx\` with \`starlette.testclient\` is deprecated` 警告

#### Scenario: 并发测试仍使用 ASGITransport 与 AsyncClient

- **WHEN** 开发者审查 `tests/test_concurrency.py`
- **THEN** 该文件 SHALL 从 `httpx2` 导入 `ASGITransport` 与 `AsyncClient`，并保持现有测试行为不变

#### Scenario: dev 依赖声明与测试导入一致

- **WHEN** 开发者查看 `pyproject.toml` 的 `[project.optional-dependencies] dev`
- **THEN** 其中 SHALL 包含 `httpx2` 而不是 `httpx`

