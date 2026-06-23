## Context

当前测试运行结束时输出一条警告：

```
.venv/lib/python3.10/site-packages/fastapi/testclient.py:1
  StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

环境信息：

- `fastapi==0.137.2`
- `starlette==1.3.1`
- `httpx==0.28.1`

`starlette.testclient` 在导入时优先尝试 `import httpx2 as httpx`，若未安装则回退到 `httpx` 并发出上述弃用警告。`fastapi.testclient` 进一步复用了 `starlette.testclient`，导致项目测试触发该警告。

## Goals / Non-Goals

**Goals:**

- 消除 pytest 输出中的 `StarletteDeprecationWarning`。
- 使测试依赖与 starlette 推荐保持一致（使用 `httpx2`）。
- 保持现有测试行为不变。

**Non-Goals:**

- 不修改运行时依赖或生产代码。
- 不引入新的测试框架或重写测试逻辑。
- 不强制移除 `httpx`（它仍是多个运行时依赖的传递依赖）。

## Decisions

### 1. 将 dev 依赖从 `httpx` 替换为 `httpx2`

**决策**：在 `pyproject.toml` 的 `[project.optional-dependencies] dev` 中，将 `httpx>=0.24.0` 替换为 `httpx2>=2.0.0`。

**理由**：
- 这是 `starlette.testclient` 官方推荐的修复方式，警告信息本身已明确说明。
- `httpx2` 是 starlette 团队维护的 `httpx` 兼容分支，API 与 `httpx` 一致，迁移成本低。
- 仅修改 dev 依赖，不影响生产环境。

**替代方案**：
- 在 `pyproject.toml` 中同时保留 `httpx` 并新增 `httpx2`。未采纳原因：我们的测试代码可直接使用 `httpx2`，同时保留两者会造成依赖冗余。
- 使用 `pytest.filterwarnings` 忽略该警告。未采纳原因：只是掩盖问题，不符合“测试输出应干净”的目标。

### 2. 同步更新 `tests/test_concurrency.py` 的导入

**决策**：将 `from httpx import ASGITransport, AsyncClient` 改为 `from httpx2 import ASGITransport, AsyncClient`。

**理由**：
- `httpx2` 已验证导出 `ASGITransport` 和 `AsyncClient`，与现有用法兼容。
- 保持测试代码与 dev 依赖一致，避免混合使用两个库。

**替代方案**：保持 `from httpx import ...` 不变。未采纳原因：既然 dev 依赖已切换为 `httpx2`，测试代码应使用同一库，减少维护困惑。

## Risks / Trade-offs

- **[风险] `httpx2` 未来与 `httpx` 出现 API 分叉** → 缓解：`httpx2` 当前是 `httpx` 的兼容 fork，且仅用于测试；若未来不兼容，可再评估是否回退或调整。
- **[风险] 开发者本地环境未重新安装依赖导致警告仍在** → 缓解：在 commit/PR 中提示运行 `.venv/bin/python -m pip install -e ".[dev]"` 更新依赖。
- **[风险] CI 环境缓存了旧依赖** → 缓解：依赖变更会触发 CI 重新解析安装；如仍缓存，可手动清除缓存。
