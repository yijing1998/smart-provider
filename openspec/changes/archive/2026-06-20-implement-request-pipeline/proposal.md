## Why

`src/limiter/` 已实现滑动窗口 RPM 限速器，`src/ingress/` 和 `src/config/` 也已落地，但请求尚未真正走通。当前 `ingress/app.py` 在入队后**直接调用 stub forwarder 返回 `pong`**，Queue 没有真正缓冲，Limiter 没有控制出队，上游也没有被异步调用。只有把这些组件串成一条管线，Smart-Provider 才能兑现“平滑流量、降低 429”的核心价值。

## What Changes

- 新增 `src/processor.py`（或 `src/engine.py`）中的 `RequestProcessor`，作为后台 Worker 协调 Queue、Limiter、Forwarder：
  - 单 Worker 循环：`dequeue -> 等待限速许可 -> 检查等待超时 -> 异步转发 -> 通过 `asyncio.Future` 回传结果。
  - 提供 `start()` / `stop()` 生命周期方法，供 FastAPI lifespan 调用。
- 将 `RequestQueue` 从同步 list 实现迁移为基于 `asyncio.Queue` 的实现，提供 `async dequeue()`。
- 将 `Forwarder.forward()` 改为异步接口 `async def forward_async()`；本次先保留 stub 实现，返回固定响应。
- 修改 `src/ingress/app.py`：
  - 使用 FastAPI `lifespan` 在启动时启动 `RequestProcessor`，在关闭时停止。
  - 端点入队后调用 `processor.submit(context)` 并 `await asyncio.wait_for(..., timeout=context.max_wait_time_ms)`。
  - 队列已满时返回 503；等待超时或上游超时时返回 504。
- 修改 `tests/test_ingress.py` 与 `tests/test_queue.py`（新建或更新），适配异步 Queue 与 Processor。
- 新增 `tests/test_processor.py`，覆盖：Future 结果回传、限速器控制出队、等待超时、启动/停止生命周期。
- 新增 `openspec/specs/request-pipeline/spec.md`，定义管线编排能力。

## Capabilities

### New Capabilities

- `request-pipeline`：定义请求处理管线的编排行为，包括 Worker 循环、限速出队、Future 回传、等待超时与生命周期管理。

### Modified Capabilities

无。本次变更不修改已有产品能力的需求定义，仅实现已有 `request-queue`、`rate-limiting`、`upstream-forwarding`、`response-return` 规格中尚未落地方的部分。

## Impact

- 新增文件：`src/processor.py`（或 `src/engine.py`）、`tests/test_processor.py`、`openspec/specs/request-pipeline/spec.md`。
- 修改文件：`src/queue/queue.py`、`src/forwarder/forwarder.py`、`src/ingress/app.py`、相关测试。
- 无新增外部依赖。
- 当前 stub forwarder 仍返回固定响应；真实上游调用在后续变更中替换。
