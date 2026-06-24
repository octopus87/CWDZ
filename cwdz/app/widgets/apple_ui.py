"""Apple HIG 风格布局组件（分组列表、侧栏、分段控件）。"""

from __future__ import annotations

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCalendarWidget,
    QDateEdit,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# 与 canvases/cwdz-apple-ui-design.canvas.tsx 对齐的间距 token
SPACING_ROOT = 10
SPACING_BODY = 14
SPACING_MAIN_COLUMN = 8
SPACING_PAGE = 6
SPACING_SECTION = 4
PAGE_HEADER_COMPACT_SPACING = 2
SPACING_COLUMNS = 16
SPACING_LIST_ROW = 12
SPACING_TRAILING_BAR = 8
SPACING_PLATFORM = 8
SPACING_ACTION_TOP = 8
PRIMARY_BUTTON_HEIGHT = 28
COMPACT_BUTTON_HEIGHT = 24
SPACING_SIDEBAR_STEPS = 4
SPACING_LOGIN_COL = 6

LIST_ROW_HEIGHT = 36
LIST_ROW_TALL_HEIGHT = 52
LIST_ROW_LABEL_WIDTH = 148
LIST_ROW_MARGIN_H = 16
CONTENT_PANEL_MARGINS = (16, 14, 16, 14)
INLINE_FIELD_WIDTH = 140


def make_page_layout(parent: QWidget | None = None) -> QVBoxLayout:
    """页面主纵向布局：块间距统一，内容顶对齐。"""
    if parent is not None:
        layout = QVBoxLayout(parent)
    else:
        layout = QVBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING_PAGE)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    return layout


def make_column_layout(parent: QWidget | None = None) -> QVBoxLayout:
    """分栏内分组纵向布局：块间距 8px。"""
    return make_page_layout(parent)


def make_inline_line_edit(
    text: str = "",
    placeholder: str = "",
    *,
    password: bool = False,
) -> QLineEdit:
    field = QLineEdit(text)
    field.setObjectName("InlineField")
    field.setPlaceholderText(placeholder)
    field.setFixedHeight(24)
    field.setMinimumWidth(72)
    field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    if password:
        field.setEchoMode(QLineEdit.EchoMode.Password)
    return field


def make_inline_date_edit() -> QDateEdit:
    field = QDateEdit()
    field.setObjectName("InlineField")
    field.setDisplayFormat("yyyy/M/d")
    field.setFixedHeight(24)
    field.setMinimumWidth(100)
    field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    field.setCalendarPopup(True)
    field.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
    return field


def open_date_calendar(date_edit: QDateEdit) -> None:
    """弹出日历选择当前日期控件值。"""
    dialog = QDialog(date_edit.window())
    dialog.setWindowTitle("选择日期")
    dialog.setWindowFlags(
        Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
    )
    calendar = QCalendarWidget(dialog)
    calendar.setGridVisible(True)
    calendar.setSelectedDate(date_edit.date())

    def pick(day: QDate) -> None:
        if day.isValid():
            date_edit.setDate(day)
        dialog.accept()

    calendar.clicked.connect(pick)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.addWidget(calendar)
    anchor = date_edit.mapToGlobal(date_edit.rect().bottomLeft())
    dialog.move(anchor)
    dialog.exec()


def make_date_trailing(date_edit: QDateEdit) -> QWidget:
    """日期输入 + 日历按钮。"""
    calendar_btn = QPushButton("日历")
    calendar_btn.setObjectName("CompactButton")
    calendar_btn.setFixedHeight(COMPACT_BUTTON_HEIGHT)
    calendar_btn.setMinimumWidth(52)
    calendar_btn.setToolTip("打开日历选择日期")
    calendar_btn.clicked.connect(lambda: open_date_calendar(date_edit))
    date_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return make_trailing_bar((date_edit, 1), (calendar_btn, 0))


def make_path_field(text: str = "", placeholder: str = "") -> QLineEdit:
    field = QLineEdit(text)
    field.setObjectName("PathField")
    field.setPlaceholderText(placeholder)
    field.setFixedHeight(24)
    field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return field


def wrap_trailing(widget: QWidget, width: int = INLINE_FIELD_WIDTH) -> QWidget:
    """将控件右对齐包裹（固定槽宽，用于非拉伸行）。"""
    wrap = QWidget()
    wrap.setFixedWidth(width)
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.addStretch()
    row.addWidget(widget)
    return wrap


def make_inline_slot(widget: QWidget) -> QWidget:
    """列表行标签后的内联控件槽：占满剩余宽度，左对齐。"""
    if hasattr(widget, "setFixedHeight") and not isinstance(widget, QLabel):
        widget.setFixedHeight(24)
    wrap = QWidget()
    wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(widget, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    return wrap


def make_bar_line_edit(
    text: str = "",
    placeholder: str = "",
    *,
    min_width: int = 80,
    full_width: bool = False,
) -> QLineEdit:
    """用于 trailing bar 内可伸缩的输入框（如验证码识别结果行）。"""
    field = QLineEdit(text)
    field.setObjectName("InlineField")
    field.setPlaceholderText(placeholder)
    field.setMinimumWidth(min_width)
    if not full_width:
        field.setMaximumWidth(160)
    field.setFixedHeight(24)
    field.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return field


def make_trailing_bar(
    *items: tuple[QWidget, int],
    min_width: int = 0,
) -> QWidget:
    """横向工具条：左侧控件可拉伸，末尾按钮贴右（如路径 + 浏览）。"""
    wrap = QWidget()
    wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    if min_width > 0:
        wrap.setMinimumWidth(min_width)
    row = QHBoxLayout(wrap)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(SPACING_TRAILING_BAR)
    for widget, stretch in items:
        row.addWidget(widget, stretch)
    return wrap


def make_path_trailing(path_field: QLineEdit, browse_btn: QPushButton) -> QWidget:
    """路径行：文本框占满标签与浏览按钮之间的区域，浏览贴最右。"""
    path_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    browse_btn.setFixedHeight(COMPACT_BUTTON_HEIGHT)
    browse_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    return make_trailing_bar((path_field, 1), (browse_btn, 0))


class PageHeader(QWidget):
    """页面大标题 + 副标题。"""

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        *,
        compact: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PageHeaderCompact" if compact else "PageHeader")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PAGE_HEADER_COMPACT_SPACING if compact else 6)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._title_label = QLabel(title)
        self._title_label.setObjectName("PageTitle")
        layout.addWidget(self._title_label)
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setObjectName("PageSubtitle")
        self._subtitle_label.setWordWrap(True)
        layout.addWidget(self._subtitle_label)
        self._subtitle_label.setVisible(bool(subtitle))

    def set_content(self, title: str, subtitle: str = "") -> None:
        self._title_label.setText(title)
        self._subtitle_label.setText(subtitle)
        self._subtitle_label.setVisible(bool(subtitle))


class ListRow(QFrame):
    """分组列表行：固定宽左标签列 + 控件列纵向对齐。"""

    def __init__(
        self,
        label: str,
        trailing: QWidget | None = None,
        subtitle: str = "",
        last: bool = False,
        tall: bool = False,
        trailing_expand: bool = True,
        label_adjacent: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ListRow")
        if tall:
            self.setFixedHeight(LIST_ROW_TALL_HEIGHT)
        else:
            self.setFixedHeight(LIST_ROW_HEIGHT)
        if last:
            self.setProperty("lastRow", True)
        if tall:
            self.setProperty("tallRow", True)

        row = QHBoxLayout(self)
        row.setContentsMargins(LIST_ROW_MARGIN_H, 0, LIST_ROW_MARGIN_H, 0)
        row.setSpacing(SPACING_LIST_ROW)

        label_wrap = QWidget()
        label_wrap.setFixedWidth(LIST_ROW_LABEL_WIDTH)
        label_wrap.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        if subtitle:
            label_col = QVBoxLayout(label_wrap)
            label_col.setContentsMargins(0, 0, 0, 0)
            label_col.setSpacing(0)
            title = QLabel(label)
            title.setObjectName("ListRowLabel")
            title.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )
            label_col.addWidget(title)
            hint = QLabel(subtitle)
            hint.setObjectName("ListRowSubtitle")
            hint.setAlignment(Qt.AlignmentFlag.AlignLeft)
            hint.setWordWrap(True)
            label_col.addWidget(hint)
        else:
            label_row = QHBoxLayout(label_wrap)
            label_row.setContentsMargins(0, 0, 0, 0)
            title = QLabel(label)
            title.setObjectName("ListRowLabel")
            title.setAlignment(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            )
            label_row.addWidget(title, 1, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(label_wrap, 0, Qt.AlignmentFlag.AlignVCenter)
        if trailing is not None:
            if label_adjacent:
                stretch = 1 if trailing_expand else 0
                row.addWidget(
                    trailing,
                    stretch=stretch,
                    alignment=Qt.AlignmentFlag.AlignVCenter,
                )
            else:
                row.addStretch()
                stretch = 1 if trailing_expand else 0
                row.addWidget(
                    trailing,
                    stretch=stretch,
                    alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                )


class GroupedSection(QWidget):
    """带 section 标题与 footnote 的分组列表容器。"""

    def __init__(
        self,
        title: str = "",
        footer: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACING_SECTION)
        if title:
            section = QLabel(title)
            section.setObjectName("SectionTitle")
            outer.addWidget(section)
        self._list = QFrame()
        self._list.setObjectName("GroupedList")
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        outer.addWidget(self._list)
        if footer:
            foot = QLabel(footer)
            foot.setObjectName("SectionFooter")
            foot.setWordWrap(True)
            outer.addWidget(foot)

    def add_row(self, row: ListRow) -> None:
        self._list_layout.addWidget(row)


class SegmentedControl(QWidget):
    """双项分段控件（设计稿：圆角轨道 + 选中项白底）。"""

    selectionChanged = Signal(str)

    TRACK_WIDTH = 196
    TRACK_HEIGHT = 28

    def __init__(self, options: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SegmentedControl")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._options = options
        self._buttons: list[QPushButton] = []

        track = QFrame()
        track.setObjectName("SegmentedTrack")
        track.setFixedSize(self.TRACK_WIDTH, self.TRACK_HEIGHT)
        layout = QHBoxLayout(track)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for i, text in enumerate(options):
            btn = QPushButton(text)
            btn.setObjectName("SegmentButton")
            btn.setCheckable(True)
            btn.setFlat(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda _checked=False, t=text: self._on_click(t))
            self._group.addButton(btn, i)
            self._buttons.append(btn)
            layout.addWidget(btn, stretch=1)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(track)
        if options:
            self.set_current(options[0])

    def _on_click(self, text: str) -> None:
        self.set_current(text)
        self.selectionChanged.emit(text)

    def set_current(self, text: str) -> None:
        for btn in self._buttons:
            selected = btn.text() == text
            btn.setChecked(selected)
            btn.setProperty("selected", selected)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def current_text(self) -> str:
        for btn in self._buttons:
            if btn.isChecked():
                return btn.text()
        return self._options[0] if self._options else ""


class PlatformBar(QWidget):
    """平台切换行：白卡片外、主内容区右上右对齐（与设计稿一致）。"""

    selectionChanged = Signal(str)

    def __init__(
        self,
        options: list[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PlatformBar")
        self.setFixedHeight(SegmentedControl.TRACK_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        _l, _t, right_inset, _b = CONTENT_PANEL_MARGINS
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, right_inset, 0)
        row.setSpacing(SPACING_PLATFORM)
        row.addStretch()

        label = QLabel("平台")
        label.setObjectName("PlatformLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(label, 0, Qt.AlignmentFlag.AlignVCenter)

        self._segment = SegmentedControl(options)
        self._segment.selectionChanged.connect(self.selectionChanged.emit)
        row.addWidget(self._segment, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_current(self, text: str) -> None:
        self._segment.set_current(text)

    def current_text(self) -> str:
        return self._segment.current_text()


class SidebarStep(QFrame):
    """侧栏步骤项：主标题 + 副说明两行排版。"""

    clicked = Signal()

    def __init__(
        self,
        index: int,
        title: str,
        detail: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarStep")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._index = index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self._title = QLabel(f"{index + 1}. {title}")
        self._title.setObjectName("SidebarStepTitle")
        self._detail = QLabel(detail)
        self._detail.setObjectName("SidebarStepDetail")
        layout.addWidget(self._title)
        layout.addWidget(self._detail)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        for label in (self._title, self._detail):
            label.setProperty("selected", selected)
            label.style().unpolish(label)
            label.style().polish(label)
        self.style().unpolish(self)
        self.style().polish(self)


class WorkflowSidebar(QWidget):
    """左侧工作流程导航。"""

    stepChanged = Signal(int)

    STEPS: list[tuple[str, str]] = [
        ("下载对账", "从平台拉取对账 Excel"),
        ("整理数据", "合并、校验与对账"),
        ("生成凭证", "导出财务凭证表"),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._steps: list[SidebarStep] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(SPACING_SIDEBAR_STEPS)

        caption = QLabel("工作流程")
        caption.setObjectName("SidebarCaption")
        layout.addWidget(caption)

        for i, (title, detail) in enumerate(self.STEPS):
            step = SidebarStep(i, title, detail)
            step.clicked.connect(lambda idx=i: self._select(idx))
            self._steps.append(step)
            layout.addWidget(step)

        layout.addStretch()
        self.set_step(0)

    def _select(self, index: int) -> None:
        self.set_step(index)
        self.stepChanged.emit(index)

    def set_step(self, index: int) -> None:
        for i, step in enumerate(self._steps):
            step.set_selected(i == index)


class ActionBar(QFrame):
    """主操作区：顶部分隔线 + 右对齐主按钮。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActionBar")
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, SPACING_ACTION_TOP, 0, 0)
        self._row.setSpacing(SPACING_TRAILING_BAR)

    def set_primary(self, button: QPushButton) -> None:
        button.setFixedHeight(PRIMARY_BUTTON_HEIGHT)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._row.addStretch()
        self._row.addWidget(button, 0, Qt.AlignmentFlag.AlignRight)


class ContentPanel(QFrame):
    """主内容 elevated 面板。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
        self._layout = QVBoxLayout(self)
        l, t, r, b = CONTENT_PANEL_MARGINS
        self._layout.setContentsMargins(l, t, r, b)
        self._layout.setSpacing(0)

    @property
    def body_layout(self) -> QVBoxLayout:
        return self._layout
