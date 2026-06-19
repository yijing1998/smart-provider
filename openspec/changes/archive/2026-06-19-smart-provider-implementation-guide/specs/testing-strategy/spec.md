## ADDED Requirements

### Requirement: 定义单元测试覆盖范围
编码实现指导文档 SHALL 说明队列、限速器、转发器三个核心组件的单元测试重点。

#### Scenario: 编写限速器测试
- **WHEN** 开发人员为限速器编写单元测试
- **THEN** 文档 SHALL 说明需验证滑动窗口清理、RPM 上限与窗口边界行为

### Requirement: 定义集成测试场景
编码实现指导文档 SHALL 说明端到端限速测试、队列满载测试与上游异常测试三个关键集成场景。

#### Scenario: 验证限速效果
- **WHEN** 运行端到端测试
- **THEN** 文档 SHALL 说明如何判断 RPM 限速是否有效平滑了请求流量
