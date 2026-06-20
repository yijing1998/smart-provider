# 流式响应支持实现任务清单

## 1. StreamHandle 与上下文扩展

- [x] 1.1 创建 `src/ingress/stream_handle.py`，实现 `StreamHandle` 类
- [x] 1.2 实现 `put_chunk()`、`put_error()`、`close()`、`cancel()`、`is_cancelled` 和 `__aiter__`
- [x] 1.3 扩展 `RequestContext`，新增 `stream_handle: StreamHandle | None` 字段
- [x] 1.4 验证 `StreamHandle` 单元测试覆盖正常流、错误流、取消场景

## 2. Forwarder 流式接口

- [x] 2.1 扩展 `Forwarder` 抽象基类，新增 `stream_async()` 方法
- [x] 2.2 在 `LitellmForwarder` 中实现 `stream_async()`，调用 `litellm.acompletion(..., stream=True)`
- [x] 2.3 实现 chunk 到 dict 的转换（复用/扩展 `_response_to_dict` 逻辑）
- [x] 2.4 新增 `StubForwarder.stream_async()`，用于测试返回合成 chunk

## 3. Processor 流式支持

- [x] 3.1 新增 `RequestProcessor.submit_stream()`，创建 `StreamHandle` 并入队
- [x] 3.2 在 `MetricsCollector` 中记录 `streams_started_total`
- [x] 3.3 修改 `Worker._run()`，根据 `context.stream` 区分流式与非流式路径
- [x] 3.4 流式路径：经过 breaker 和 limiter，调用 `stream_async()`，逐 chunk 写入 `StreamHandle`
- [x] 3.5 流式路径：写入 chunk 前检查 `is_cancelled`，取消时立即 break 并 close
- [x] 3.6 流式路径：上游结束时调用 `StreamHandle.close()`，失败时调用 `put_error()`
- [x] 3.7 流式路径：根据结果更新 breaker 和 `streams_completed_total`

## 4. Ingress SSE 输出

- [x] 4.1 修改 `src/ingress/app.py` 的 `chat_completions`，根据 `completion_request.stream` 选择路径
- [x] 4.2 非 stream 路径保持现有 Future 逻辑不变
- [x] 4.3 stream 路径：调用 `submit_stream()`，构造 `StreamingResponse`
- [x] 4.4 实现 `_sse_generator()`，将 chunk 序列化为 `data: {...}\n\n`，最后发送 `data: [DONE]`
- [x] 4.5 实现 SSE 错误帧：`event: error\ndata: {...}\n\n`，最后发送 `data: [DONE]`
- [x] 4.6 客户端断开时调用 `StreamHandle.cancel()`

## 5. 可观测性扩展

- [x] 5.1 扩展 `MetricsCollector`，新增 `streams_started_total` 和 `streams_completed_total`
- [x] 5.2 在 `snapshot()` 中返回新增指标
- [x] 5.3 在 `reset()` 中清零新增指标
- [x] 5.4 验证 `/metrics` 端点返回新增指标

## 6. 测试

- [x] 6.1 创建 `tests/test_stream_handle.py`，覆盖正常流、错误传播、取消
- [x] 6.2 在 `tests/test_forwarder.py` 中补充 `stream_async()` 测试（mock litellm）
- [x] 6.3 在 `tests/test_processor.py` 中补充流式请求集成测试
- [x] 6.4 在 `tests/test_ingress.py` 中补充 SSE 端到端测试，验证 chunk 格式和 `[DONE]`
- [x] 6.5 在 `tests/test_observability.py` 中补充流式指标测试
- [x] 6.6 运行完整测试套件 `pytest tests/`，确保全部通过

## 7. 文档

- [x] 7.1 更新 `docs/configuration.md`，说明流式响应已支持
- [x] 7.2 在 `README.md` 路线图中标注 streaming 支持已完成
- [x] 7.3 检查所有代码注释与 docstring 清晰准确
