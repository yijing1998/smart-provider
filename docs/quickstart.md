# 快速开始

本指南帮助你在 5 分钟内在本地启动 Smart-Provider，并完成第一个模型 API 请求。

---

## 前置条件

- Python >= 3.10
- 一个模型 API 的访问密钥（例如 OpenAI API Key）
- `curl` 或任意 HTTP 客户端

---

## 1. 安装依赖

Smart-Provider 使用项目自带的虚拟环境 `.venv`：

```bash
.venv/bin/python -m pip install -e .
```

> 如果没有 `.venv`，可使用系统 Python 创建：
> ```bash
> python3.10 -m venv .venv
> .venv/bin/python -m pip install -e .
> ```

---

## 2. 配置环境变量

在项目根目录复制示例配置并编辑：

```bash
cp .env.example .env
```

修改 `.env`，至少填写上游 API 地址和你的 RPM 限制：

```bash
SMART_PROVIDER_UPSTREAM_URL=https://api.openai.com/v1
SMART_PROVIDER_RATE_LIMIT_RPM=60
```

完整配置说明见 [docs/configuration.md](configuration.md)。

---

## 3. 启动服务

```bash
.venv/bin/python -m uvicorn src.ingress.app:create_app --factory --host 0.0.0.0 --port 8080
```

看到类似如下日志即表示启动成功：

```
INFO:     Started server process [12345]
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

> `--port` 仅影响 uvicorn 监听端口，应用实际读取的配置仍以 `SMART_PROVIDER_SERVER_PORT` 或 `.env` 中的值为准。建议在本地让两者保持一致。

---

## 4. 发送第一个请求

Smart-Provider 暴露 OpenAI 兼容的 `POST /v1/chat/completions` 端点。你只需要把原本发给上游 API 的请求原样发给 Smart-Provider，`Authorization` 等请求头会自动透传给上游。

### 非流式请求

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

正常返回示例：

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "gpt-4o",
  "choices": [...]
}
```

### 流式请求

添加 `"stream": true`：

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

返回为 `text/event-stream` 格式：

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"你"}}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"好"}}]}

data: [DONE]
```

---

## 5. 检查服务健康状态

Smart-Provider 提供两个健康检查端点：

### 存活探针

```bash
curl http://localhost:8080/health
```

返回：

```json
{"status": "healthy"}
```

### 就绪探针

```bash
curl http://localhost:8080/ready
```

返回：

```json
{"status": "ready"}
```

> 服务刚启动时，`/ready` 可能会短暂返回 503，因为后台 Processor 尚未启动完成。

---

## 6. 验证限速是否生效

将 `SMART_PROVIDER_RATE_LIMIT_RPM` 设为一个较小的值（例如 `5`），然后快速并发发送多个请求：

```bash
for i in {1..10}; do
  curl -s -o /dev/null -w "%{http_code}\n" \
    http://localhost:8080/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}' &
done
wait
```

如果部分请求返回 `503`，说明队列已满或请求等待超时，Smart-Provider 正在主动保护上游。你会观察到请求以不超过每分钟 5 次的速率被转发。

> 验证限速时请注意控制并发量，避免消耗过多上游配额。

---

## 下一步

- 查看完整配置说明：[docs/configuration.md](configuration.md)
- 了解模块扩展方式：[docs/config-module.md](config-module.md)
- 查看请求接入层细节：[docs/ingress.md](ingress.md)
