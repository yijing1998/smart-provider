# 流式响应支持设计文档

## Context

Smart-Provider 当前仅支持非流式请求。`Ingress` 在解析到 `stream=true` 时直接返回 503，拒绝服务。为了支持更多真实客户端，需要引入 OpenAI 兼容的 SSE 流式响应路径。

本设计选择**方案 A**：流式请求与非流式请求共享同一个请求队列和单一 Worker。Worker 根据请求类型选择非流式的 `forward_async()` 或流式的 `stream_async()`。流式 chunk 通过 `StreamHandle` 异步通道从 Worker 传回 Ingress，Ingress 再将其包装为 SSE 返回给客户端。

## Goals / Non-Goals

**Goals：**

- 支持 `POST /v1/chat/completions` 的 `stream=true` 请求，返回 OpenAI 兼容的 SSE 流。
- 流式请求同样受 RPM 限速器和熔断器保护。
- 保持现有非流式路径行为完全不变。
- 客户端断开连接时，上游流式调用应尽快停止，避免资源泄漏。

**Non-Goals：**

- 多 Worker 并发处理流式请求（项目已明确单 Worker）。
- 按 chunk 数限速（首期按请求数消耗 RPM）。
- 支持非 OpenAI 协议格式的流式输出。
- 改变非流式请求的 Future 结果传递模式。

## Decisions

### 1. 流式请求走完整管线，使用 StreamHandle 作为异步通道

- **选择**：流式请求调用 `Processor.submit_stream()` 入队，Worker 出队后经过 breaker 和 limiter，再调用 `Forwarder.stream_async()`。chunk 通过 `StreamHandle` 传回 Ingress。
- **理由**：
  - 与现有架构统一，流式请求也能复用队列、限速、熔断。
  - `StreamHandle` 用 `asyncio.Queue` 解耦 Worker 生产 chunk 与 Ingress 消费 chunk。
- **已知代价**：单 Worker 处理长 stream 时会阻塞队列中其他请求。已确认接受该代价。

### 2. `submit()` 与 `submit_stream()` 分离

- **选择**：非流式继续使用 `submit()` 返回 `Future<ForwardResult>`；流式使用 `submit_stream()` 返回 `StreamHandle`。
- **理由**：
  - 两种结果类型语义差异大，分离接口更直观。
  - 避免返回联合类型或包装对象增加调用方复杂度。
- **替代方案**：统一返回 `ResultHandle`。放弃原因：需要调用方再判断类型，不够直接。

### 3. StreamHandle 错误与关闭语义

- **选择**：
  - `put_chunk(chunk)`：写入一个 SSE data 帧。
  - `put_error(exc)`：写入一个异常对象，消费端会抛出该异常。
  - `close()`：写入 `None` 哨兵，消费端正常结束。
  - `cancel()`：设置取消事件，Worker 停止写入并关闭。
- **理由**：
  - 明确区分正常结束、错误结束和取消三种场景。
  - SSE generator 在捕获异常后可发送 `event: error` 帧再发 `[DONE]`。

### 4. SSE 错误格式

- **选择**：流式过程中出错时发送：

```http
event: error
data: {"error": {"message": "...", "type": "..."}}

data: [DONE]
```

- **理由**：
  - stream 已经开始后，HTTP 状态码固定为 200，需要用 SSE event 表达错误。
  - payload 结构与 OpenAI 错误对象一致，便于客户端复用错误处理逻辑。

### 5. chunk 转换策略

- **选择**：直接透传 litellm stream chunk 的 `model_dump(mode="json")` 结果。
- **理由**：
  - litellm 返回的 chunk 已是 OpenAI 兼容格式。
  - 代理层不应修改上游响应结构，避免未来字段扩展时被截断。
  - 与非流式路径的 `_response_to_dict()` 逻辑保持一致。

### 6. 取消传播策略

- **选择**：Ingress 在客户端断开时调用 `StreamHandle.cancel()`；Worker 每次写入 chunk 前检查 `is_cancelled`，若已取消则立即 break 并 `close()`。
- **理由**：
  - 尽快停止上游调用，减少无效网络和计算资源消耗。
  - `close()` 确保 Ingress 端的 SSE generator 不会因等待而挂起。

### 7. 指标设计

- **选择**：新增 `streams_started_total`（`submit_stream()` 入队时）和 `streams_completed_total`（`StreamHandle.close()` 正常结束时）。
- **理由**：
  - 不破坏现有 `requests_processed_total` 的语义（它代表出队开始处理）。
  - 通过 `started - completed` 可推算进行中和失败数量。

### 8. StreamHandle 放置位置

- **选择**：`StreamHandle` 放在 `src/ingress/context.py` 同目录或单独 `src/streaming/stream_handle.py`。
- **理由**：
  - 它与 `RequestContext` 紧密相关，但又是独立的流式原语。
  - 为保持简单，首期放在 `src/ingress/stream_handle.py` 或并入 `src/ingress/context.py`。
  - 本设计倾向于新建 `src/ingress/stream_handle.py`，避免 context.py 过度膨胀。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| 单 Worker 被长 stream 阻塞，其他请求等待 | 已明确接受；后续如需缓解可考虑多 Worker 或 stream 独立路径 |
| 客户端断开后上游 generator 继续运行 | `StreamHandle.cancel()` + Worker 检查取消状态 |
| `asyncio.Queue` 在快速生产/消费时产生背压 | 默认无界队列，单进程场景下通常不构成问题 |
| SSE 错误格式不被某些客户端识别 | 使用通用 `event: error` 格式，并在文档中说明 |
| litellm stream chunk 结构变化 | 透传 model_dump，不硬编码字段 |
| Metrics 单例在测试中的 reset | 沿用现有 `reset_metrics` fixture 模式 |

## Migration Plan

1. **部署**：新代码默认不影响非流式请求；`stream=true` 开始返回 SSE 而非 503。
2. **回滚**：回退到上一版本，流式请求重新返回 503，非流式请求行为不变。

## Open Questions

1. 是否需要为流式请求单独配置 `stream_timeout_ms`？当前复用 `forwarder_timeout_ms`。
2. 是否需要限制单个 stream 的最大 chunk 数或时长？首期不做限制。
3. `StreamHandle` 是否需要支持背压控制（bounded queue）？首期使用无界队列。
