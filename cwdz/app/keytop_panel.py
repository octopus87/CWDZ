"""科拓平台下载面板（单屏、无滚动）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cwdz.app.widgets.apple_ui import (
    COMPACT_BUTTON_HEIGHT,
    SPACING_COLUMNS,
    SPACING_LOGIN_COL,
    ActionBar,
    GroupedSection,
    ListRow,
    make_column_layout,
    make_inline_date_edit,
    make_inline_slot,
    make_page_layout,
    make_path_field,
    make_path_trailing,
)
from cwdz.config import load_settings, resolve_path

QR_SIZE = 116


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class KeytopDownloadPanel(QWidget):
    log_message = Signal(str)
    fetch_qr_requested = Signal()
    batch_download_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._logged_in = False
        settings = load_settings()
        kt = settings.get("keytop", {})

        root_outer = make_page_layout(self)

        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(SPACING_COLUMNS)

        login_col = QVBoxLayout()
        login_col.setSpacing(SPACING_LOGIN_COL)
        login_col.setContentsMargins(0, 0, 0, 0)

        self._qr_image = ClickableLabel("点击获取二维码")
        self._qr_image.setObjectName("QrPlaceholder")
        self._qr_image.setFixedSize(QR_SIZE, QR_SIZE)
        self._qr_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_image.setToolTip("点击二维码刷新")
        self._qr_image.clicked.connect(self.fetch_qr_requested.emit)

        self._fetch_qr_btn = QPushButton("获取二维码")
        self._fetch_qr_btn.setObjectName("CompactButton")
        self._fetch_qr_btn.setFixedHeight(COMPACT_BUTTON_HEIGHT)
        self._fetch_qr_btn.clicked.connect(self.fetch_qr_requested.emit)

        self._login_status = QLabel("请扫码并在手机上确认登录")
        self._login_status.setObjectName("StatusMuted")
        self._login_status.setWordWrap(True)

        self._login_detail = QWidget()
        detail_layout = QVBoxLayout(self._login_detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(SPACING_LOGIN_COL)
        detail_layout.addWidget(self._qr_image, alignment=Qt.AlignmentFlag.AlignHCenter)
        detail_layout.addWidget(self._fetch_qr_btn)
        detail_layout.addWidget(self._login_status)

        self._login_summary = QWidget()
        summary_layout = QVBoxLayout(self._login_summary)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(SPACING_LOGIN_COL)
        self._login_ok = QLabel("已登录")
        self._login_ok.setObjectName("StatusOk")
        self._user_info = QLabel("")
        self._user_info.setObjectName("UserBadge")
        self._user_info.setWordWrap(True)
        self._relogin_btn = QPushButton("切换账号")
        self._relogin_btn.setObjectName("GhostButton")
        self._relogin_btn.clicked.connect(self.fetch_qr_requested.emit)
        summary_layout.addWidget(self._login_ok)
        summary_layout.addWidget(self._user_info)
        summary_layout.addWidget(self._relogin_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self._login_summary.hide()

        login_col.addWidget(self._login_detail)
        login_col.addWidget(self._login_summary)
        login_col.addStretch()

        login_wrap = QWidget()
        login_wrap.setFixedWidth(148)
        login_wrap.setLayout(login_col)

        form_wrap = QWidget()
        form_col = make_column_layout(form_wrap)

        today = QDate.currentDate()
        prev_month = today.addMonths(-1)
        self._start = make_inline_date_edit()
        self._end = make_inline_date_edit()
        self._start.setDate(QDate(prev_month.year(), prev_month.month(), 2))
        self._end.setDate(QDate(today.year(), today.month(), 1))

        date_section = GroupedSection("批量下载")
        date_section.add_row(
            ListRow("开始日期", trailing=make_inline_slot(self._start), trailing_expand=True)
        )
        date_section.add_row(
            ListRow("结束日期", trailing=make_inline_slot(self._end), trailing_expand=True, last=True)
        )

        default_task = "/Users/octopus/Downloads/科拓代扣4.29-6.1.xlsx"
        self._task_file = make_path_field(default_task)
        task_browse_btn = QPushButton("浏览…")
        task_browse_btn.setObjectName("CompactButton")
        task_browse_btn.clicked.connect(self._browse_task_file)
        task_trailing = make_path_trailing(self._task_file, task_browse_btn)

        task_section = GroupedSection("任务")
        task_section.add_row(
            ListRow("批量任务文件", trailing=task_trailing, trailing_expand=True, last=True)
        )

        default_dir = str(resolve_path(kt.get("download_dir", "/Users/octopus/Downloads/科拓")))
        self._download_dir = make_path_field(default_dir)
        browse_btn = QPushButton("浏览…")
        browse_btn.setObjectName("CompactButton")
        browse_btn.clicked.connect(self._browse_download_dir)
        out_trailing = make_path_trailing(self._download_dir, browse_btn)

        output_section = GroupedSection("输出")
        output_section.add_row(
            ListRow("保存目录", trailing=out_trailing, trailing_expand=True, last=True)
        )

        self._batch_btn = QPushButton("批量下载并生成新文件")
        self._batch_btn.setObjectName("PrimaryButton")
        self._batch_btn.clicked.connect(self.batch_download_requested.emit)

        form_col.addWidget(date_section)
        form_col.addWidget(task_section)
        form_col.addWidget(output_section)

        body = QWidget()
        body.setLayout(root)
        root.addWidget(login_wrap)
        root.addWidget(form_wrap, stretch=1)

        action_bar = ActionBar()
        action_bar.set_primary(self._batch_btn)
        root_outer.addWidget(body)
        root_outer.addWidget(action_bar)
        root_outer.addStretch()

    def set_busy(self, busy: bool) -> None:
        enabled = not busy and self._logged_in
        self._batch_btn.setEnabled(enabled and bool(self.get_task_file()))
        self._fetch_qr_btn.setEnabled(not busy)
        self._relogin_btn.setEnabled(not busy)

    def set_qr_loading(self, loading: bool) -> None:
        if loading:
            self._login_status.setText("正在获取二维码…")
        elif not self._logged_in:
            self._login_status.setText("请扫码并在手机上确认登录")

    def show_qr(self, image: bytes) -> None:
        pixmap = QPixmap()
        pixmap.loadFromData(image)
        scaled = pixmap.scaled(
            self._qr_image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._qr_image.setPixmap(scaled)
        self._qr_image.setText("")
        self._qr_image.setObjectName("QrImage")
        self._qr_image.setStyleSheet("")
        self._fetch_qr_btn.setText("刷新二维码")
        if not self._logged_in:
            self._login_status.setText("请扫码并在手机上确认登录")

    def set_login_status(self, text: str) -> None:
        self._login_status.setText(text)

    def set_user_profile(self, lot_name: str = "", user_name: str = "") -> None:
        parts = []
        if lot_name:
            parts.append(f"车场：{lot_name}")
        if user_name:
            parts.append(f"用户：{user_name}")
        self._user_info.setText("\n".join(parts) if parts else "")

    def set_logged_in(self, logged_in: bool) -> None:
        self._logged_in = logged_in
        self._batch_btn.setEnabled(logged_in and bool(self.get_task_file()))
        self._login_detail.setVisible(not logged_in)
        self._login_summary.setVisible(logged_in)
        if logged_in:
            self._login_ok.setText("已登录，可以批量下载")
        else:
            self._user_info.clear()
            self._login_status.setText("请使用「停车场云助手 APP」扫码登录")

    def get_download_dir(self) -> str:
        return self._download_dir.text().strip()

    def get_task_file(self) -> str:
        return self._task_file.text().strip()

    def get_date_range(self) -> tuple[str, str]:
        start = self._start.date().toString("yyyy-MM-dd")
        end = self._end.date().toString("yyyy-MM-dd")
        return start, end

    def _browse_download_dir(self) -> None:
        current = self._download_dir.text().strip()
        start_dir = current if current and Path(current).exists() else str(Path.home() / "Downloads")
        path = QFileDialog.getExistingDirectory(self, "选择下载目录", start_dir)
        if path:
            self._download_dir.setText(path)

    def _browse_task_file(self) -> None:
        current = self._task_file.text().strip()
        if current and Path(current).exists():
            start_dir = str(Path(current).parent)
            start_file = current
        else:
            start_dir = str(Path.home() / "Downloads")
            start_file = ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择批量任务 Excel",
            start_file or start_dir,
            "Excel 文件 (*.xlsx)",
        )
        if path:
            self._task_file.setText(path)
            if self._logged_in:
                self._batch_btn.setEnabled(True)
