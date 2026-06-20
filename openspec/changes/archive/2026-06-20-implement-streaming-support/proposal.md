# 实现流式响应支持（Streaming Support）

## Why

Smart-Provider 当前会明确拒绝 `stream=true` 的请求并返回 503。然而，许多调用模型 API 的客户端默认使用流式响应以降低首 token 延迟，拒绝 streaming 会显著限制 Smart-Provider 的可用性。本变更在保持现有非流式管线不变的前提下，新增流式响应支持，使 Smart-Provider 能够代理 OpenAI 兼容的 SSE 流式输出。

## What Changes

- 新增 `StreamHandle` 抽象，作为 Worker 与 Ingress 之间的异步流式通道；它内部使用 `asyncio.Queue`，支持 chunk 写入、错误传播、关闭标记和取消传播。
- 扩展 `RequestContext`，增加 `stream_handle` 字段，使流式请求能够把通道随请求一起传递。
- 扩展 `Forwarder` 接口，新增 `stream_async()` 方法，返回上游 chunk 的异步迭代器。
- 在 `LitellmForwarder` 中通过 `litellm.acompletion(..., stream=True)` 实现 `stream_async()`。
- 扩展 `RequestProcessor`：
  - 新增 `submit_stream()`，返回 `StreamHandle`；
  - Worker 循环区分流式与非流式请求；
  - 流式请求同样经过熔断器和 RPM 限速器；
  - Worker 在客户端取消时停止向 `StreamHandle` 写入 chunk 并关闭通道。
- 扩展 Ingress：
  - 当 `stream=true` 时调用 `submit_stream()`；
  - 使用 `StreamingResponse` 以 SSE 格式返回流式结果；
  - 客户端断开时调用 `StreamHandle.cancel()`。
- 扩展 `MetricsCollector`，新增 `streams_started_total` 与 `streams_completed_total` 指标。
- 更新配置文档与 README 路线图。

## Capabilities

### New Capabilities

- `streaming-support`：定义 Smart-Provider 如何接收、排队、转发和返回 OpenAI 兼容的流式聊天补全响应。

### Modified Capabilities

- `request-ingress`：新增要求——Ingress SHALL 接收 `stream=true` 的聊天补全请求，并以 SSE 格式返回流式响应；不再返回 503。
- `request-pipeline`：新增要求——Processor SHALL 提供 `submit_stream()` 接口，使流式请求能够入队并在 Worker 中通过流式通道返回 chunk。
- `upstream-forwarding`：新增要求——Forwarder SHALL 提供 `stream_async()` 接口，以异步迭代器方式返回上游流式响应 chunk。
- `observability`：新增要求——指标端点 SHALL 暴露流式请求的开始次数与完成次数。

## Impact

- **新增代码**：`src/streaming/stream_handle.py` 或并入 `src/ingress/context.py`；`LitellmForwarder.stream_async()`。
- **修改代码**：
  - `src/ingress/context.py`：扩展 `RequestContext`；
  - `src/forwarder/forwarder.py`：扩展 `Forwarder` 接口并实现流式转发；
  - `src/processor.py`：新增 `submit_stream()` 与 Worker 流式分支；
  - `src/ingress/app.py`：处理 `stream=true` 并返回 `StreamingResponse`；
  - `src/observability/metrics.py`：新增流式指标。
- **新增测试**：
  - `StreamHandle` 单元测试；
  - `LitellmForwarder.stream_async()` 测试；
  - Processor 流式集成测试；
  - Ingress SSE 端到端测试。
- **文档更新**：`docs/configuration.md`、`README.md`。
- **非破坏性变更**：默认行为不变，仅当客户端显式发送 `stream=true` 时启用流式路径。
