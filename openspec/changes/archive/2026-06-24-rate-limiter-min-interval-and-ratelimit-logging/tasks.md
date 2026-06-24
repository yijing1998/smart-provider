## 1. 配置模型扩展

- [x] 1.1 在 `LimiterConfig` 中新增 `min_interval_ms: Optional[int] = Field(default=None, ge=0)`
- [x] 1.2 在 `Config` 中新增 `rate_limit_min_interval_ms: Optional[int] = Field(default=None, ge=0)`
- [x] 1.3 更新 `Config.limiter` 属性，将 `rate_limit_min_interval_ms` 传递给 `LimiterConfig`
- [x] 1.4 为新增配置字段补充单元测试，覆盖默认值、环境变量加载与非法值校验

## 2. 限速器最小间隔实现

- [x] 2.1 在 `SlidingWindowRateLimiter` 中记录上一次放行时间戳
- [x] 2.2 在 `acquire()` 中，放行前检查并等待 `min_interval_ms`
- [x] 2.3 等待期间释放锁，确保并发安全与协程调度
- [x] 2.4 为最小间隔行为补充单元测试：未配置时不影响、间隔未到等待、间隔已到放行、并发保持间隔

## 3. 上游 429 响应头日志

- [x] 3.1 在 `LitellmForwarder` 中新增辅助函数，从 `RateLimitError.response.headers` 提取包含 `ratelimit` 或 `retry-after` 的字段
- [x] 3.2 在 `_record_upstream_error` 中将提取出的原始响应头写入日志 `extra["ratelimit_headers"]`
- [x] 3.3 确保 `response.headers` 缺失时安全降级为空字典
- [x] 3.4 为 429 响应头日志补充单元测试：含 `x-ratelimit-*`、含 `retry-after`、头缺失、大小写混合

## 4. 集成与回归

- [x] 4.1 运行完整测试套件，确保 `test_processor` 中限速相关用例通过
- [x] 4.2 更新 `docs/configuration.md` 中关于 `rate_limit_rpm` 与新增最小间隔的说明
- [x] 4.3 在本地或测试环境验证 429 日志输出格式符合预期
