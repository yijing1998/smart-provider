## 1. 核心实现

- [x] 1.1 修改 `src/config/loader.py`：实现 `_resolve_env_file()`，按优先级解析 `--env-file`、`SMART_PROVIDER_ENV_FILE`、默认 `.env`
- [x] 1.2 修改 `src/config/loader.py`：在 `load_config()` 中将解析结果通过 `Config(_env_file=...)` 传入
- [x] 1.3 实现显式指定文件不存在的启动报错逻辑

## 2. 测试

- [x] 2.1 新增测试：默认 `.env` 加载行为保持不变
- [x] 2.2 新增测试：`SMART_PROVIDER_ENV_FILE` 加载指定文件并替代 `.env`
- [x] 2.3 新增测试：`--env-file` 加载指定文件并替代 `.env` 与 `SMART_PROVIDER_ENV_FILE`
- [x] 2.4 新增测试：显式指定文件不存在时启动报错
- [x] 2.5 新增测试：`.env` 不存在且未指定自定义文件时不报错并使用默认值
- [x] 2.6 运行完整测试套件 `pytest tests/`，确认无破坏

## 3. 文档

- [x] 3.1 更新 `docs/configuration.md`：说明自定义 env 文件用法、优先级、缺失行为
- [x] 3.2 核对文档中的示例命令与实现一致

## 4. 验证与归档

- [x] 4.1 运行 `openspec validate support-custom-env-files` 确认变更通过验证
- [x] 4.2 归档变更
