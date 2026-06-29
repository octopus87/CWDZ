# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：生成 macOS / Windows 可双击运行的目录分发包。"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# spec 在 build/ 下：SPECPATH 为 build 目录，上一级才是项目根
ROOT = Path(SPECPATH).resolve().parent
APP_NAME = "CWDZ"
DISPLAY_NAME = "财务对账工具"

datas = [
    (str(ROOT / "config" / "settings.yaml"), "config"),
    (str(ROOT / "config" / "local.yaml.example"), "config"),
    (str(ROOT / "config" / "voucher"), "config/voucher"),
]
# ddddocr 验证码模型（.onnx 不会随 hiddenimports 自动打入）
_ddddocr_datas = collect_data_files("ddddocr", includes=["*.onnx"])
if not _ddddocr_datas:
    import ddddocr

    _ddddocr_dir = Path(ddddocr.__file__).resolve().parent
    _ddddocr_datas = [(str(p), "ddddocr") for p in _ddddocr_dir.glob("*.onnx")]
datas += _ddddocr_datas

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "playwright",
    "playwright.sync_api",
    "httpx",
    "httpx._transports",
    "pandas",
    "openpyxl",
    "xlrd",
    "yaml",
    "ddddocr",
    "onnxruntime",
    "PIL",
    "cv2",
    "numpy",
    "chinese_calendar",
    "chinese_calendar.constants",
    "chinese_calendar.utils",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[
        str(ROOT / "build" / "runtime_hook_cwd.py"),
        str(ROOT / "build" / "runtime_hook_playwright.py"),
    ],
    excludes=["tkinter", "matplotlib", "scipy"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{DISPLAY_NAME}.app",
        icon=None,
        bundle_identifier="com.sunsea.cwdz",
        info_plist={
            "CFBundleName": DISPLAY_NAME,
            "CFBundleDisplayName": DISPLAY_NAME,
            "CFBundleVersion": "0.1.0",
            "CFBundleShortVersionString": "0.1.0",
            "NSHighResolutionCapable": True,
        },
    )
