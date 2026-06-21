# 配置 Smart-Provider

Smart-Provider 使用 [pydantic-settings](https://docs.pydantic.dev/projects/pydantic-settings/) 加载运行时配置，支持以下两种来源：

- **环境变量**：所有变量以 `SMART_PROVIDER_` 为前缀。
- **`.env` 文件**：工作目录下的 `.env` 文件（UTF-8 编码）。

配置在启动阶段即完成类型与范围校验，非法配置会导致进程立即退出（fail-fast）。

## 配置加载优先级

```
┌─────────────────────────────────────────┐
│           配置来源优先级                 │
├─────────────────────────────────────────┤
│                                         │
│   1. 显式传入参数（主要用于测试）          │
│      load_config(server_port=7777)       │
│           ▼                             │
│   2. 环境变量                            │
│      SMART_PROVIDER_SERVER_PORT=9000     │
│           ▼                             │
│   3. .env 文件                           │
│      SMART_PROVIDER_SERVER_PORT=8080     │
│           ▼                             │
│   4. 默认值                               │
│      server_port = 8080                  │
│                                         │
└─────────────────────────────────────────┘
```

## 环境变量清单

| 环境变量 | 默认值 | 校验规则 | 说明 |
|----------|--------|----------|------|
| `SMART_PROVIDER_UPSTREAM_URL` | `https://api.openai.com/v1` | 非空字符串 | 真实上游 API Endpoint 地址 |
| `SMART_PROVIDER_SERVER_PORT` | `8080` | 1–65535 | 服务监听端口 |
| `SMART_PROVIDER_CLIENT_ID_HEADER` | `X-Client-Id` | 非空字符串 | 用于标识客户端的 HTTP Header 名称 |
| `SMART_PROVIDER_QUEUE_MAX_SIZE` | `1000` | ≥1 | 请求队列最大容量 |
| `SMART_PROVIDER_QUEUE_MAX_WAIT_MS` | `30000` | ≥1 | 请求在队列中最大等待时间（毫秒） |
| `SMART_PROVIDER_SHUTDOWN_DRAIN_TIMEOUT_MS` | `30000` | ≥1 | 优雅关闭时队列排空超时（毫秒） |
| `SMART_PROVIDER_RATE_LIMIT_RPM` | `60` | ≥1 | 每分钟最大请求数（RPM） |
| `SMART_PROVIDER_RATE_LIMIT_TPM` | 未设置 | 可选，≥1 | 每分钟最大 Token 数（TPM），当前预留 |
| `SMART_PROVIDER_RATE_LIMIT_WINDOW_SECONDS` | `60` | ≥1 | RPM 滑动窗口宽度（秒） |
| `SMART_PROVIDER_FORWARDER_TIMEOUT_MS` | `30000` | ≥1 | 上游 HTTP 调用超时（毫秒） |
| `SMART_PROVIDER_FORWARDER_MAX_RETRIES` | `0` | ≥0 | 上游请求失败后的最大重试次数 |
| `SMART_PROVIDER_FORWARDER_RETRY_BACKOFF_MS` | `1000` | ≥0 | 重试退避基数（毫秒） |
| `SMART_PROVIDER_CIRCUIT_BREAKER_ENABLED` | `false` | — | 熔断器开关 |
| `SMART_PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | ≥1 | 触发熔断的连续失败次数阈值 |
| `SMART_PROVIDER_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_MS` | `30000` | ≥1 | 熔断后恢复等待时间（毫秒） |
| `SMART_PROVIDER_OBSERVABILITY_LOG_LEVEL` | `INFO` | `DEBUG/INFO/WARNING/ERROR/CRITICAL` | 日志级别，当前预留 |
| `SMART_PROVIDER_OBSERVABILITY_METRICS_ENABLED` | `false` | — | 指标开关，当前预留 |
| `SMART_PROVIDER_DISTRIBUTED_RATE_LIMITER_ENABLED` | `false` | — | 分布式限速开关，当前预留 |
| `SMART_PROVIDER_DISTRIBUTED_RATE_LIMITER_URL` | 未设置 | 可选字符串 | 分布式限速后端地址，例如 `redis://localhost:6379` |

> 说明：表中标注“当前预留”的字段会被配置模型加载和校验，但当前代码尚未消费，默认处于关闭状态，不影响现有行为。熔断器相关字段已实现。

## 熔断器

熔断器用于在上游 API 持续异常时保护 Smart-Provider。当上游连续失败次数达到 `SMART_PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD` 时，熔断器打开，后续请求会直接返回 503 而不会调用上游；经过 `SMART_PROVIDER_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_MS` 后，熔断器进入半开状态，允许下一个请求作为探测，根据探测结果决定闭合或重新打开。

仅以下上游/网络层错误会计入熔断失败计数：

- 429 Too Many Requests
- 5xx 服务端错误
- 连接错误
- 上游超时

400/401/404 等客户端错误不会触发熔断计数。

示例配置：

```bash
SMART_PROVIDER_CIRCUIT_BREAKER_ENABLED=true
SMART_PROVIDER_CIRCUIT_BREAKER_FAILURE_THRESHOLD=3
SMART_PROVIDER_CIRCUIT_BREAKER_RECOVERY_TIMEOUT_MS=30000
```

## 流式响应

Smart-Provider 支持 OpenAI 兼容的流式聊天补全请求。当客户端发送 `stream=true` 时，系统会返回 `text/event-stream` 响应，逐 chunk 转发上游输出。

流式请求与非流式请求共享同一个请求队列和单一 Worker，因此同样受 RPM 限速器和熔断器保护。每个流式请求消耗 1 个 RPM 配额。

SSE 输出格式示例：

```http
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"}}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

流式过程中若发生错误，会发送 `event: error` 帧：

```http
event: error
data: {"error":{"message":"...","type":"ServiceUnavailableError"}}

data: [DONE]
```

## `.env` 文件示例

在工作目录创建 `.env` 文件：

```bash
SMART_PROVIDER_UPSTREAM_URL=https://api.example.com/v1
SMART_PROVIDER_RATE_LIMIT_RPM=120
SMART_PROVIDER_QUEUE_MAX_SIZE=2000
SMART_PROVIDER_OBSERVABILITY_LOG_LEVEL=DEBUG
```

当同时存在 `.env` 文件和环境变量时，**环境变量优先级更高**。未在 `.env` 或环境中设置的字段使用上表默认值。

## 启动校验

如果配置值类型不匹配或超出范围，`pydantic-settings` 会在启动时抛出 `ValidationError`，服务不会启动。例如：

```bash
export SMART_PROVIDER_RATE_LIMIT_RPM=0
.venv/bin/python -m uvicorn src.ingress.app:create_app --factory
```

将报错并退出，因为 `rate_limit_rpm` 必须大于 0。

其它常见校验失败场景：

| 错误配置 | 原因 |
|----------|------|
| `SMART_PROVIDER_SERVER_PORT=70000` | 端口超出 1–65535 范围 |
| `SMART_PROVIDER_QUEUE_MAX_SIZE=-1` | 队列容量必须 ≥1 |
| `SMART_PROVIDER_OBSERVABILITY_LOG_LEVEL=VERBOSE` | 日志级别不在允许集合中 |
| `SMART_PROVIDER_UPSTREAM_URL=` | 上游地址不能为空 |

## 启动方式

```bash
.venv/bin/python -m uvicorn src.ingress.app:create_app --factory --host 0.0.0.0 --port 8080
```

`--port` 仅影响 uvicorn 监听端口，应用实际读取的配置仍以 `SMART_PROVIDER_SERVER_PORT` 或对应 `.env` 值为准。建议在本地开发时让两者保持一致。

## 相关文档

- 开发者扩展指南：[config-module.md](config-module.md)
- 配置规格来源：`openspec/specs/configuration/spec.md`
