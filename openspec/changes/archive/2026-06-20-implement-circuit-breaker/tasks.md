# 熔断器实现任务清单

## 1. 熔断器核心实现

- [x] 1.1 创建 `src/circuit_breaker/__init__.py`，导出 `CircuitBreaker`、`CircuitBreakerState`
- [x] 1.2 创建 `src/circuit_breaker/circuit_breaker.py`，实现 CLOSED/OPEN/HALF_OPEN 状态机
- [x] 1.3 实现 `can_execute()` 方法：CLOSED 放行、OPEN 拒绝、HALF_OPEN 允许单探测
- [x] 1.4 实现 `record_success()`、`record_failure()`、`record_exception()` 方法
- [x] 1.5 实现异常分类逻辑：仅 429/5xx/连接错误/超时计入失败，400/401/404 不计入
- [x] 1.6 实现时钟注入，便于测试中控制状态转换时间

## 2. Processor 集成

- [x] 2.1 修改 `RequestProcessor.__init__()`，支持注入可选的 `CircuitBreaker`
- [x] 2.2 在 `Processor._run()` 出队后、限速前调用 `can_execute()`，熔断打开时设置 `ServiceUnavailableError`
- [x] 2.3 在转发成功后调用 `record_success()`
- [x] 2.4 在转发异常后调用 `record_exception()`
- [x] 2.5 保持未启用熔断器时的原有行为不变

## 3. Ingress 与配置集成

- [x] 3.1 修改 `src/ingress/app.py` 中的 `create_app()`，根据配置创建 `CircuitBreaker` 并注入 Processor
- [x] 3.2 确认 `src/config/schema.py` 中已有配置项满足需求（enabled、threshold、recovery_timeout）
- [x] 3.3 验证默认 `circuit_breaker_enabled=false` 时服务启动正常

## 4. 可观测性扩展

- [x] 4.1 扩展 `MetricsCollector`，新增 `circuit_breaker_state` 状态字段
- [x] 4.2 扩展 `MetricsCollector`，新增 `circuit_breaker_opens_total` 计数器
- [x] 4.3 在熔断器状态转换时更新指标
- [x] 4.4 验证 `/metrics` 端点返回新增指标

## 5. 测试

- [x] 5.1 创建 `tests/test_circuit_breaker.py`，覆盖状态转换、连续失败、恢复超时、半开探测、异常分类
- [x] 5.2 在 `tests/test_processor.py` 中补充熔断器集成测试：熔断打开时请求快速失败、探测成功后恢复
- [x] 5.3 补充 Ingress 端到端测试：模拟上游连续失败，验证返回 503 及后续恢复
- [x] 5.4 运行完整测试套件 `pytest tests/`，确保全部通过

## 6. 文档

- [x] 6.1 更新 `docs/configuration.md`，添加熔断器配置项说明与行为描述
- [x] 6.2 在 `README.md` 扩展路线图中标注熔断器已完成
- [x] 6.3 检查所有代码注释与 docstring 清晰准确
