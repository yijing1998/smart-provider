# 增加并发场景下的 RPM 限速测试

## Why

Smart-Provider 的核心价值是平滑请求流量、避免触发上游 429，而单 Worker 架构下多个 HTTP 客户端并发请求时，Limiter 与 Queue 的协同行为是保障这一价值的关键。当前测试以模块单元测试为主，缺少真实并发 HTTP 请求下的 RPM 上限验证、队列背压验证和等待超时验证，无法在生产部署前建立足够信心。本 change 通过引入 `pytest-asyncio` 和独立的并发测试文件，系统性地补齐这一缺口。

## What Changes

- 新增开发依赖 `pytest-asyncio`，支持异步测试函数和 async fixtures。
- 新增 `tests/test_concurrency.py`，专门存放并发场景测试，边界清晰、便于维护。
- 新增 `RecordingForwarder` 测试辅助类，精确记录上游调用时间戳，用于验证 RPM 上限。
- 新增以下并发测试：
  - 突发流量下的 RPM 上限：任意滑动窗口内上游调用数不超过配置 RPM。
  - 持续负载下的速率稳定性：长期运行不漂移、不产生窗口边界尖刺。
  - 并发下的队列背压：队列满时新请求立即返回 503，已入队请求继续处理。
  - 并发下的队列等待超时：超过 `max_wait_time_ms` 的请求返回 504。
  - 流式与非流式请求混合并发：两者共享 RPM 配额，互不干扰。
- 新增 `@pytest.mark.slow` 标记，允许通过 `pytest -m "not slow"` 跳过运行时间较长的并发测试。

## Capabilities

### New Capabilities

（无新增产品能力，本 change 仅增加测试覆盖。）

### Modified Capabilities

- `rate-limiting`：补充并发 HTTP 请求场景下的 RPM 上限要求，明确在单 Worker 架构中多个客户端同时请求时，上游实际调用速率仍被滑动窗口限制。
- `request-pipeline`：补充并发提交场景下的排队、限速、超时要求，确保 `submit()` 与 `submit_stream()` 在高并发下行为一致。
- `request-queue`：补充并发入队场景下的 FIFO 与容量上限要求，确保多个请求同时到达时队列状态一致。

## Impact

- **依赖**：`pyproject.toml` 的 `dev` 依赖中增加 `pytest-asyncio`。
- **测试文件**：新增 `tests/test_concurrency.py`；可能需要在 `tests/conftest.py` 中增加 async metrics reset fixture。
- **生产代码**：本 change 不修改生产代码逻辑，仅通过测试暴露潜在问题。
- **CI / 本地开发**：新增 slow 标记的测试运行时间可能增加数十秒，建议 CI 全量运行、本地开发可跳过 slow 测试。
