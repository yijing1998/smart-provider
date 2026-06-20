## 1. Forwarder 接口重构

- [x] 1.1 在 `src/forwarder/forwarder.py` 中定义 `Forwarder` 抽象基类（`forward_async` 接口）
- [x] 1.2 将现有实现重命名为 `StubForwarder`
- [x] 1.3 更新 `src/forwarder/__init__.py` 导出 `Forwarder`、`StubForwarder`、`LitellmForwarder`、`ForwardResult`

## 2. LitellmForwarder 实现

- [x] 2.1 创建 `LitellmForwarder` 类，接收 `ForwarderConfig`
- [x] 2.2 将 `RequestContext` 映射为 `litellm.acompletion()` 参数（model、messages、api_base、extra_body）
- [x] 2.3 使用 `asyncio.wait_for` 实现单次调用超时
- [x] 2.4 实现重试循环：对 `APIConnectionError`、`RateLimitError`、`ServiceUnavailableError`、`InternalServerError` 进行最多 `max_retries` 次重试
- [x] 2.5 按 `retry_backoff_ms` 实现指数退避
- [x] 2.6 将 litellm 响应转换为 `ForwardResult`
- [x] 2.7 让 litellm 异常自然传播，供 Ingress 异常处理器映射

## 3. Ingress 默认使用真实 Forwarder

- [x] 3.1 修改 `create_app()`：当未注入 forwarder 时，默认使用 `LitellmForwarder(cfg.forwarder)`
- [x] 3.2 保持 `forwarder` 参数可注入，便于测试

## 4. 测试

- [x] 4.1 更新 `tests/test_ingress.py`：对不依赖真实上游的测试注入 `StubForwarder`
- [x] 4.2 新建 `tests/test_forwarder.py`
- [x] 4.3 测试成功响应转换
- [x] 4.4 测试超时抛出 `Timeout`
- [x] 4.5 测试 429 触发重试并最终返回/抛出 `RateLimitError`
- [x] 4.6 测试 500 触发重试并在重试耗尽后抛出错误
- [x] 4.7 测试 400 客户端错误不重试
- [x] 4.8 运行全部测试并通过：`pytest tests/`

## 5. 规格同步与归档

- [ ] 5.1 确认 `openspec/specs/upstream-forwarding/spec.md` 已反映重试与退避要求
- [ ] 5.2 运行 `openspec validate implement-real-upstream-forwarder` 确认变更有效
- [ ] 5.3 归档变更
