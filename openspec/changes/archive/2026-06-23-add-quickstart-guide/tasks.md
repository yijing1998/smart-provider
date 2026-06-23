## 1. 文档内容准备

- [x] 1.1 编写 `docs/quickstart.md`：前置条件、安装、配置、启动、非流式/流式 curl 示例、健康检查、限速验证、链接到完整配置文档
- [x] 1.2 编写 `.env.example`：常用配置项示例值与注释
- [x] 1.3 更新 `README.md`：新增“快速开始”入口链接，指向 `docs/quickstart.md`

## 2. 一致性与格式检查

- [x] 2.1 核对 `docs/quickstart.md` 中的默认值、端点路径与当前代码（`src/config/schema.py`、`src/ingress/app.py`）一致
- [x] 2.2 核对 `.env.example` 中的字段与默认值与 `docs/configuration.md` 一致
- [x] 2.3 检查新增文档与 `docs/configuration.md`、`docs/ingress.md` 的格式风格一致
- [x] 2.4 检查 `README.md` 与 `docs/quickstart.md` 中的链接路径正确

## 3. 验证与归档

- [x] 3.1 运行 `openspec validate add-quickstart-guide` 确认变更通过验证
- [x] 3.2 运行 `pytest tests/` 确认文档变更未破坏现有测试
- [x] 3.3 归档变更
