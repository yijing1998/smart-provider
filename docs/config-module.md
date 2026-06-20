# 配置模块开发者指南

`src/config/` 负责 Smart-Provider 的运行时配置管理：定义 schema、加载来源、校验规则，并向其它模块提供按职责切分的配置视图。

## 模块结构

```
src/config/
├── __init__.py   # 公共接口：导出 Config、load_config
├── loader.py     # 加载入口：load_config(**overrides)
└── schema.py     # 数据模型：BaseSettings、组件视图、校验规则
```

| 文件 | 职责 |
|------|------|
| `schema.py` | 定义 `Config(BaseSettings)`、各组件视图模型、字段默认值与校验规则。 |
| `loader.py` | 提供 `load_config(**overrides)` 工厂函数，封装 `Config(...)` 构造，便于测试覆盖与后续扩展多来源加载。 |
| `__init__.py` | 稳定公共接口，调用方始终使用 `from src.config import Config, load_config`。 |

## 设计原则

### 1. 加载层扁平，视图层分组

`Config` 顶层字段保持扁平，环境变量直接使用 `SMART_PROVIDER_<FIELD_NAME>` 映射，无需嵌套分隔符。内部通过 property 返回按组件分组的小模型：

```python
config.queue               # QueueConfig
config.limiter             # LimiterConfig
config.forwarder           # ForwarderConfig
config.circuit_breaker     # CircuitBreakerConfig（预留）
config.observability       # ObservabilityConfig（预留）
config.distributed_rate_limiter  # DistributedRateLimiterConfig（预留）
```

这样组件构造函数只依赖自己的配置切片，例如：

```python
request_queue = RequestQueue(max_size=cfg.queue.max_size)
```

### 2. 配置来源优先级

`pydantic-settings` 默认优先级：

```
显式传入参数 > 环境变量 > .env 文件 > 默认值
```

`load_config(**overrides)` 中的 `overrides` 主要用于测试注入；生产环境通常只使用环境变量或 `.env` 文件。

### 3. 启动时校验

所有字段通过 Pydantic `Field(...)` 声明类型与范围。非法配置在实例化 `Config` 时即抛出 `ValidationError`，保证服务 fail-fast。

## 组件视图

```
┌─────────────────────────────────────────┐
│              Config                     │
│  （扁平字段，映射环境变量）               │
└──────────┬──────────────────────────────┘
           │
    ┌──────┼──────┬──────────┐
    ▼      ▼      ▼          ▼
┌───────┐ ┌───────┐ ┌────────┐ ┌────────────┐
│ queue │ │limiter│ │forwarder│ │ circuit_   │
│       │ │       │ │         │ │ breaker    │
└───────┘ └───────┘ └────────┘ └────────────┘
```

| 视图 | 模型 | 对应顶层字段 |
|------|------|--------------|
| `config.queue` | `QueueConfig` | `queue_max_size`, `queue_max_wait_ms` |
| `config.limiter` | `LimiterConfig` | `rate_limit_rpm`, `rate_limit_tpm`, `rate_limit_window_seconds` |
| `config.forwarder` | `ForwarderConfig` | `forwarder_timeout_ms`, `forwarder_max_retries`, `forwarder_retry_backoff_ms` |
| `config.circuit_breaker` | `CircuitBreakerConfig` | `circuit_breaker_*` |
| `config.observability` | `ObservabilityConfig` | `observability_*` |
| `config.distributed_rate_limiter` | `DistributedRateLimiterConfig` | `distributed_rate_limiter_*` |

## 新增配置字段流程

1. **在 `schema.py` 的 `Config` 中添加字段**
   - 设置合理的默认值。
   - 使用 `Field(ge=..., le=..., min_length=...)` 声明校验规则。
   - 如果字段属于某个组件，同步更新对应视图模型和 property。

2. **更新 `docs/configuration.md`**
   - 在环境变量清单中添加新行。
   - 如果有新的校验规则或示例，同步补充。

3. **补充或更新测试**
   - 在 `tests/test_config.py` 中添加默认值、环境变量、范围校验、组件视图测试。

4. **如果涉及产品行为变更**
   - 更新 `openspec/specs/configuration/spec.md` 中的对应 requirement。

## Reserved 字段约定

路线图中的远期能力（TPM 限速、熔断器、可观测性、分布式限速）已经在 schema 中占位：

- 字段名使用能力前缀，例如 `circuit_breaker_*`、`observability_*`、`distributed_rate_limiter_*`。
- 默认值设置为关闭或 `None`，确保不影响当前行为。
- 在代码注释和文档中标注“reserved for future use”。
- 组件视图已经返回对应配置切片，未来实现该能力时可直接消费，无需再调整 `Config` 结构。

## 测试

```bash
.venv/bin/python -m pytest tests/test_config.py -v
```

测试覆盖：

- 默认值
- 环境变量加载
- `.env` 文件加载
- 范围校验失败
- 组件视图
- `load_config(**overrides)` 覆盖优先级

## 相关文档

- 使用者配置参考：[configuration.md](configuration.md)
- 配置规格来源：`openspec/specs/configuration/spec.md`
