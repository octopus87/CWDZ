"""应用根目录与打包后路径解析。"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """可读写根目录：开发时为项目根；打包后为可执行文件所在目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    """只读资源根目录（PyInstaller _MEIPASS），开发时同 app_root。"""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return app_root()


def ensure_runtime_dirs() -> None:
    """确保 data 子目录存在（打包分发后可写）。"""
    root = app_root()
    for rel in (
        "data",
        "data/.auth",
        "data/downloads",
        "data/output",
        "data/output/vouchers",
        "config",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
