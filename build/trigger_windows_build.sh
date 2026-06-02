#!/usr/bin/env bash
# 登录 GitHub 后运行：推送代码并触发 Windows Actions 构建
# 方式 A: gh auth login 后本脚本自动用 gh
# 方式 B: export GITHUB_TOKEN=ghp_xxx （见 build/README.md）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPO_NAME="${GITHUB_REPO_NAME:-CWDZ}"
VIS="${GITHUB_REPO_VISIBILITY:-private}"

api() {
  curl -fsSL -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$@"
}

ensure_git_commit() {
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    git init -b main
  fi
  git add -A
  if ! git diff --cached --quiet 2>/dev/null || [ -z "$(git rev-parse --verify HEAD 2>/dev/null || true)" ]; then
    git commit -m "chore: trigger Windows CI build" || true
  fi
}

run_with_gh() {
  local GH="$1"
  if ! "$GH" auth status >/dev/null 2>&1; then
    echo "请先登录 GitHub（会打开浏览器）："
    echo "  $GH auth login -h github.com -p https -w"
    return 1
  fi
  ensure_git_commit
  if ! git remote get-url origin >/dev/null 2>&1; then
    echo "==> 创建 GitHub 仓库: $REPO_NAME ($VIS)"
    "$GH" repo create "$REPO_NAME" --"$VIS" --source=. --remote=origin --push
  else
    git push -u origin main
  fi
  echo "==> 触发 Build Windows workflow"
  "$GH" workflow run build-windows.yml
  local run_id
  run_id="$("$GH" run list --workflow=build-windows.yml --limit=1 --json databaseId -q '.[0].databaseId')"
  echo "==> 等待构建（约 30–60 分钟）run_id=$run_id"
  "$GH" run watch "$run_id" --exit-status
  mkdir -p dist
  "$GH" run download "$run_id" -D dist -n CWDZ-Windows-x64
  echo "完成: dist/CWDZ-Windows-x64.zip"
}

run_with_token() {
  if [ -z "${GITHUB_TOKEN:-}" ]; then
    echo "未设置 GITHUB_TOKEN。"
    echo "1. 浏览器打开 https://github.com/settings/tokens/new?scopes=repo,workflow&description=CWDZ-CI"
    echo "2. 生成 Classic token 后执行: export GITHUB_TOKEN=ghp_xxxx"
    echo "3. 重新运行本脚本"
    return 1
  fi
  ensure_git_commit
  local user
  user="$(api https://api.github.com/user | python3 -c 'import sys,json; print(json.load(sys.stdin)["login"])')"
  echo "==> GitHub 用户: $user"

  if ! api "https://api.github.com/repos/${user}/${REPO_NAME}" >/dev/null 2>&1; then
    echo "==> 创建仓库 ${user}/${REPO_NAME}"
    api -X POST https://api.github.com/user/repos \
      -d "{\"name\":\"${REPO_NAME}\",\"private\":$([ \"$VIS\" = private ] && echo true || echo false)}" >/dev/null
  fi

  local remote="https://x-access-token:${GITHUB_TOKEN}@github.com/${user}/${REPO_NAME}.git"
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$remote"
  else
    git remote add origin "$remote"
  fi
  echo "==> 推送代码"
  git push -u origin main

  echo "==> 触发 workflow"
  api -X POST "https://api.github.com/repos/${user}/${REPO_NAME}/actions/workflows/build-windows.yml/dispatches" \
    -d '{"ref":"main"}' >/dev/null

  echo "==> 等待运行完成（轮询中）"
  local run_id=""
  for _ in $(seq 1 120); do
    sleep 30
    run_id="$(api "https://api.github.com/repos/${user}/${REPO_NAME}/actions/workflows/build-windows.yml/runs?per_page=1" \
      | python3 -c 'import sys,json; r=json.load(sys.stdin)["workflow_runs"][0]; print(r["id"], r["status"], r["conclusion"] or "")' 2>/dev/null || echo "")"
    read -r id status conclusion <<< "$run_id" || true
    [ -n "${id:-}" ] || continue
    echo "  run $id status=$status conclusion=${conclusion:-pending}"
    if [ "$status" = "completed" ]; then
      if [ "$conclusion" != "success" ]; then
        echo "构建失败，请打开: https://github.com/${user}/${REPO_NAME}/actions"
        exit 1
      fi
      run_id="$id"
      break
    fi
  done
  [ -n "${run_id:-}" ] || { echo "等待超时"; exit 1; }

  echo "==> 下载产物"
  mkdir -p dist
  export _GH_USER="$user" _GH_REPO="$REPO_NAME" _GH_RUN="$run_id"
  GITHUB_TOKEN="$GITHUB_TOKEN" python3 <<'PY'
import json, os, subprocess, sys

raw = subprocess.check_output([
    "curl", "-fsSL",
    "-H", f"Authorization: Bearer {os.environ['GITHUB_TOKEN']}",
    "-H", "Accept: application/vnd.github+json",
    f"https://api.github.com/repos/{os.environ['_GH_USER']}/{os.environ['_GH_REPO']}/actions/runs/{os.environ['_GH_RUN']}/artifacts",
])
data = json.loads(raw)
url = next(a["archive_download_url"] for a in data["artifacts"] if a["name"] == "CWDZ-Windows-x64")
out = "dist/CWDZ-Windows-x64.zip"
subprocess.check_call([
    "curl", "-fsSL", "-o", out,
    "-H", f"Authorization: Bearer {os.environ['GITHUB_TOKEN']}",
    "-H", "Accept: application/vnd.github+json",
    url,
])
print(f"完成: {out}")
PY
}

# --- main ---
GH=""
for c in gh /tmp/gh_2.93.0_macOS_arm64/bin/gh /opt/homebrew/bin/gh; do
  if [ -x "$c" ] 2>/dev/null || command -v "$c" >/dev/null 2>&1; then
    GH="$(command -v "$c" 2>/dev/null || echo "$c")"
    break
  fi
done

if [ -n "$GH" ] && run_with_gh "$GH"; then
  exit 0
fi

run_with_token
