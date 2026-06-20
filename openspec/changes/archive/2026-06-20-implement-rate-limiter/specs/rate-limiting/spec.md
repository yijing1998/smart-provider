## ADDED Requirements

### Requirement: 限速器提供异步放行接口

Smart-Provider 的限速器 SHALL 提供可被请求处理 Worker 调用的异步接口，以便在窗口容量不足时等待，在容量释放后放行。

#### Scenario: 窗口已满时等待放行

- **WHEN** 当前时间窗口内已发送请求数达到 RPM 限制
- **THEN** 调用方 SHALL 能够通过限速器的异步接口等待，直到窗口容量释放后获得放行

#### Scenario: 窗口未届满时立即放行

- **WHEN** 当前时间窗口内已发送请求数小于 RPM 限制
- **THEN** 调用方 SHALL 立即获得放行，无需等待

### Requirement: 限速器提供即时查询接口

Smart-Provider 的限速器 SHALL 提供即时查询接口，供调用方在不阻塞的情况下判断当前是否可放行。

#### Scenario: 查询当前是否可放行

- **WHEN** 调用方查询限速器当前状态
- **THEN** 限速器 SHALL 立即返回当前是否允许下一个请求出队

### Requirement: 限速器支持并发调用

Smart-Provider 的限速器 SHALL 在并发调用下保持状态一致，避免多个 Worker 同时通过放行判断导致实际发送请求数超过 RPM 限制。

#### Scenario: 多个 Worker 同时请求放行

- **WHEN** 多个 Worker 在同一时刻请求放行
- **THEN** 限速器 SHALL 保证在窗口容量范围内的放行次数不超过 RPM 限制
