from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cwdz.paths import (
    app_root,
    bundle_root,
    default_download_dir,
    default_reconcile_output_dir,
    default_voucher_output_dir,
    is_unusable_absolute,
    join_relative,
    resolve_under,
    sanitize_writable_path,
    writable_root,
)

PROJECT_ROOT = app_root()


def load_settings() -> dict[str, Any]:
    settings: dict[str, Any] = {}
    settings_path = bundle_root() / "config" / "settings.yaml"
    local_path = app_root() / "config" / "local.yaml"

    if settings_path.exists():
        with settings_path.open(encoding="utf-8") as f:
            settings = yaml.safe_load(f) or {}

    if local_path.exists():
        with local_path.open(encoding="utf-8") as f:
            local = yaml.safe_load(f) or {}
        settings = _deep_merge(settings, local)

    return settings


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_path(relative: str, *, platform: str = "tingsimple") -> Path:
    """可读写路径：相对路径基于数据根目录（Windows 为 D:/CWDZ）。"""
    text = (relative or "").strip()
    if not text:
        return default_download_dir(platform)
    if is_unusable_absolute(text):
        return default_download_dir(platform)
    path = Path(text)
    if path.is_absolute():
        return path
    return resolve_under(writable_root(), text)


def resolve_resource_path(relative: str) -> Path:
    """只读资源（凭证模板）：优先程序目录，其次 bundle（PyInstaller _MEIPASS）。"""
    text = (relative or "").strip()
    if not text:
        raise ValueError("资源路径为空")
    if is_unusable_absolute(text):
        raise FileNotFoundError(f"资源路径在当前系统不可用: {text}")
    path = Path(text)
    if path.is_absolute() and path.is_file():
        return path
    for root in (app_root(), bundle_root()):
        candidate = join_relative(root, text)
        if candidate.is_file():
            return candidate
    bundled = join_relative(bundle_root(), text)
    local = join_relative(app_root(), text)
    raise FileNotFoundError(
        f"资源文件不存在: {text}\n已查找:\n  {local}\n  {bundled}"
    )


# 供外部模块统一调用（sanitize_writable_path 定义在 cwdz.paths）
