from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from cwdz.paths import app_root, bundle_root

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


def resolve_path(relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute():
        return path
    return app_root() / path
