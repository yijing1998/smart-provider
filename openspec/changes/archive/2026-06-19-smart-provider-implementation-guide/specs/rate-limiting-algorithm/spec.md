## ADDED Requirements

### Requirement: 详细说明滑动窗口 RPM 算法
编码实现指导文档 SHALL 详细说明滑动窗口 RPM 限速算法的实现步骤，包括时间戳清理、放行判断与边界条件。

#### Scenario: 实现限速器
- **WHEN** 开发人员实现限速器
- **THEN** 文档 SHALL 提供算法步骤：清理过期时间戳、判断是否达到 RPM 上限、记录放行时间戳

### Requirement: 说明限速器与队列的协作方式
编码实现指导文档 SHALL 说明限速器不主动操作队列，而由调度循环协调两者。

#### Scenario: 设计调度循环
- **WHEN** 设计请求出队与转发流程
- **THEN** 文档 SHALL 说明调度循环仅在队列非空且限速器允许放行时才出队
