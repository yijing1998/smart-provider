## Why

Smart-Provider 的核心目标是平滑请求流量、降低上游 `429` 触发概率。当前 `src/limiter/` 仅存在 `.gitkeep`，限速能力完全未实现；`src/queue/queue.py` 和 `src/forwarder/forwarder.py` 也只是 stub，无法与真实上游交互。`openspec/specs/rate-limiting/spec.md` 虽已定义滑动窗口 RPM 与可配置性需求，但缺少对限速器对外接口的约定。本次变更将实现一个可独立测试的滑动窗口 RPM 限速器模块，明确其对外接口与并发安全语义，为后续 Worker / 异步转发集成奠定基础。

## What Changes

- 在 `src/limiter/` 下实现 `SlidingWindowRateLimiter`，支持基于滑动时间窗口的 RPM 限制判断。
- 提供异步友好的接口：`async acquire()` 等待并获取放行许可，`is_allowed()` 即时判断当前是否可放行。
- 保证在并发/多 worker 场景下的线程安全与 asyncio 安全。
- 通过 `src.config.Config` 的 `limiter` 组件视图读取 `rate_limit_rpm` 与 `rate_limit_window_seconds`。
- 在 `src/limiter/__init__.py` 中导出公共接口。
- 新增 `tests/test_limiter.py`，覆盖：窗口未超限放行、窗口已满阻塞、窗口滚动后恢复、配置变更生效、并发竞争。
- 修改 `openspec/specs/rate-limiting/spec.md`，补充限速器对外接口与并发安全的要求。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `rate-limiting`：补充限速器对外接口（`acquire`/`is_allowed`）与并发安全要求，使规格不仅描述算法语义，也描述可被 Worker 调用的接口契约。

## Impact

- 受影响代码：`src/limiter/`、`tests/test_limiter.py`。
- 无 API 破坏性变更（新增模块）。
- 当前 `src/ingress/app.py`、`src/queue/`、`src/forwarder/` 不会被修改；限速器模块先独立落地，后续再集成到请求处理管线。
