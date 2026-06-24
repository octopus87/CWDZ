from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cwdz import __version__
from cwdz.app.input_memory import input_memory
from cwdz.app.tabs import DownloadTab, ProcessTab, VoucherTab
from cwdz.app.theme import apply_app_theme
from cwdz.paths import ensure_runtime_dirs
from cwdz.app.widgets.apple_ui import (
    SPACING_BODY,
    SPACING_MAIN_COLUMN,
    SPACING_ROOT,
    ContentPanel,
    PlatformBar,
    WorkflowSidebar,
)
from cwdz.app.widgets.log_widget import LogWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"财务对账工具 v{__version__}")
        self.setMinimumSize(920, 720)
        self.resize(1000, 760)

        central = QWidget()
        central.setObjectName("CentralRoot")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(SPACING_ROOT)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title = QLabel("财务对账工具")
        title.setObjectName("AppTitle")
        badge = QLabel(f"v{__version__}")
        badge.setObjectName("VersionBadge")
        title_row.addWidget(title)
        title_row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()
        layout.addLayout(title_row)

        subtitle = QLabel("停简单 / 科拓对账下载与整理")
        subtitle.setObjectName("AppSubtitle")
        layout.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(SPACING_BODY)
        self._sidebar = WorkflowSidebar()
        self._sidebar.stepChanged.connect(self._on_step_changed)

        main_col = QVBoxLayout()
        main_col.setSpacing(SPACING_MAIN_COLUMN)
        main_col.setContentsMargins(0, 0, 0, 0)

        self._platform = PlatformBar(["停简单", "科拓"])
        self._platform.selectionChanged.connect(self._on_platform_changed)
        main_col.addWidget(self._platform)

        self._content_panel = ContentPanel()
        self._stack = QStackedWidget()
        self._stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._download_tab = DownloadTab()
        self._process_tab = ProcessTab()
        self._voucher_tab = VoucherTab()
        self._stack.addWidget(self._download_tab)
        self._stack.addWidget(self._process_tab)
        self._stack.addWidget(self._voucher_tab)
        self._content_panel.body_layout.addWidget(self._stack)
        main_col.addWidget(self._content_panel, stretch=1)

        main_wrap = QWidget()
        main_wrap.setLayout(main_col)

        body.addWidget(self._sidebar)
        body.addWidget(main_wrap, stretch=1)
        layout.addLayout(body, stretch=1)

        self._log = LogWidget()
        layout.addWidget(self._log, stretch=0)

        self._download_tab.log_message.connect(self._log.append)
        self._process_tab.log_message.connect(self._log.append)
        self._voucher_tab.log_message.connect(self._log.append)
        self._download_tab.download_dir_changed.connect(self._process_tab.set_source_dir)
        self._download_tab.download_file_changed.connect(self._process_tab.set_source_file)
        self._process_tab.process_file_changed.connect(self._voucher_tab.set_source_file)

        self._download_tab.set_platform(self._platform.current_text())
        self._stack.setCurrentIndex(0)

        QApplication.instance().aboutToQuit.connect(self._save_input_memory)

    def _save_input_memory(self) -> None:
        self._download_tab.save_input_memory()
        self._process_tab.save_input_memory()
        self._voucher_tab.save_input_memory()
        input_memory().sync()

    def _on_step_changed(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if index == 0:
            self._download_tab.activate(self._platform.current_text())
        elif index == 2:
            last = self._process_tab.last_output_path()
            if last:
                self._voucher_tab.set_source_file(last)

    def _on_platform_changed(self, platform: str) -> None:
        self._download_tab.set_platform(platform)
        self._process_tab.set_platform(platform)
        self._voucher_tab.set_platform(platform)
        last = self._process_tab.last_output_path()
        if last:
            self._voucher_tab.set_source_file(last)

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def run() -> None:
    ensure_runtime_dirs()
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("CWDZ")
    apply_app_theme(app, "apple")
    app.aboutToQuit.connect(_shutdown)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _shutdown() -> None:
    from cwdz.crawler.browser_executor import shutdown_browser_executor

    shutdown_browser_executor()
