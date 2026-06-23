## Why

运行测试时，pytest 持续输出以下 `StarletteDeprecationWarning`：

```
Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

该警告源于 `fastapi.testclient` → `starlette.testclient` 的导入链。虽然不影响测试结果，但会污染输出、掩盖其他潜在警告，并提示依赖关系需要调整。本次变更通过将测试依赖从 `httpx` 迁移到 `httpx2` 来消除该警告。

## What Changes

- 更新 `pyproject.toml`：
  - 将 `dev` 可选依赖中的 `httpx>=0.24.0` 替换为 `httpx2>=2.0.0`。
- 更新 `tests/test_concurrency.py`：
  - 将 `from httpx import ASGITransport, AsyncClient` 改为 `from httpx2 import ASGITransport, AsyncClient`。
- 更新开发者环境说明（如需要）：提示重新安装 dev 依赖。

## Capabilities

### New Capabilities

- `test-tooling`：维护测试运行环境健康，确保测试输出干净、依赖符合上游推荐。

### Modified Capabilities

无。

## Impact

- 修改构建/开发依赖：`pyproject.toml`
- 修改测试代码：`tests/test_concurrency.py`
- 无运行时代码、API 或部署行为变化。
- `httpx` 仍会通过 `litellm`、`openai`、`huggingface_hub` 等运行时依赖作为传递依赖安装，不影响生产行为。
