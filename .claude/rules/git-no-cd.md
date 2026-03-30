---
description: When running git commands that need to target a specific directory
globs:
---

# Git 命令禁止 cd 组合

永远不要写 `cd <path> && git ...` 的组合形式。
所有 git 命令需要指定路径时，使用 `git -C <path> <command>` 形式。

- ❌ `cd "D:/桌面/trendTracker" && git status`
- ✅ `git -C "D:/桌面/trendTracker" status`
