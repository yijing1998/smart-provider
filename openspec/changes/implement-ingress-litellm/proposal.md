## Why

Smart-Provider 的架构设计与编码实现指导文档已明确了请求接入层（Ingress）的职责：接收客户端请求、构造内部请求上下文、将上下文入队、并将上游响应返回给客户端。当前项目已创建 `src/ingress/` 目录，但尚未实现具体代码。为了尽快验证核心流程并避免重复造轮子，本次变更将基于 litellm 提供的 SDK 实现 Ingress 模块，重点复用 litellm 的请求模型解析、模型信息校验、异常分类与日志回调能力，而不是从零实现 OpenAI 兼容协议栈。

## What Changes

- 在 `src/ingress/` 中实现 Ingress 模块，使用 Python 编写。
- 使用 litellm SDK 提供的类型、工具函数与回调机制辅助实现，不重复实现 litellm 已提供的功能。
- 暴露 OpenAI 兼容的 chat/completions 端点，接收客户端请求。
- 将客户端请求解析并封装为项目内部请求上下文对象。
- 将内部上下文提交给请求队列，若队列已满则返回明确错误。
- 等待转发结果并将响应返回给客户端。
- 新增针对 Ingress-litellm 实现的 spec 文件，定义该模块的行为要求。
- 本变更聚焦 Ingress 实现，不实现队列、限速器、转发器等其它模块。

## Capabilities

### New Capabilities

- `ingress-litellm`：使用 litellm SDK 实现 Smart-Provider 的请求接入层，包括端点暴露、请求解析、上下文构造、队列入队与响应返回。

### Modified Capabilities

- 无现有 spec 需要修改（现有 `request-ingress` 主规格已定义高层需求，本次变更通过新增 `ingress-litellm` 实现规格来落地）。

## Impact

- 新增 `src/ingress/` 下的 Python 实现文件与必要依赖声明（如 `pyproject.toml` 或 `requirements.txt`）。
- 引入 litellm 作为依赖，用于请求解析、模型校验、异常与日志。
- 为后续队列、限速器、转发器模块提供可集成的 Ingress 入口。
