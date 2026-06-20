## 1. 模块结构

- [x] 1.1 创建 `src/limiter/__init__.py`，导出公共接口
- [x] 1.2 创建 `src/limiter/rate_limiter.py`（或 `limiter.py`）

## 2. 限速器核心实现

- [x] 2.1 实现 `SlidingWindowRateLimiter` 类，接收 `LimiterConfig`
- [x] 2.2 实现 `is_allowed() -> bool` 即时判断接口
- [x] 2.3 实现 `async acquire() -> None` 异步等待放行接口
- [x] 2.4 使用 `asyncio.Lock` 保证并发安全
- [x] 2.5 根据 `rate_limit_window_seconds` 过滤窗口外记录

## 3. 测试

- [x] 3.1 新建 `tests/test_limiter.py`
- [x] 3.2 添加测试：窗口未超限立即放行
- [x] 3.3 添加测试：窗口已满时 `is_allowed` 返回 False
- [x] 3.4 添加测试：窗口滚动后恢复放行
- [x] 3.5 添加测试：RPM 配置变更生效
- [x] 3.6 添加测试：并发竞争下放行次数不超过 RPM 限制
- [x] 3.7 运行全部测试并通过：`pytest tests/`

## 4. 规格同步与归档

- [ ] 4.1 确认 `openspec/specs/rate-limiting/spec.md` 已反映新增接口与并发安全要求
- [ ] 4.2 运行 `openspec validate implement-rate-limiter` 确认变更有效
- [ ] 4.3 归档变更
