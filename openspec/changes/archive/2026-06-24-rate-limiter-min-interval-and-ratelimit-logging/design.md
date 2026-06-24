## Context

当前 `SlidingWindowRateLimiter` 位于 `src/limiter/rate_limiter.py`，仅维护一个基于时间窗口的 RPM 计数器。该实现允许在窗口起始阶段一次性放行最多 `rpm` 个请求，无法约束相邻请求的间隔，因而可能在窗口内形成突发流量。

上游（如 OpenAI、Anthropic、Azure）的限流策略通常同时包含 RPM、TPM 与突发/并发维度。当上游返回 429 时，`LitellmForwarder` 仅记录错误类型和状态码，不保留 `x-ratelimit-*` 等响应头，导致运维人员无法判断本次 429 是 RPM 耗尽、TPM 耗尽还是其他原因。

本次变更在现有 RPM 滑动窗口基础上增加全局最小请求间隔，并在 429 日志中原样输出限流响应头。

## Goals / Non-Goals

**Goals:**
- 平滑请求突发：通过全局最小间隔限制相邻两次放行的时间差。
- 提供可观测信息：在 429 日志中打印上游限流响应头，辅助定位限流原因。
- 保持向后兼容：新增配置默认不启用，不影响现有行为。

**Non-Goals:**
- 不替换现有滑动窗口算法为令牌桶。
- 不根据 `x-ratelimit-*` 或 `retry-after` 动态调整重试退避时间。
- 不为不同 model 或 client 维护独立的间隔窗口。
- 不消费 `rate_limit_tpm` 字段实现 TPM 限速。

## Decisions

### Decision 1：在 `SlidingWindowRateLimiter` 内增加 `min_interval_ms`

在现有 `acquire()` 流程中，放行前额外检查距离上一次放行的时间。若不足 `min_interval_ms` 则异步等待，等待期间释放锁，避免阻塞其他协程。

**替代方案：** 在 processor 层控制间隔。
**未选原因：** 限流语义应集中在 limiter 内，processor 不应关心具体限速算法。

### Decision 2：最小间隔作为 `LimiterConfig` 的可选字段

```python
class LimiterConfig(BaseModel):
    rpm: int = Field(ge=1)
    tpm: Optional[int] = Field(default=None, ge=1)
    window_seconds: int = Field(ge=1)
    min_interval_ms: Optional[int] = Field(default=None, ge=0)
```

默认 `None` 表示不启用，确保向后兼容。

### Decision 3：最小间隔为全局单间隔

当前 `SlidingWindowRateLimiter` 已是全局单实例，最小间隔沿用同一实例，不区分 model 或 client。

**替代方案：** 按 model 分桶维护多个 limiter。
**未选原因：** 当前架构下全局 limiter 足以满足多数场景，分桶会显著增加状态复杂度。

### Decision 4：429 响应头原样打印，不做结构化解析

在 `LitellmForwarder._record_upstream_error` 中提取 `exc.response.headers` 中所有键名包含 `ratelimit` 或等于 `retry-after`（大小写不敏感）的字段，以原始键值字典形式写入日志 `extra` 的 `ratelimit_headers` 字段。

**替代方案：** 提取固定字段如 `x_ratelimit_remaining_requests` 并 flatten 到 `extra`。
**未选原因：** 不同 provider 的头名差异较大，原样打印避免丢失信息，也避免维护 provider 映射表。

### Decision 5：放行时间戳使用与滑动窗口相同的 `clock`

`SlidingWindowRateLimiter` 已支持注入 `clock`（默认 `time.monotonic`）。最小间隔也使用该 clock，确保测试可注入伪造时钟。

## Risks / Trade-offs

| 风险 | 缓解 |
|---|---|
| `min_interval` 与 `rpm` 配置冲突，导致实际限速远低于预期 | 在文档中明确说明：实际有效速率为 `min(rpm, 60000 / min_interval_ms)`（每分钟） |
| 最小间隔等待期间，单个 worker 无法处理队列中其他请求 | 等待时释放锁，其他协程可继续排队；processor 为单 worker，但锁释放不影响并发 acquire 的语义 |
| 429 日志中 `ratelimit_headers` 字典可能较大 | 仅过滤 `ratelimit` 与 `retry-after` 相关字段，通常不超过 10 个键 |
| litellm 某些版本未在 `RateLimitError` 中暴露 `response.headers` | 使用 `getattr` 安全访问，缺失时输出空字典 |

## Migration Plan

1. 代码变更后，现有未配置 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS` 的部署行为不变。
2. 如需启用最小间隔，逐步调大 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS` 并观察 `upstream_429_total` 指标与 429 日志中的 `ratelimit_headers`。
3. 无需数据迁移或停机。

## Open Questions

- 是否需要将最小间隔与 retry 行为联动（例如 retry 前重新 `acquire()`）？本次变更暂不处理，留待后续观察。
