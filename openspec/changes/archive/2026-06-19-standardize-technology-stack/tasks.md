## 1. 依赖声明更新

- [x] 1.1 在 pyproject.toml 的 dependencies 中显式添加 pydantic>=2.0.0
- [x] 1.2 在 pyproject.toml 的 dependencies 中显式添加 pydantic-settings>=2.0.0
- [x] 1.3 检查并锁定 litellm 主版本号，确保与 technology-stack 规格一致
- [x] 1.4 在虚拟环境中重新解析依赖，确认无 Pydantic v1/v2 冲突

## 2. 主规格文档同步

- [x] 2.1 将 technology-stack capability 规格从变更目录同步至 openspec/specs/technology-stack/spec.md
- [x] 2.2 更新 openspec/specs/request-ingress/spec.md，补充 ADDED 中的技术栈约束条款
- [x] 2.3 更新 openspec/specs/upstream-forwarding/spec.md，补充异步转发与 litellm acompletion 相关条款
- [x] 2.4 更新 openspec/specs/configuration/spec.md，补充 Pydantic Settings 与环境变量加载条款
- [x] 2.5 更新受影响的 capability 规格 Purpose 字段，避免继续为 TBD

## 3. 规格一致性校验

- [x] 3.1 检查所有新增/修改 requirement 是否均包含至少一个 Scenario
- [x] 3.2 检查 Scenario 是否使用 #### 标题格式
- [x] 3.3 检查 technology-stack 规格中列出的技术与 pyproject.toml 依赖是否一致
- [x] 3.4 检查 design.md 中的决策与 specs 中的 requirement 是否对应

## 4. 变更收尾

- [x] 4.1 运行 openspec validate 校验变更 artifacts 完整性
- [x] 4.2 将 delta 规格合并至主规格（因 archive 工具检测到主规格已包含新增内容，本次通过手动同步完成）
- [x] 4.3 归档本次变更至 openspec/changes/archive/
