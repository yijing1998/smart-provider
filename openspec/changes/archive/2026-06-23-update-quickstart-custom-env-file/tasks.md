## 1. 文档内容更新

- [x] 1.1 更新 `docs/quickstart.md`：在“配置环境变量”后新增“使用自定义配置文件（可选）”小节，包含 `SMART_PROVIDER_ENV_FILE` 与 `--env-file` 示例、优先级说明、链接到 `docs/configuration.md`
- [x] 1.2 更新 `README.md`：在“快速开始”代码块后增加一句提示，指向 `docs/quickstart.md` 中的自定义配置文件说明

## 2. 一致性与格式检查

- [x] 2.1 核对 `docs/quickstart.md` 中的示例与 `docs/configuration.md` 一致
- [x] 2.2 检查 `README.md` 链接路径正确
- [x] 2.3 检查新增文档内容与现有 quickstart 格式风格一致

## 3. 验证与归档

- [x] 3.1 运行 `openspec validate update-quickstart-custom-env-file` 确认变更通过验证
- [x] 3.2 运行 `pytest tests/` 确认文档变更未破坏现有测试
- [x] 3.3 归档变更
