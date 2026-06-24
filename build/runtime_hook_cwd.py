"""PyInstaller 运行时：工作目录设为可执行文件所在目录。"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    os.chdir(Path(sys.executable).resolve().parent)
