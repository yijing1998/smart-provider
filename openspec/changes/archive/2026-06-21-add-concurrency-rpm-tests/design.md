# 并发 RPM 限速测试设计

## Context

Smart-Provider 当前有 125 个测试，覆盖了模块单元行为和部分 HTTP 端点集成。但缺少在**真实并发 HTTP 请求**下验证 RPM 限速有效性的测试。现有 `test_limiter.py` 中的 `test_concurrent_acquires_respect_rpm` 只验证了 Limiter 本身，没有验证 Queue + Pipeline + Ingress 整条链路在并发下的行为。

本 change 的目标是建立一组可重复、可观测的并发测试，证明：当多个 HTTP 客户端同时请求时，上游实际接收速率仍被限制在配置 RPM 内。

## Goals / Non-Goals

**Goals:**

- 引入 `pytest-asyncio`，支持异步测试函数和 async fixtures。
- 新增独立的 `tests/test_concurrency.py`，集中管理并发测试。
- 提供 `RecordingForwarder` 辅助类，精确记录上游调用时间戳。
- 覆盖突发流量、持续负载、队列背压、队列超时、流式/非流式混合 5 个核心场景。
- 使用 `@pytest.mark.slow` 标记运行时间较长的测试。

**Non-Goals:**

- 不修改生产代码逻辑。
- 不引入真实上游服务或 Docker 依赖。
- 不做分布式或多实例测试。
- 不做压力测试或长时间 soak test（总运行时间控制在 30 秒内）。

## Decisions

### Decision 1：使用 `pytest-asyncio`

**选择**：引入 `pytest-asyncio` 作为 dev 依赖，用 `@pytest.mark.asyncio` 标记异步测试。

**理由**：

- 当前测试通过 `asyncio.run()` 手动包装，写并发测试非常啰嗦。
- `pytest-asyncio` 原生支持 `async def test_*` 和 async fixtures。
- 与现有 `asyncio.run` 测试可以共存，不强制重构旧测试。

**替代方案**：保持现有风格，手动 `asyncio.run(asyncio.gather(...))`。被否决，因为可读性和 fixture 支持差。

### Decision 2：独立测试文件 `tests/test_concurrency.py`

**选择**：把并发测试单独放在一个文件中，而不是分散到 `test_ingress.py` 和 `test_processor.py`。

**理由**：

- 并发测试有共同的辅助类（`RecordingForwarder`）和 fixture 模式，集中管理更清晰。
- 避免把运行时间较长的 slow 测试混入现有快速测试文件。
- 未来扩展并发测试时边界清晰。

### Decision 3：用 `RecordingForwarder` 记录上游调用时间戳

**选择**：测试中用自定义 Forwarder 记录每次上游调用发生的精确时间。

**理由**：

- 验证 RPM 上限最直接的方式是统计上游调用，而不是看响应时间。
- 响应时间受序列化、网络栈、FastAPI 内部调度影响，不够精确。
- `RecordingForwarder` 可以在 `forward_async` 和 `stream_async` 中统一记录。

### Decision 4：窗口大小使用 1 秒

**选择**：并发测试使用 `window_seconds=1`，而不是生产默认的 60 秒。

**理由**：

- 1 秒窗口足以验证滑动窗口算法的正确性。
- 运行时间可控，整套并发测试能在 10-30 秒内完成。
- 配合 `rpm=5` 或 `rpm=10`，既能观察限速效果，又不会让测试等待太久。

**风险**：1 秒窗口下 asyncio 调度粒度可能影响测试稳定性，需要通过 tolerance 缓解。

### Decision 5：使用 `httpx.AsyncClient` 做并发 HTTP 请求

**选择**：通过 `httpx.AsyncClient(app=app)` 发起真正的并发 ASGI 请求。

**理由**：

- `fastapi.TestClient` 是同步的，无法模拟多个客户端同时连接。
- `httpx.AsyncClient` 支持 `asyncio.gather()` 同时发起多个请求。
- 虽然仍在单进程内，但能触发 FastAPI 的并发请求处理路径。

## Risks / Trade-offs

- **风险**：时间相关测试在 CI 环境中可能因 CPU 调度抖动而偶发失败。
  - **缓解**：使用 tolerance（如 ±50ms），并标记为 slow 测试，CI 失败时可重试。
- **风险**：`pytest-asyncio` 与现有 `asyncio.run` 测试可能在 event loop 管理上产生冲突。
  - **缓解**：使用 `asyncio_mode = "auto"` 配置，让 `pytest-asyncio` 自动处理；保留旧测试不变。
- **风险**：并发测试运行时间增加，拖慢本地开发反馈。
  - **缓解**：标记 `@pytest.mark.slow`，本地默认跳过，CI 全量运行。
- **风险**：`MetricsCollector` 单例在并发测试后状态未清理，污染后续测试。
  - **缓解**：在 `conftest.py` 中提供 async 的 `reset_metrics` fixture，每个测试前清理。

## Migration Plan

1. 安装 `pytest-asyncio` 到 `.venv`。
2. 新增 `tests/test_concurrency.py`。
3. 运行全套测试，确保现有 125 个测试不受影响。
4. 在 CI 中默认运行全部测试（包括 slow）；本地开发可通过 `pytest -m "not slow"` 跳过。

## Open Questions

1. 是否需要把现有 `test_limiter.py::test_concurrent_acquires_respect_rpm` 重构为 `pytest-asyncio` 风格？（本 change 先不动，保持最小改动。）
2. slow 测试的 tolerance 是否需要根据 CI 环境动态调整？（先固定 50ms，后续根据实际失败率调整。）
3. 是否需要为并发测试单独配置更小的 `queue_max_wait_ms` 以加速超时场景？（是，测试中显式注入小值。）
