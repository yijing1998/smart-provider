## 1. 依赖与模块结构

- [x] 1.1 在 `pyproject.toml` 中添加 `python-dotenv>=1.0.0` 依赖
- [x] 1.2 创建 `src/config/schema.py` 文件
- [x] 1.3 创建 `src/config/loader.py` 文件
- [x] 1.4 更新 `src/config/__init__.py`，导出 `Config` 与 `load_config`

## 2. 配置 Schema 实现

- [x] 2.1 在 `schema.py` 中定义 `Config(BaseSettings)`，设置 `env_prefix="SMART_PROVIDER_"` 与 `.env` 文件支持
- [x] 2.2 为当前字段增加类型与范围校验：`upstream_url`、`server_port`、`client_id_header`、`queue_max_size`、`queue_max_wait_ms`、`rate_limit_rpm`、`rate_limit_window_seconds`、`forwarder_timeout_ms`、`forwarder_max_retries`、`forwarder_retry_backoff_ms`
- [x] 2.3 为远期能力添加占位字段：`rate_limit_tpm`、`circuit_breaker_*`、`observability_*`、`distributed_rate_limiter_*`，默认值关闭
- [x] 2.4 定义组件视图模型：`QueueConfig`、`LimiterConfig`、`ForwarderConfig`、`CircuitBreakerConfig`、`ObservabilityConfig`、`DistributedRateLimiterConfig`
- [x] 2.5 在 `Config` 上添加 property，返回上述组件视图

## 3. 加载器与公共接口

- [x] 3.1 在 `loader.py` 中实现 `load_config(**overrides) -> Config`
- [x] 3.2 删除 `src/config/config.py` 及其中未使用的 `Config.from_dict` 方法
- [x] 3.3 验证 `from src.config import Config, load_config` 公共接口稳定可用

## 4. 消费方适配

- [x] 4.1 更新 `src/ingress/app.py`，使用 `load_config()` 初始化配置
- [x] 4.2 修正 `RequestContext.max_wait_time_ms` 的赋值来源为 `cfg.queue_max_wait_ms`
- [x] 4.3 更新 `src/ingress/app.py` 中队列构造逻辑，使用 `cfg.queue` 视图（保持 `RequestQueue` 构造参数兼容）
- [x] 4.4 （可选）调整 `src/queue/queue.py` 与 `src/forwarder/forwarder.py`，支持接收各自的配置视图

## 5. 测试

- [x] 5.1 新建 `tests/test_config.py`，覆盖默认配置值
- [x] 5.2 添加环境变量加载测试：`SMART_PROVIDER_UPSTREAM_URL`、`SMART_PROVIDER_QUEUE_MAX_SIZE` 等
- [x] 5.3 添加 `.env` 文件加载测试
- [x] 5.4 添加范围校验失败测试：`rate_limit_rpm=0`、`server_port=70000`、`queue_max_size=-1`
- [x] 5.5 添加组件视图测试：`config.queue.max_size`、`config.limiter.rpm`
- [x] 5.6 更新 `tests/test_ingress.py`，确保 `Config(...)` 构造与 `create_app(config=...)` 注入仍正常工作
- [x] 5.7 运行全部测试并通过：`pytest tests/`

## 6. 规格同步与收尾

- [x] 6.1 将 `openspec/changes/implement-config-management/specs/configuration/spec.md` 中的变更同步到 `openspec/specs/configuration/spec.md`
- [x] 6.2 运行 `openspec validate implement-config-management` 确认实现与规格一致
- [x] 6.3 归档变更
