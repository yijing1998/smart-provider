# quickstart-guide Specification

## Purpose

定义 Smart-Provider 面向使用者的快速入门能力，确保用户能够在本地完成首次部署、配置、启动并验证首个请求。

## Requirements
### Requirement: 提供快速入门文档

Smart-Provider SHALL 提供一份面向使用者的快速入门文档，帮助用户在本地完成首次部署并验证首个请求。

#### Scenario: 使用者按文档完成安装与启动

- **WHEN** 使用者阅读 `docs/quickstart.md`
- **THEN** 文档 SHALL 包含环境准备、依赖安装、`.env` 配置、启动命令的完整步骤

#### Scenario: 使用者发出第一个非流式请求

- **WHEN** 使用者按照 `docs/quickstart.md` 中的非流式示例发起 `POST /v1/chat/completions`
- **THEN** 示例 SHALL 说明如何透传 `Authorization` 请求头，并返回上游响应

#### Scenario: 使用者发出第一个流式请求

- **WHEN** 使用者按照 `docs/quickstart.md` 中的流式示例发起 `stream=true` 请求
- **THEN** 文档 SHALL 说明返回格式为 `text/event-stream`，并给出可运行的 `curl` 示例

#### Scenario: 使用者验证服务健康状态

- **WHEN** 使用者需要确认 Smart-Provider 是否已就绪
- **THEN** 文档 SHALL 说明 `/health` 与 `/ready` 端点的用途，并给出调用示例

#### Scenario: 使用者验证限速生效

- **WHEN** 使用者希望观察 RPM 限速是否生效
- **THEN** 文档 SHALL 提供一个简单的并发请求示例，展示请求被队列控制的现象

#### Scenario: README 提供快速开始入口

- **WHEN** 新用户阅读 `README.md`
- **THEN** `README.md` SHALL 包含“快速开始”小节或链接，指向 `docs/quickstart.md`

### Requirement: 提供可复用的环境变量示例

Smart-Provider SHALL 在项目根目录提供 `.env.example` 文件，作为使用者创建 `.env` 的模板。

#### Scenario: 使用者复制示例配置

- **WHEN** 使用者查看项目根目录的 `.env.example`
- **THEN** 文件 SHALL 包含常用 `SMART_PROVIDER_` 配置项、示例值与字段说明注释

