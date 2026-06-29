"""应用根目录与打包后路径解析。"""

from __future__ import annotations

import re
import shutil
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


def join_relative(base: Path, relative: str) -> Path:
    """拼接相对路径，兼容 settings 中的 / 与 Windows 的 \\。"""
    text = relative.strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = text.strip("/")
    if not text:
        return base
    return base.joinpath(*text.split("/"))


def is_windows() -> bool:
    return sys.platform == "win32"


def writable_root() -> Path:
    """可读写数据根目录：Windows 默认 D:/CWDZ，macOS / 开发环境为程序目录。"""
    if is_windows():
        root = Path("D:/CWDZ")
        try:
            root.mkdir(parents=True, exist_ok=True)
            return root
        except OSError:
            pass
    return app_root()


def is_unusable_absolute(path_text: str) -> bool:
    """当前系统无法使用的绝对路径（如在 Windows 上的 Mac 路径）。"""
    if not path_text:
        return True
    text = path_text.strip().replace("\\", "/")
    if is_windows():
        if re.match(r"^[A-Za-z]:/", text):
            return False
        if text.startswith("/Users/") or text.startswith("/home/"):
            return True
        if text.startswith("/") and not text.startswith("//"):
            return True
    return False


def resolve_under(base: Path, path_text: str) -> Path:
    """解析配置路径：相对路径拼到 base；不可用绝对路径回退到 base 下相对部分。"""
    text = (path_text or "").strip()
    if not text:
        return base
    path = Path(text)
    if path.is_absolute():
        if not is_unusable_absolute(text) and path.exists():
            return path
        if is_unusable_absolute(text):
            # /Users/octopus/Downloads/科拓 -> data/downloads/keytop 等由调用方处理
            return base
        return path
    return join_relative(base, text)


def default_download_dir(platform: str = "tingsimple") -> Path:
    root = writable_root()
    if platform == "keytop":
        return root / "data" / "downloads" / "keytop"
    return root / "data" / "downloads"


def default_voucher_output_dir(platform: str = "tingsimple") -> Path:
    root = writable_root()
    if platform == "keytop":
        return root / "data" / "output" / "vouchers" / "keytop"
    return root / "data" / "output" / "vouchers" / "tingsimple"


def ensure_voucher_assets() -> None:
    """首次运行时将 bundle 内凭证模板释放到程序目录（Windows 下与 exe 同目录）。"""
    src_root = bundle_root() / "config" / "voucher"
    if not src_root.is_dir():
        return
    dst_root = app_root() / "config" / "voucher"
    for src in src_root.rglob("*.xlsx"):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        if dst.exists() and dst.stat().st_size == src.stat().st_size:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def ensure_runtime_dirs() -> None:
    """确保 data 子目录存在（Windows 在 D:/CWDZ，其余在程序目录）。"""
    data_root = writable_root()
    for rel in (
        "data",
        "data/.auth",
        "data/downloads",
        "data/downloads/keytop",
        "data/output",
        "data/output/vouchers",
        "data/output/vouchers/tingsimple",
        "data/output/vouchers/keytop",
    ):
        (data_root / rel).mkdir(parents=True, exist_ok=True)
    for rel in ("config", "config/voucher/tingsimple", "config/voucher/keytop"):
        (app_root() / rel).mkdir(parents=True, exist_ok=True)
    ensure_voucher_assets()
