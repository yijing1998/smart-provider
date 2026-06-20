## 1. 文档内容准备

- [x] 1.1 编写 `docs/configuration.md`：配置加载优先级、环境变量清单、`.env` 示例、校验说明、启动命令
- [x] 1.2 编写 `docs/config-module.md`：模块职责、组件视图、新增字段流程、reserved 字段约定
- [x] 1.3 更新 `README.md`：新增“配置”入口小节，包含最小示例并链接到 `docs/configuration.md` 与 `docs/config-module.md`

## 2. 一致性与格式检查

- [x] 2.1 核对 `docs/configuration.md` 中的默认值、校验规则与 `src/config/schema.py` 一致
- [x] 2.2 检查新增文档与 `docs/ingress.md` 的格式风格一致
- [x] 2.3 检查 `README.md` 中的链接路径正确

## 3. 验证与归档

- [x] 3.1 运行 `openspec validate add-config-docs` 确认变更通过验证
- [x] 3.2 运行 `pytest tests/` 确认文档变更未破坏现有测试
- [ ] 3.3 归档变更
