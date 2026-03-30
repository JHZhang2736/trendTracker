---
description: When using gh CLI or git commands that need multi-line content (PR body, issue body, commit message)
globs:
---

# 禁止 Here-Doc 和引号换行

gh CLI 和 git 命令禁止使用 Here-Docs (`<<EOF`) 或带引号换行和 `#` 的 shell 命令。
必须使用临时文件配合 `--body-file` 或 `-F` 标志传递多行内容。

原因：权限检查机制会被 heredoc/引号换行触发，导致命令被拒绝。

示例：
```bash
# ❌ 错误
gh pr create --body "$(cat <<EOF
...
EOF
)"

# ✅ 正确
echo "PR body content" > /tmp/pr_body.txt
gh pr create --body-file /tmp/pr_body.txt
```
