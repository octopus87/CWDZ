"""卡片式布局组件。"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


class Card(QFrame):
    """白色圆角卡片容器。"""

    def __init__(self, title: str = "", hint: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 18, 20, 20)
        self._layout.setSpacing(10)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("CardTitle")
            self._layout.addWidget(title_label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("CardHint")
            hint_label.setWordWrap(True)
            self._layout.addWidget(hint_label)

        self._body = QWidget()
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(10)
        self._layout.addWidget(self._body)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._body_layout
