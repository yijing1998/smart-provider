---
description: 使用 `git commit` 命令把当前变更所涉及的文件提交到本地代码仓库
---

把变更所涉及的文件提交到本地仓库

**执行步骤**

1. 通过上下文，确定当前变更所涉及的文件列表

2. 用简洁语言概括当前变更，把内容保存到临时目录 /tmp/{random-file-name}

3. 使用如下命令提交变更
```
git commit -F /tmp/{random-file-name} --cleanup=verbatim
```

**注意事项**
- 依据的上下文范围是：从上一次执行 /git-commit 之后到本次执行 /git-commit之前
- **必须**通过上下文确定变更所涉及的文件列表，使用`git status`命令获得的变更列表，不能正确反映真实的变更情况，如临时文件、与本次变更无关的文件的修改，都会在`git status`命令结果中出现，需要进行排查
- {random-file-name}指的是随机文件名，可通过`mktemp`命令获得