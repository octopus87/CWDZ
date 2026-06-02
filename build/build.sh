#!/usr/bin/env bash
# macOS 打包：生成 财务对账工具.app 与 dist/CWDZ/ 目录
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 准备虚拟环境"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt
python -m playwright install chromium

echo "==> PyInstaller 打包"
pyinstaller build/cwdz.spec --noconfirm --clean

DIST_DIR="$ROOT/dist/CWDZ"
APP_PATH="$ROOT/dist/财务对账工具.app"

# 浏览器：复制到分发目录（供 runtime_hook 使用）
PW_CACHE="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/Library/Caches/ms-playwright}"
if [ -d "$PW_CACHE" ]; then
  echo "==> 复制 Playwright Chromium ($(du -sh "$PW_CACHE" | cut -f1))"
  rm -rf "$DIST_DIR/ms-playwright"
  cp -R "$PW_CACHE" "$DIST_DIR/ms-playwright"
  if [ -d "$APP_PATH/Contents/MacOS" ]; then
    rm -rf "$APP_PATH/Contents/MacOS/ms-playwright"
    cp -R "$PW_CACHE" "$APP_PATH/Contents/MacOS/ms-playwright"
  fi
else
  echo "警告: 未找到 Playwright 浏览器缓存 $PW_CACHE，请在本机执行: playwright install chromium"
fi

echo "==> 初始化 data / config 目录"
for TARGET in "$DIST_DIR" "$APP_PATH/Contents/MacOS"; do
  [ -d "$TARGET" ] || continue
  mkdir -p "$TARGET/data/.auth" "$TARGET/data/downloads" "$TARGET/data/output/vouchers"
  [ -f "$TARGET/config/local.yaml.example" ] || cp "$ROOT/config/local.yaml.example" "$TARGET/config/" 2>/dev/null || true
done

echo ""
echo "打包完成:"
echo "  macOS 应用: dist/财务对账工具.app  （推荐双击）"
echo "  目录版入口: dist/CWDZ/CWDZ"
echo ""
echo "首次运行可在 dist/CWDZ/config/ 下复制 local.yaml.example 为 local.yaml 修改账号配置。"
