from __future__ import annotations

import logging
import traceback
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cwdz.app.keytop_panel import KeytopDownloadPanel
from cwdz.app.widgets.apple_ui import (
    COMPACT_BUTTON_HEIGHT,
    SPACING_COLUMNS,
    SPACING_LOGIN_COL,
    ActionBar,
    GroupedSection,
    ListRow,
    PageHeader,
    make_bar_line_edit,
    make_column_layout,
    make_inline_date_edit,
    make_inline_line_edit,
    make_inline_slot,
    make_page_layout,
    make_path_field,
    make_path_trailing,
    make_trailing_bar,
)
from cwdz.config import load_settings, resolve_path
from cwdz.crawler.keytop.batch import download_batch_workbook
from cwdz.crawler.keytop.client import KeytopClient
from cwdz.crawler.session import TingsimpleClient
from cwdz.processor.parser import merge_tingsimple_exports, parse_tingsimple_export
from cwdz.processor.reconcile import reconcile, save_reconciled
from cwdz.processor.validator import validate
from cwdz.voucher.generator import generate_voucher


class ClickableLabel(QLabel):
    clicked = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class Worker(QThread):
    finished_ok = Signal(str)
    finished_err = Signal(str)
    progress = Signal(str)
    captcha_ready = Signal(bytes)
    captcha_text = Signal(str)
    qr_ready = Signal(bytes, str)

    def __init__(self, task: str, **kwargs) -> None:
        super().__init__()
        self.task = task
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            if self.task == "fetch_captcha":
                result = TingsimpleClient().fetch_captcha(
                    refresh=self.kwargs.get("refresh", False),
                    on_progress=self.progress.emit,
                )
                self.captcha_ready.emit(result.image)
                if result.text:
                    self.captcha_text.emit(result.text)
                self.finished_ok.emit("captcha")
            elif self.task == "download":
                path = TingsimpleClient().fetch_reconciliation(
                    self.kwargs["start_date"],
                    self.kwargs["end_date"],
                    username=self.kwargs["username"],
                    password=self.kwargs["password"],
                    captcha=self.kwargs["captcha"],
                    download_dir=self.kwargs.get("download_dir"),
                    on_progress=self.progress.emit,
                )
                self.finished_ok.emit(str(path))
            elif self.task == "keytop_qr":
                with KeytopClient() as client:
                    qr = client.fetch_qr_code()
                self.qr_ready.emit(qr.image, qr.uuid)
                self.finished_ok.emit(qr.uuid)
            elif self.task == "keytop_login":
                with KeytopClient() as client:
                    client.wait_for_login(
                        self.kwargs["uuid"],
                        on_progress=self.progress.emit,
                    )
                    profile = client.fetch_user_profile(on_progress=self.progress.emit)
                self.finished_ok.emit(
                    f"{profile.lot_name}|{profile.user_name}|{profile.current_lot_id}"
                )
            elif self.task == "keytop_batch_download":
                with KeytopClient() as client:
                    result = download_batch_workbook(
                        client,
                        self.kwargs["workbook_path"],
                        self.kwargs["start_date"],
                        self.kwargs["end_date"],
                        output_dir=self.kwargs.get("download_dir"),
                        on_progress=self.progress.emit,
                    )
                summary = (
                    f"{result.workbook_path}|"
                    f"ok={result.success_count}|"
                    f"no_perm={result.no_permission_count}|"
                    f"err={result.error_count}|"
                    f"total={len(result.sheets)}"
                )
                self.finished_ok.emit(summary)
            elif self.task == "process":
                input_dir = Path(self.kwargs["input_dir"])
                merge_result = merge_tingsimple_exports(input_dir)
                for msg in [
                    f"合并 {len(merge_result.processed_files)} 个文件",
                    *[f"  ✓ {name}" for name in merge_result.processed_files],
                ]:
                    self.progress.emit(msg)
                for name in merge_result.skipped_files:
                    self.progress.emit(f"  - 跳过: {name}")

                df = merge_result.dataframe
                errors = validate(df)
                if errors:
                    raise ValueError("\n".join(errors))
                result = reconcile(df)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                out = save_reconciled(result, input_dir / f"对账结果_合并_{stamp}.xlsx")
                self.finished_ok.emit(str(out))
            elif self.task == "voucher":
                input_path = Path(self.kwargs["input_path"])
                period = self.kwargs.get("period", "")
                df = parse_tingsimple_export(input_path)
                settings = load_settings()
                template = resolve_path(settings["voucher"]["template_path"])
                output_dir = resolve_path(settings["voucher"]["output_dir"])
                out = generate_voucher(df, template, output_dir, period=period or None)
                self.finished_ok.emit(str(out))
            else:
                raise ValueError(f"未知任务: {self.task}")
        except Exception as exc:
            self.finished_err.emit(f"{exc}\n{traceback.format_exc()}")


class DownloadTab(QWidget):
    log_message = Signal(str)
    download_dir_changed = Signal(str)

    _PLATFORM_HEADER: dict[str, tuple[str, str]] = {
        "停简单": ("下载对账", "登录停简单商户后台，按账期导出对账明细。"),
        "科拓": ("下载对账", "科拓扫码登录后批量下载工作簿。"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._worker: Worker | None = None
        self._has_captcha = False
        self._keytop_uuid = ""
        self._keytop_logged_in = False
        self._keytop_qr_loaded = False
        self._pending_qr_image: bytes | None = None
        self._current_platform = "停简单"

        title, subtitle = self._PLATFORM_HEADER["停简单"]
        self._page_header = PageHeader(title, subtitle, compact=True)

        self._tingsimple_page = self._build_tingsimple_page()
        self._keytop_panel = KeytopDownloadPanel()
        self._keytop_panel.fetch_qr_requested.connect(self._fetch_keytop_qr)
        self._keytop_panel.batch_download_requested.connect(self._on_keytop_batch_download)

        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._stack.addWidget(self._tingsimple_page)
        self._stack.addWidget(self._keytop_panel)

        layout = make_page_layout(self)
        layout.addWidget(self._page_header)
        layout.addWidget(self._stack)

    def set_platform(self, platform: str) -> None:
        self._current_platform = platform
        title, subtitle = self._PLATFORM_HEADER.get(platform, self._PLATFORM_HEADER["停简单"])
        self._page_header.set_content(title, subtitle)
        self._stop_worker()
        is_keytop = platform == "科拓"
        self._stack.setCurrentWidget(self._keytop_panel if is_keytop else self._tingsimple_page)
        if is_keytop:
            self._keytop_logged_in = False
            with KeytopClient() as client:
                if client.is_logged_in():
                    self._keytop_logged_in = True
                    profile = client.saved_profile()
                    self._keytop_panel.set_user_profile(profile.lot_name, profile.user_name)
                    self._keytop_panel.set_logged_in(True)
                    return
            if self._pending_qr_image and self._keytop_uuid:
                self._apply_keytop_qr(self._pending_qr_image)
                self._ensure_keytop_login_poll()
            else:
                self._keytop_uuid = ""
                self._keytop_qr_loaded = False
                QTimer.singleShot(0, self._fetch_keytop_qr)
        else:
            QTimer.singleShot(0, self._fetch_captcha)

    def activate(self, platform: str) -> None:
        """下载页签被选中时，补加载当前平台所需的验证码/二维码。"""
        self._current_platform = platform
        if platform == "科拓":
            self._stack.setCurrentWidget(self._keytop_panel)
            if self._keytop_logged_in:
                return
            if self._pending_qr_image:
                self._apply_keytop_qr(self._pending_qr_image)
                self._ensure_keytop_login_poll()
                return
            if not self._keytop_qr_loaded and not self._is_worker_running(
                "keytop_qr", "keytop_login"
            ):
                self._fetch_keytop_qr()
        elif not self._has_captcha and not self._is_worker_running("fetch_captcha"):
            self._stack.setCurrentWidget(self._tingsimple_page)
            self._fetch_captcha()

    def _is_worker_running(self, *tasks: str) -> bool:
        return bool(
            self._worker
            and self._worker.isRunning()
            and self._worker.task in tasks
        )

    def _apply_keytop_qr(self, image: bytes) -> None:
        self._keytop_panel.show_qr(image)
        self._keytop_panel.set_busy(False)
        self._keytop_qr_loaded = True

    def _ensure_keytop_login_poll(self) -> None:
        if self._current_platform != "科拓" or self._keytop_logged_in or not self._keytop_uuid:
            return
        if self._is_worker_running("keytop_login"):
            return
        self._start_keytop_login(self._keytop_uuid)

    def _stop_worker(self) -> None:
        worker = self._worker
        if worker is None:
            return
        for signal in (
            worker.progress,
            worker.finished_ok,
            worker.finished_err,
            worker.captcha_ready,
            worker.captcha_text,
            worker.qr_ready,
        ):
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                pass
        if worker.isRunning():
            worker.terminate()
            worker.wait(3000)
        self._worker = None
        self._set_busy(False)
        self._keytop_panel.set_busy(False)

    def _build_tingsimple_page(self) -> QWidget:
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        settings = load_settings()
        ts = settings.get("tingsimple", {})

        self._username = make_inline_line_edit(ts.get("username", ""), "商户账号")
        self._password = make_inline_line_edit(ts.get("password", ""), "密码", password=True)

        today = QDate.currentDate()
        prev_month = today.addMonths(-1)
        self._start = make_inline_date_edit()
        self._end = make_inline_date_edit()
        self._start.setDate(QDate(prev_month.year(), prev_month.month(), 2))
        self._end.setDate(QDate(today.year(), today.month(), 1))

        self._captcha_image = ClickableLabel("点击获取验证码")
        self._captcha_image.setObjectName("QrPlaceholder")
        self._captcha_image.setFixedSize(132, 48)
        self._captcha_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._captcha_image.setToolTip("点击图片刷新验证码")
        self._captcha_image.clicked.connect(self._fetch_captcha)
        self._fetch_btn = QPushButton("获取验证码")
        self._fetch_btn.setObjectName("CompactButton")
        self._fetch_btn.setFixedHeight(COMPACT_BUTTON_HEIGHT)
        self._fetch_btn.clicked.connect(self._fetch_captcha)

        self._captcha_input = make_bar_line_edit(
            "", "自动识别或手动输入", full_width=True
        )
        self._captcha_input.setMaxLength(8)

        default_dir = str(resolve_path(ts.get("download_dir", "/Users/octopus/Downloads")))
        self._download_dir = make_path_field(default_dir, "选择目录…")
        browse_btn = QPushButton("浏览…")
        browse_btn.setObjectName("CompactButton")
        browse_btn.clicked.connect(self._browse_download_dir)
        dir_trailing = make_path_trailing(self._download_dir, browse_btn)

        date_section = GroupedSection("账期")
        date_section.add_row(
            ListRow("开始日期", trailing=make_inline_slot(self._start), trailing_expand=True)
        )
        date_section.add_row(
            ListRow("结束日期", trailing=make_inline_slot(self._end), trailing_expand=True, last=True)
        )

        login_section = GroupedSection("账号")
        login_section.add_row(
            ListRow("用户名", trailing=make_inline_slot(self._username), trailing_expand=True)
        )
        login_section.add_row(
            ListRow("密码", trailing=make_inline_slot(self._password), trailing_expand=True, last=True)
        )

        captcha_section = GroupedSection("验证码")
        captcha_section.add_row(
            ListRow(
                "图形码",
                trailing=make_inline_slot(self._captcha_image),
                tall=True,
                trailing_expand=True,
            )
        )
        captcha_section.add_row(
            ListRow(
                "识别结果",
                trailing=make_trailing_bar((self._captcha_input, 1), (self._fetch_btn, 0)),
                trailing_expand=True,
                last=True,
            )
        )

        path_section = GroupedSection("下载")
        path_section.add_row(
            ListRow("保存目录", trailing=dir_trailing, trailing_expand=True, last=True)
        )

        left_wrap = QWidget()
        left_col = make_column_layout(left_wrap)
        left_col.addWidget(date_section)
        left_col.addWidget(login_section)

        right_wrap = QWidget()
        right_col = make_column_layout(right_wrap)
        right_col.addWidget(captcha_section)

        self._btn = QPushButton("登录并下载对账数据")
        self._btn.setObjectName("PrimaryButton")
        self._btn.clicked.connect(self._on_download)
        action_bar = ActionBar()
        action_bar.set_primary(self._btn)

        columns = QHBoxLayout()
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(SPACING_COLUMNS)
        columns.addWidget(left_wrap, stretch=1)
        columns.addWidget(right_wrap, stretch=1)

        page_layout = make_page_layout(page)
        page_layout.addLayout(columns)
        page_layout.addWidget(path_section)
        page_layout.addWidget(action_bar)
        page_layout.addStretch()
        return page

    def _set_busy(self, busy: bool) -> None:
        self._fetch_btn.setEnabled(not busy)
        self._captcha_image.setEnabled(not busy)
        self._btn.setEnabled(not busy)

    def _browse_download_dir(self) -> None:
        current = self._download_dir.text().strip()
        start_dir = current if current and Path(current).exists() else str(Path.home() / "Downloads")
        path = QFileDialog.getExistingDirectory(self, "选择下载目录", start_dir)
        if path:
            self._download_dir.setText(path)

    def _fetch_captcha(self) -> None:
        if self._current_platform != "停简单":
            return
        if self._worker and self._worker.isRunning():
            if self._worker.task == "fetch_captcha":
                return
            self._stop_worker()
        refresh = self._has_captcha
        self._set_busy(True)
        self.log_message.emit("刷新验证码…" if refresh else "获取验证码…")
        self._worker = Worker("fetch_captcha", refresh=refresh)
        self._worker.progress.connect(self.log_message.emit)
        self._worker.captcha_ready.connect(self._on_captcha_ready)
        self._worker.captcha_text.connect(self._on_captcha_text)
        self._worker.finished_ok.connect(lambda _: self._set_busy(False))
        self._worker.finished_err.connect(self._on_captcha_err)
        self._worker.start()

    def _on_captcha_ready(self, image: bytes) -> None:
        if self._current_platform != "停简单":
            return
        pixmap = QPixmap()
        pixmap.loadFromData(image)
        scaled = pixmap.scaled(
            self._captcha_image.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._captcha_image.setPixmap(scaled)
        self._captcha_image.setText("")
        self._captcha_image.setObjectName("QrImage")
        self._captcha_image.setStyleSheet("")
        self._has_captcha = True
        self._fetch_btn.setText("刷新验证码")
        self._captcha_input.clear()
        self.log_message.emit("✓ 验证码已加载")

    def _on_captcha_text(self, text: str) -> None:
        if self._current_platform != "停简单":
            return
        self._captcha_input.setText(text)
        self.log_message.emit(f"✓ 验证码已自动识别: {text}")

    def _on_captcha_err(self, msg: str) -> None:
        if self._current_platform != "停简单":
            return
        self._set_busy(False)
        self.log_message.emit("✗ 获取验证码失败")
        QMessageBox.critical(self, "错误", msg)

    def _fetch_keytop_qr(self) -> None:
        if self._current_platform != "科拓":
            return
        if self._worker and self._worker.isRunning():
            self._stop_worker()
        self._keytop_panel.set_busy(True)
        self._keytop_panel.set_qr_loading(True)
        self._keytop_logged_in = False
        self._keytop_panel.set_logged_in(False)
        self._keytop_panel.set_user_profile("", "")
        self._keytop_uuid = ""
        self._keytop_qr_loaded = False
        self._pending_qr_image = None
        self.log_message.emit("刷新科拓登录二维码…")
        self._worker = Worker("keytop_qr")
        self._worker.progress.connect(self.log_message.emit)
        self._worker.qr_ready.connect(self._on_keytop_qr_ready)
        self._worker.finished_ok.connect(self._start_keytop_login)
        self._worker.finished_err.connect(self._on_keytop_qr_err)
        self._worker.start()

    def _on_keytop_qr_ready(self, image: bytes, uuid: str) -> None:
        self._keytop_uuid = uuid
        self._pending_qr_image = image
        self._keytop_qr_loaded = True
        if self._current_platform != "科拓":
            return
        self._apply_keytop_qr(image)
        self.log_message.emit("✓ 科拓二维码已加载，请扫码")

    def _start_keytop_login(self, uuid: str) -> None:
        def start() -> None:
            if self._current_platform != "科拓":
                return
            if self._worker and self._worker.isRunning():
                self._stop_worker()
            self._worker = Worker("keytop_login", uuid=uuid)
            self._worker.progress.connect(self.log_message.emit)
            self._worker.finished_ok.connect(self._on_keytop_login_ok)
            self._worker.finished_err.connect(self._on_keytop_login_err)
            self._worker.start()

        QTimer.singleShot(0, start)

    def _on_keytop_login_ok(self, payload: str) -> None:
        if self._current_platform != "科拓":
            return
        self._keytop_logged_in = True
        self._keytop_panel.set_busy(False)
        lot_name, user_name, _ = (payload.split("|") + ["", ""])[:3]
        self._keytop_panel.set_user_profile(lot_name, user_name)
        self._keytop_panel.set_logged_in(True)
        if lot_name or user_name:
            self.log_message.emit(f"✓ 科拓登录成功：{lot_name} / {user_name}")
        else:
            self.log_message.emit("✓ 科拓登录成功")

    def _on_keytop_login_err(self, msg: str) -> None:
        if self._current_platform != "科拓":
            return
        self._keytop_panel.set_busy(False)
        self.log_message.emit("✗ 科拓登录失败")
        QMessageBox.critical(self, "错误", msg)

    def _on_keytop_qr_err(self, msg: str) -> None:
        if self._current_platform != "科拓":
            return
        self._keytop_panel.set_busy(False)
        self.log_message.emit("✗ 获取二维码失败")
        QMessageBox.critical(self, "错误", msg)

    def _on_keytop_batch_download(self) -> None:
        if not self._keytop_logged_in:
            QMessageBox.warning(self, "提示", "请先扫码登录科拓平台")
            return
        if self._worker and self._worker.isRunning():
            return

        workbook_path = self._keytop_panel.get_task_file()
        if not workbook_path:
            QMessageBox.warning(self, "提示", "请选择批量任务 Excel 文件")
            return
        if not Path(workbook_path).exists():
            QMessageBox.warning(self, "提示", f"任务文件不存在:\n{workbook_path}")
            return

        download_dir = self._keytop_panel.get_download_dir()
        if not download_dir:
            QMessageBox.warning(self, "提示", "请选择下载路径")
            return

        start, end = self._keytop_panel.get_date_range()
        self._keytop_panel.set_busy(True)
        self.log_message.emit(f"科拓批量下载: {start} ~ {end} → {download_dir}")
        self._worker = Worker(
            "keytop_batch_download",
            start_date=start,
            end_date=end,
            workbook_path=workbook_path,
            download_dir=download_dir,
        )
        self._worker.progress.connect(self.log_message.emit)
        self._worker.finished_ok.connect(self._on_keytop_batch_download_ok)
        self._worker.finished_err.connect(self._on_keytop_batch_download_err)
        self._worker.start()

    def _on_keytop_batch_download_ok(self, payload: str) -> None:
        self._keytop_panel.set_busy(False)
        self._keytop_panel.set_logged_in(True)
        download_dir = self._keytop_panel.get_download_dir()
        if download_dir:
            self.download_dir_changed.emit(download_dir)
        parts = payload.split("|")
        path = parts[0] if parts else payload
        summary = ""
        if len(parts) >= 5:
            summary = (
                f"成功 {parts[1].split('=')[1]} 个页签，"
                f"无权限 {parts[2].split('=')[1]} 个，"
                f"失败 {parts[3].split('=')[1]} 个，"
                f"共 {parts[4].split('=')[1]} 个页签"
            )
        self.log_message.emit(f"✓ 科拓批量任务完成: {path}")
        QMessageBox.information(
            self,
            "完成",
            f"批量任务已完成，新文件已保存至:\n{path}\n\n{summary}",
        )

    def _on_keytop_batch_download_err(self, msg: str) -> None:
        self._keytop_panel.set_busy(False)
        if self._keytop_logged_in:
            self._keytop_panel.set_logged_in(True)
        self.log_message.emit("✗ 科拓批量下载失败")
        QMessageBox.critical(self, "错误", msg)

    def _on_download(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        username = self._username.text().strip()
        password = self._password.text()
        captcha = self._captcha_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "提示", "请填写用户名和密码")
            return
        if not self._has_captcha:
            QMessageBox.warning(self, "提示", "请先获取验证码")
            return
        if not captcha:
            QMessageBox.warning(self, "提示", "验证码为空，请点击图片或按钮刷新")
            return

        download_dir = self._download_dir.text().strip()
        if not download_dir:
            QMessageBox.warning(self, "提示", "请选择下载路径")
            return

        start = self._start.date().toString("yyyy-MM-dd")
        end = self._end.date().toString("yyyy-MM-dd")
        self._set_busy(True)
        self.log_message.emit(f"开始登录并下载: {start} ~ {end} → {download_dir}")

        self._worker = Worker(
            "download",
            start_date=start,
            end_date=end,
            username=username,
            password=password,
            captcha=captcha,
            download_dir=download_dir,
        )
        self._worker.progress.connect(self.log_message.emit)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def _on_ok(self, path: str) -> None:
        self._set_busy(False)
        self._has_captcha = False
        self._captcha_image.setPixmap(QPixmap())
        self._captcha_image.setText("点击获取验证码")
        self._captcha_image.setObjectName("QrPlaceholder")
        self._captcha_image.setStyleSheet("")
        self._fetch_btn.setText("获取验证码")
        download_dir = self._download_dir.text().strip()
        if download_dir:
            self.download_dir_changed.emit(download_dir)
        self.log_message.emit(f"✓ 下载成功: {path}")
        QMessageBox.information(
            self,
            "完成",
            f"对账文件已下载到:\n{download_dir or path}\n\n可在「整理数据」中合并。",
        )

    def _on_err(self, msg: str) -> None:
        self._set_busy(False)
        self.log_message.emit("✗ 下载失败")
        QMessageBox.critical(self, "错误", msg)


class ProcessTab(QWidget):
    log_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._worker: Worker | None = None
        self._platform = "停简单"
        settings = load_settings()
        ts = settings.get("tingsimple", {})
        kt = settings.get("keytop", {})
        self._default_dirs = {
            "停简单": str(resolve_path(ts.get("download_dir", "/Users/octopus/Downloads"))),
            "科拓": str(resolve_path(kt.get("download_dir", "/Users/octopus/Downloads/科拓"))),
        }

        self._dir_path = make_path_field(self._default_dirs["停简单"], "选择目录…")

        browse = QPushButton("浏览…")
        browse.setObjectName("CompactButton")
        browse.clicked.connect(self._browse)

        dir_trailing = make_path_trailing(self._dir_path, browse)

        source_section = GroupedSection("数据源")
        source_section.add_row(
            ListRow("对账源目录", trailing=dir_trailing, trailing_expand=True, last=True)
        )

        self._btn = QPushButton("整理对账数据")
        self._btn.setObjectName("PrimaryButton")
        self._btn.clicked.connect(self._on_process)
        action_bar = ActionBar()
        action_bar.set_primary(self._btn)

        layout = make_page_layout(self)
        layout.addWidget(
            PageHeader("整理数据", "合并目录内 Excel 并输出对账结果。", compact=True)
        )
        layout.addWidget(source_section)
        layout.addWidget(action_bar)
        layout.addStretch()

    def set_platform(self, platform: str) -> None:
        self._platform = platform
        if not self._dir_path.text().strip() or self._dir_path.text() in self._default_dirs.values():
            self._dir_path.setText(self._default_dirs.get(platform, self._default_dirs["停简单"]))

    def set_source_dir(self, path: str) -> None:
        if path.strip():
            self._dir_path.setText(path.strip())

    def _browse(self) -> None:
        current = self._dir_path.text().strip()
        start_dir = current if current and Path(current).exists() else str(Path.home() / "Downloads")
        path = QFileDialog.getExistingDirectory(self, "选择对账源目录", start_dir)
        if path:
            self._dir_path.setText(path)

    def _on_process(self) -> None:
        path = self._dir_path.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请先选择对账源目录")
            return
        if not Path(path).is_dir():
            QMessageBox.warning(self, "提示", "源目录不存在，请重新选择")
            return
        if self._worker and self._worker.isRunning():
            return

        self._btn.setEnabled(False)
        self.log_message.emit(f"开始整理目录: {path}")
        self._worker = Worker("process", input_dir=path)
        self._worker.progress.connect(self.log_message.emit)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def _on_ok(self, path: str) -> None:
        self._btn.setEnabled(True)
        self.log_message.emit(f"✓ 整理完成: {path}")
        QMessageBox.information(self, "完成", f"对账结果已保存:\n{path}")

    def _on_err(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.log_message.emit("✗ 整理失败")
        QMessageBox.critical(self, "错误", msg)


class VoucherTab(QWidget):
    log_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self._worker: Worker | None = None
        self._platform = "停简单"
        self._file_path = make_path_field("", "选择 Excel…")
        self._period = make_inline_line_edit("", "2026-05")

        browse = QPushButton("浏览…")
        browse.setObjectName("CompactButton")
        browse.clicked.connect(self._browse)

        file_trailing = make_path_trailing(self._file_path, browse)

        input_section = GroupedSection("输入")
        input_section.add_row(
            ListRow("对账结果文件", trailing=file_trailing, trailing_expand=True)
        )
        input_section.add_row(
            ListRow("账期", trailing=make_inline_slot(self._period), trailing_expand=True, last=True)
        )

        self._btn = QPushButton("生成 Excel 凭证")
        self._btn.setObjectName("PrimaryButton")
        self._btn.clicked.connect(self._on_generate)
        action_bar = ActionBar()
        action_bar.set_primary(self._btn)

        layout = make_page_layout(self)
        layout.addWidget(
            PageHeader("生成凭证", "基于对账表生成 Excel 凭证。", compact=True)
        )
        layout.addWidget(input_section)
        layout.addWidget(action_bar)
        layout.addStretch()

    def set_platform(self, platform: str) -> None:
        self._platform = platform

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择对账结果", "", "Excel (*.xlsx *.xls)"
        )
        if path:
            self._file_path.setText(path)

    def _on_generate(self) -> None:
        path = self._file_path.text().strip()
        if not path:
            QMessageBox.warning(self, "提示", "请先选择对账结果文件")
            return
        if self._worker and self._worker.isRunning():
            return

        self._btn.setEnabled(False)
        period = self._period.text().strip()
        self.log_message.emit(f"开始生成凭证: {path}")
        self._worker = Worker("voucher", input_path=path, period=period)
        self._worker.finished_ok.connect(self._on_ok)
        self._worker.finished_err.connect(self._on_err)
        self._worker.start()

    def _on_ok(self, path: str) -> None:
        self._btn.setEnabled(True)
        self.log_message.emit(f"✓ 凭证已生成: {path}")
        QMessageBox.information(self, "完成", f"凭证文件:\n{path}")

    def _on_err(self, msg: str) -> None:
        self._btn.setEnabled(True)
        self.log_message.emit("✗ 凭证生成失败")
        QMessageBox.critical(self, "错误", msg)
