"""PyInstaller 运行时：指向打包目录内的 Chromium。"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    browsers = Path(sys.executable).resolve().parent / "ms-playwright"
    if browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
