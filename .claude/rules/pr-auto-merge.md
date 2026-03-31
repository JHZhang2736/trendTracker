---
description: After creating or pushing a GitHub pull request
globs:
---

# PR 创建后自动等待 CI 并合并

创建 PR 后，立即用循环命令轮询 CI 状态，全部通过后自动 squash merge，不需要打扰用户。

流程：
1. 提交 PR 前，在功能分支上运行 `git-cliff -o CHANGELOG.md` 生成最新 changelog，包含在 commit 中
2. PR 创建/推送后，每 30 秒检查一次 CI 状态
3. 最多等 10 分钟（20 次轮询）
4. CI 全绿 → 自动 `gh pr merge --squash --delete-branch`，然后 checkout main 并 pull
5. CI 失败 → 停止轮询，告知用户失败原因
