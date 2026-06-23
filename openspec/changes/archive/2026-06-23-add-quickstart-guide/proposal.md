## Why

Smart-Provider 的现有文档（`README.md`、`docs/configuration.md`、`docs/ingress.md`）对架构和配置讲得足够全，但缺少一份让新使用者在 5 分钟内完成“安装 → 配置 → 启动 → 发出第一个请求”的入门指南。本次变更补齐这一缺口，降低首次使用门槛。

## What Changes

- 在 `docs/` 目录下新建 `quickstart.md`，面向运维与使用者：
  - 列出前置条件（Python 3.10+、模型 API 访问密钥）。
  - 给出安装依赖、创建 `.env`、启动服务的完整命令。
  - 提供非流式与流式请求的 `curl` 示例，并说明 `Authorization` 透传行为。
  - 说明 `/health` 与 `/ready` 健康检查端点的用途与调用方式。
  - 给出验证限速生效的简单方法（快速并发请求观察队列行为）。
  - 链接到 `docs/configuration.md` 供读者查看完整配置项。
- 在项目根目录新增 `.env.example`，包含常用配置项的示例值与注释。
- 在 `README.md` 中新增“快速开始”入口链接，指向 `docs/quickstart.md`。

## Capabilities

### New Capabilities

- `quickstart-guide`：提供一份面向使用者的快速入门文档，帮助用户在本地完成 Smart-Provider 的首次部署与首个请求验证。

### Modified Capabilities

无。本次变更不修改现有产品能力的需求定义。

## Impact

- 新增文档文件：`docs/quickstart.md`。
- 新增示例文件：`.env.example`。
- 更新文档文件：`README.md`（新增快速开始入口链接）。
- 无代码、API、依赖或部署行为变化。
