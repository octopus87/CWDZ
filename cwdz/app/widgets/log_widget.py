from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class LogWidget(QWidget):
    """底部活动日志区（与设计稿高度一致）。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("活动日志")
        title.setObjectName("CardTitle")
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("GhostButton")
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._text = QPlainTextEdit()
        self._text.setObjectName("LogView")
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("等待任务开始…")
        self._text.setMinimumHeight(108)
        self._text.setMaximumHeight(132)
        layout.addWidget(self._text)

    def append(self, message: str) -> None:
        self._text.appendPlainText(message)

    def clear(self) -> None:
        self._text.clear()
