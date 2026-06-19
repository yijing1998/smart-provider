## ADDED Requirements

### Requirement: 定义错误分类
编码实现指导文档 SHALL 至少定义队列已满、上游超时、上游 429、上游 5xx 四类错误，并说明各自的触发条件与建议响应。

#### Scenario: 处理上游 429
- **WHEN** 上游返回 429 Too Many Requests
- **THEN** 文档 SHALL 说明应记录事件并可作为调整限速策略或触发退避的依据

### Requirement: 说明安全余量策略
编码实现指导文档 SHALL 建议将 RPM 限制值设置为上游公告值的合理比例，并说明原因。

#### Scenario: 配置 RPM 限制
- **WHEN** 设置 rateLimit.rpm
- **THEN** 文档 SHALL 建议按上游 RPM 的 80% 左右配置以留出缓冲
