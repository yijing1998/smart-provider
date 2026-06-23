## 1. 依赖与代码调整

- [x] 1.1 更新 `pyproject.toml`：将 dev 可选依赖中的 `httpx>=0.24.0` 替换为 `httpx2>=2.0.0`
- [x] 1.2 更新 `tests/test_concurrency.py`：将 `from httpx import ASGITransport, AsyncClient` 改为 `from httpx2 import ASGITransport, AsyncClient`

## 2. 环境更新与验证

- [x] 2.1 在当前虚拟环境中重新安装 dev 依赖：`.venv/bin/python -m pip install -e ".[dev]"`
- [x] 2.2 运行 `pytest tests/`，确认弃用警告消失且所有测试通过
- [x] 2.3 检查 `tests/` 中是否还有其他直接使用 `httpx` 的导入

## 3. OpenSpec 归档

- [x] 3.1 运行 `openspec validate fix-testclient-httpx2-warning` 确认变更通过验证
- [x] 3.2 归档变更
