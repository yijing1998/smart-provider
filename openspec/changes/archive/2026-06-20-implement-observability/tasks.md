## 1. 可观测性基础模块

- [x] 1.1 创建 `src/observability/__init__.py`，导出公共接口
- [x] 1.2 创建 `src/observability/metrics.py`，实现 `MetricsCollector` 单例
- [x] 1.3 实现指标：queue_size、requests_enqueued_total、requests_processed_total、upstream_429_total、upstream_5xx_total
- [x] 1.4 实现等待时间统计：count、sum、max、avg
- [x] 1.5 使用 `asyncio.Lock` 保证并发安全
- [x] 1.6 提供 `reset()` 方法供测试使用

## 2. Processor 埋点

- [x] 2.1 在 `submit()` 中记录 `requests_enqueued_total` 与 `queue_size`
- [x] 2.2 在 Worker 出队后计算 `wait_ms`，记录 `requests_processed_total` 与等待时间统计
- [x] 2.3 在转发成功/失败时输出结构化日志
- [x] 2.4 入队/出队日志使用 `smart-provider` logger

## 3. Forwarder 埋点

- [x] 3.1 在 `LitellmForwarder` 中捕获上游 429，调用 `record_upstream_429()`
- [x] 3.2 在 `LitellmForwarder` 中捕获上游 5xx / 连接错误，调用 `record_upstream_5xx()`
- [x] 3.3 继续向上传播异常，不破坏现有错误处理

## 4. Ingress 集成

- [x] 4.1 在 `create_app()` 中根据 `cfg.observability_log_level` 设置 `smart-provider` logger 级别
- [x] 4.2 当 `cfg.observability_metrics_enabled` 为 True 时注册 `/metrics` 端点
- [x] 4.3 `/metrics` 返回 `MetricsCollector.snapshot()` 的 JSON 快照

## 5. 测试

- [x] 5.1 新建 `tests/test_observability.py`
- [x] 5.2 测试 MetricsCollector 计数器更新
- [x] 5.3 测试等待时间统计
- [x] 5.4 测试 `/metrics` 端点在启用时返回指标，在禁用时 404
- [x] 5.5 测试 Processor 埋点更新指标
- [x] 5.6 测试 Forwarder 429/5xx 更新指标
- [x] 5.7 运行全部测试并通过：`pytest tests/`

## 6. 规格同步与归档

- [ ] 6.1 将 `openspec/specs/observability/spec.md` 的 Purpose 从 TBD 补全
- [ ] 6.2 同步 delta spec 中的 ADDED/MODIFIED 要求到主规格
- [ ] 6.3 运行 `openspec validate implement-observability` 确认变更有效
- [ ] 6.4 归档变更
