"""界面输入项持久化（QSettings）。"""

from __future__ import annotations

from PySide6.QtCore import QDate, QSettings, Qt
from PySide6.QtWidgets import QDateEdit, QLineEdit

_SETTINGS_ORG = "CWDZ"
_SETTINGS_APP = "财务对账工具"


class InputMemory:
    def __init__(self) -> None:
        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)

    def get_text(self, key: str, default: str = "") -> str:
        value = self._settings.value(key, default)
        if value is None:
            return default
        text = str(value).strip()
        return text if text else default

    def set_text(self, key: str, value: str) -> None:
        self._settings.setValue(key, value.strip())

    def load_line_edit(self, field: QLineEdit, key: str, default: str = "") -> None:
        saved = self.get_text(key, default)
        if saved:
            field.setText(saved)

    def save_line_edit(self, field: QLineEdit, key: str) -> None:
        self.set_text(key, field.text())

    def load_date_edit(self, field: QDateEdit, key: str, default: QDate) -> None:
        text = self.get_text(key)
        if text:
            parsed = QDate.fromString(text, Qt.DateFormat.ISODate)
            if parsed.isValid():
                field.setDate(parsed)
                return
        field.setDate(default)

    def save_date_edit(self, field: QDateEdit, key: str) -> None:
        if field.date().isValid():
            self.set_text(key, field.date().toString(Qt.DateFormat.ISODate))

    def sync(self) -> None:
        self._settings.sync()


_memory: InputMemory | None = None


def input_memory() -> InputMemory:
    global _memory
    if _memory is None:
        _memory = InputMemory()
    return _memory


def default_tingsimple_dates() -> tuple[QDate, QDate]:
    """停简单下载查询默认：上月2日 ~ 当月1日。"""
    today = QDate.currentDate()
    prev_month = today.addMonths(-1)
    start = QDate(prev_month.year(), prev_month.month(), 2)
    end = QDate(today.year(), today.month(), 1)
    return start, end


def default_keytop_dates() -> tuple[QDate, QDate]:
    """科拓下载查询默认：上月3日 ~ 当月3日。"""
    today = QDate.currentDate()
    prev_month = today.addMonths(-1)
    start = QDate(prev_month.year(), prev_month.month(), 3)
    end = QDate(today.year(), today.month(), 3)
    return start, end


def apply_default_query_dates(start: QDateEdit, end: QDateEdit) -> None:
    """停简单查询日期按当月规则重置，不读历史记忆。"""
    s, e = default_tingsimple_dates()
    start.setDate(s)
    end.setDate(e)


def apply_default_keytop_query_dates(start: QDateEdit, end: QDateEdit) -> None:
    """科拓查询日期按当月规则重置，不读历史记忆。"""
    s, e = default_keytop_dates()
    start.setDate(s)
    end.setDate(e)


def default_voucher_period() -> str:
    """凭证账期默认上个月（当月做上月账），格式 yyyy-MM。"""
    today = QDate.currentDate()
    prev = today.addMonths(-1)
    return f"{prev.year():04d}-{prev.month():02d}"
