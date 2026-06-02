#!/usr/bin/env bash
# 生成分发压缩包（需先执行 build.sh 或 build.bat）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/dist"

if [ -d "财务对账工具.app" ]; then
  echo "==> 打包 macOS: CWDZ-macOS-arm64.zip"
  rm -f CWDZ-macOS-arm64.zip
  zip -qr CWDZ-macOS-arm64.zip "财务对账工具.app"
  ls -lh CWDZ-macOS-arm64.zip
fi

if [ -f "CWDZ/CWDZ.exe" ]; then
  echo "==> 打包 Windows: CWDZ-Windows-x64.zip"
  rm -f CWDZ-Windows-x64.zip
  zip -qr CWDZ-Windows-x64.zip CWDZ
  ls -lh CWDZ-Windows-x64.zip
fi

echo "完成。输出目录: $ROOT/dist/"
