"""中国工作日判断（含法定节假日与调休）。"""

from __future__ import annotations

from datetime import date

try:
    import chinese_calendar as _cc

    def is_workday(value: date) -> bool:
        return bool(_cc.is_workday(value))

except ImportError:  # pragma: no cover - 降级为仅排除周末
    def is_workday(value: date) -> bool:
        return value.weekday() < 5
