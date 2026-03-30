---
description: When starting new feature development, bug fixes, or any code changes that will be committed
globs:
---

# 开发流程规范

1. **开发前必须创建 GitHub Issue**，记录功能点和验收标准
2. 基于 Issue 创建功能分支：`feature/issue-{n}-{desc}` / `fix/issue-{n}-{desc}`
3. 开发完成后确保测试通过，再提交 PR 合并到 main
4. PR 使用 Squash Merge，合并后删除功能分支
5. `main` 禁止直接 push，所有变更通过 PR 合并
6. 不得跳过 Issue 直接在 main 上开发
