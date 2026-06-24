## Why

当前 Smart-Provider 的 RPM 滑动窗口限速器只能保证“单位时间内总量不超限”，无法约束请求之间的最小间隔，导致短时间内仍可能向上游发送突发流量并触发 429。同时，上游返回 429 时，系统没有记录上游的 `x-ratelimit-*` 响应头，运维人员无法判断 429 是由 RPM、TPM 还是突发限制引起，难以针对性调优。

## What Changes

- 为滑动窗口限速器新增全局最小请求间隔 `rate_limit_min_interval_ms`：相邻两次获得 permit 的放行时间不得小于该间隔，平滑突发流量。
- 将最小间隔配置纳入 `LimiterConfig` 与 `Config` 配置模型，支持通过 `SMART_PROVIDER_RATE_LIMIT_MIN_INTERVAL_MS` 环境变量配置。
- 在 `LitellmForwarder` 收到 `RateLimitError` 时，将上游响应头中所有包含 `ratelimit` 及 `retry-after` 的字段原样打印到可观测日志中。
- 更新 `rate-limiting`、`configuration`、`observability` 三个能力规格，明确新增行为与配置约束。

## Capabilities

### New Capabilities

（无新能力，均为现有能力增强）

### Modified Capabilities

- `rate-limiting`: 新增全局最小请求间隔要求，扩展现有 RPM 滑动窗口语义。
- `configuration`: 新增 `rate_limit_min_interval_ms` 配置字段及其加载、校验规则。
- `observability`: 新增上游 429 响应头（`x-ratelimit-*`、`retry-after`）原样日志记录要求。

## Impact

- 受影响的代码：`src/limiter/rate_limiter.py`、`src/config/schema.py`、`src/forwarder/forwarder.py`。
- 受影响的测试：`tests/test_limiter.py`、`tests/test_config.py`、`tests/test_forwarder.py`、`tests/test_processor.py`。
- 配置兼容性：新增字段默认值为 `None`（不启用），对现有部署完全向后兼容。
- 日志输出：429 日志的 `extra` 字段会增加 `ratelimit_headers` 原始头字典，不改变日志级别与消息主体。
