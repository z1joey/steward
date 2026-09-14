#!/usr/bin/env bash
# release.sh · 发版：将 develop 最新内容以 PR 方式合入 main（squash 发布线专用）
#
# 用法：
#   scripts/release.sh [分支名]        # 分支名缺省：release/日期-时间
#
# 流程：自 origin/develop 拉发布分支 → 预合并 origin/main（冲突一律取 develop 侧，
# main 无独有内容故无损）→ 推送 → 提 PR（base: main）。
# 之后在 GitHub 上对该 PR 点「Squash and merge」完成发布。
#
# 前置：工作区干净；已安装并登录 gh CLI。
set -euo pipefail

BRANCH_NAME="${1:-release/$(date +%Y%m%d-%H%M)}"

cd "$(git rev-parse --show-toplevel)"

# —— 前置检查 ——
command -v gh >/dev/null 2>&1 || { echo "✗ 未安装 GitHub CLI (gh)，无法提 PR"; exit 1; }
if [ -n "$(git status --porcelain)" ]; then
  echo "✗ 工作区有未提交改动，请先处理："
  git status --short
  exit 1
fi

git fetch origin --prune

# —— 无增量守卫：develop 与 main 内容一致则没有可发布的东西 ——
if git diff --quiet origin/main origin/develop; then
  echo "✗ main 已包含 develop 的全部内容（无增量），无需发版"
  exit 1
fi

# —— 自 origin/develop 拉发布分支 ——
git checkout -B "$BRANCH_NAME" origin/develop

# —— 预合并 main：add/add 冲突一律取 develop 侧（-X ours，无损）——
git merge -X ours origin/main -m "chore: 预合并 main（冲突取 develop 侧）" \
  || { echo "✗ 预合并失败，请手工处理"; exit 1; }

git push -u origin "$BRANCH_NAME"

# —— 提 PR（标题 + 增量提交清单）——
TITLE="发布：$(date +%Y-%m-%d) develop → main"
BODY="$(git log --no-merges origin/main..HEAD --format='- %s' | tail -n +2)
${BODY_EXTRA:-}

> 合并方式：Squash and merge。"
gh pr create --base main --head "$BRANCH_NAME" --title "$TITLE" --body "$BODY"

echo "✓ 已创建 PR：在 GitHub 上对该 PR 点「Squash and merge」完成发布"
