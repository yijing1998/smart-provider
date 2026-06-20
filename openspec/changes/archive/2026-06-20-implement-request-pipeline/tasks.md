## 1. Queue 异步化

- [x] 1.1 将 `RequestQueue` 内部存储从 list 替换为 `asyncio.Queue`
- [x] 1.2 保留 `enqueue()`、`size()`、`is_full()` 同步接口
- [x] 1.3 新增 `async dequeue()` 接口
- [x] 1.4 更新或新建 `tests/test_queue.py` 验证异步 dequeue 与容量行为

## 2. Forwarder 异步化

- [x] 2.1 将 `Forwarder.forward()` 改为 `async def forward_async()`
- [x] 2.2 保留 stub 实现（返回固定响应），确保现有测试可适配
- [x] 2.3 更新 `src/forwarder/__init__.py` 导出（如有必要）

## 3. Processor 实现

- [x] 3.1 创建 `src/processor.py`
- [x] 3.2 实现 `RequestProcessor` 类，接收 Queue、Limiter、Forwarder
- [x] 3.3 实现 `submit(context) -> Future`：注册 Future、入队、返回 Future
- [x] 3.4 实现 `start()` / `stop()` 生命周期
- [x] 3.5 实现单 Worker 循环：dequeue -> acquire -> 检查等待超时 -> forward_async -> set result/exception
- [x] 3.6 处理 Future 已取消/已完成的安全设置

## 4. Ingress 适配

- [x] 4.1 在 `create_app()` 中组装 Processor、Queue、Limiter、Forwarder
- [x] 4.2 使用 FastAPI `lifespan` 管理 Processor 启动/停止
- [x] 4.3 修改 `chat_completions` 端点为 async，使用 `processor.submit(context)` + `asyncio.wait_for`
- [x] 4.4 队列已满返回 503，等待超时返回 504，转发错误返回 500

## 5. 测试

- [x] 5.1 新建 `tests/test_processor.py`
- [x] 5.2 测试 Future 结果成功回传
- [x] 5.3 测试限速器控制出队速率
- [x] 5.4 测试请求等待超时
- [x] 5.5 测试 Processor 启动/停止生命周期
- [x] 5.6 更新 `tests/test_ingress.py`，适配异步端点与 Processor 注入
- [x] 5.7 运行全部测试并通过：`pytest tests/`

## 6. 规格同步与归档

- [ ] 6.1 确认 `openspec/specs/request-pipeline/spec.md` 已创建并同步到主规格目录
- [ ] 6.2 运行 `openspec validate implement-request-pipeline` 确认变更有效
- [ ] 6.3 归档变更
