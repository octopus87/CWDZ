#!/usr/bin/env bash
# 登录 GitHub 后运行：推送代码并触发 Windows Actions 构建
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

GH="${GH_CLI:-gh}"
if ! command -v "$GH" >/dev/null 2>&1; then
  for c in /tmp/gh_*/bin/gh /opt/homebrew/bin/gh; do
    if [ -x "$c" ]; then GH="$c"; break; fi
  done
fi

if ! command -v "$GH" >/dev/null 2>&1; then
  echo "未找到 gh。请先安装 GitHub CLI："
  echo "  https://cli.github.com/"
  exit 1
fi

if ! "$GH" auth status >/dev/null 2>&1; then
  echo "请先登录 GitHub（会打开浏览器）："
  echo "  $GH auth login -h github.com -p https -w"
  exit 1
fi

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  git init -b main
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  REPO_NAME="${GITHUB_REPO_NAME:-CWDZ}"
  VIS="${GITHUB_REPO_VISIBILITY:-private}"
  echo "==> 创建 GitHub 仓库: $REPO_NAME ($VIS)"
  "$GH" repo create "$REPO_NAME" --"$VIS" --source=. --remote=origin --push
else
  git add -A
  if git diff --cached --quiet; then
    echo "无新改动，直接触发 workflow"
  else
    git commit -m "chore: trigger Windows CI build"
    git push -u origin main
  fi
fi

echo "==> 触发 Build Windows workflow"
"$GH" workflow run build-windows.yml

RUN_ID="$("$GH" run list --workflow=build-windows.yml --limit=1 --json databaseId -q '.[0].databaseId')"
echo "==> 等待构建完成（约 30–60 分钟）run_id=$RUN_ID"
"$GH" run watch "$RUN_ID" --exit-status

mkdir -p dist
"$GH" run download "$RUN_ID" -D dist -n CWDZ-Windows-x64
echo ""
echo "完成: dist/CWDZ-Windows-x64.zip"
