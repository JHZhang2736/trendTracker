---
description: When creating git commits
globs:
---

# Commit 规范

格式：`<type>(<scope>): <subject>`

类型：
- `feat` 新功能 / `fix` 修复 / `refactor` 重构 / `test` 测试 / `chore` 工程 / `docs` 文档

注意：
- commit 信息中**不要使用 Co-Authored-By**
- 多行 commit message 使用临时文件 + `-F` 标志（不用 heredoc）
