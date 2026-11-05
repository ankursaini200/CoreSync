"""Main application window for CoreSync."""

import sys
from typing import Dict, Tuple
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from utils.config import APP_NAME, APP_SUBTITLE, APP_VERSION
from gui.styles import DARK_STYLESHEET
from gui.components.header_bar import HeaderBar
from gui.dashboard import DashboardPage
from gui.data_parallelism import DataParallelismPage
from gui.task_parallelism import TaskParallelismPage
from gui.core_monitor import CoreMonitorPage
from gui.scheduler_view import SchedulerViewPage
from gui.performance import PerformancePage
from gui.settings import SettingsPage


class MainWindow(QMainWindow):
    """CoreSync Master Workstation Window."""

    NAV_SECTIONS: Dict[int, Tuple[str, str]] = {
        0: ("Dashboard", "Workstation Overview & Activity Feed"),
        1: ("Data Parallelism", "Scatter / SIMD Compute / Gather Visualizer"),
        2: ("Task Parallelism", "Heterogeneous Workloads & DAG Dependency Manager"),
        3: ("Core Monitor", "CPU Core Topology & Affinity Controller"),
        4: ("Process Scheduler", "Educational Queue & Dispatch Simulator"),
        5: ("Performance Analytics", "Speedup, Efficiency & Amdahl's Law"),
        6: ("Settings", "Process Timeouts, Engine & Probing Config"),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE} (v{APP_VERSION})")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)

        # Apply dark workstation styling
        self.setStyleSheet(DARK_STYLESHEET)

        self._setup_ui()
        self._setup_status_bar()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Navigation
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # 2. Main Content Container (Header + Stacked Pages)
        content_container = QWidget(self)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Header Bar
        self.header_bar = HeaderBar(content_container)
        content_layout.addWidget(self.header_bar)

        # Stacked Pages
        self.pages = QStackedWidget(content_container)
        content_layout.addWidget(self.pages, stretch=1)
        main_layout.addWidget(content_container, stretch=1)

        # 3. Instantiate & Add All 7 Functional Pages
        self.page_dashboard = DashboardPage(self)
        self.page_data = DataParallelismPage(self)
        self.page_task = TaskParallelismPage(self)
        self.page_core = CoreMonitorPage(self)
        self.page_scheduler = SchedulerViewPage(self)
        self.page_performance = PerformancePage(self)
        self.page_settings = SettingsPage(self)

        self.pages.addWidget(self.page_dashboard)    # Index 0
        self.pages.addWidget(self.page_data)         # Index 1
        self.pages.addWidget(self.page_task)         # Index 2
        self.pages.addWidget(self.page_core)         # Index 3
        self.pages.addWidget(self.page_scheduler)    # Index 4
        self.pages.addWidget(self.page_performance)  # Index 5
        self.pages.addWidget(self.page_settings)     # Index 6

        # Connect Dashboard quick navigation requests
        self.page_dashboard.navigate_requested.connect(self.navigate_to_page)

    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget(self)
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(2)

        # Branding Header
        brand_label = QLabel(APP_NAME, sidebar)
        brand_label.setObjectName("appBrand")
        subtitle_label = QLabel(APP_SUBTITLE, sidebar)
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(brand_label)
        layout.addWidget(subtitle_label)

        # Navigation Button Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        # Categories & Navigation Items
        categories = [
            ("OVERVIEW", [("Dashboard", 0)]),
            ("PARALLEL PROCESSING", [
                ("Data Parallelism", 1),
                ("Task Parallelism", 2),
            ]),
            ("SYSTEM & SCHEDULING", [
                ("Core Monitor", 3),
                ("Process Scheduler", 4),
            ]),
            ("ANALYTICS & CONFIG", [
                ("Performance Analytics", 5),
                ("Settings", 6),
            ]),
        ]

        self.nav_buttons: Dict[int, QPushButton] = {}

        for cat_title, items in categories:
            cat_label = QLabel(cat_title, sidebar)
            cat_label.setProperty("class", "nav-category")
            layout.addWidget(cat_label)

            for item_title, idx in items:
                btn = QPushButton(item_title, sidebar)
                btn.setProperty("class", "nav-button")
                btn.setCheckable(True)
                if idx == 0:
                    btn.setChecked(True)
                self.nav_group.addButton(btn, idx)
                self.nav_buttons[idx] = btn
                layout.addWidget(btn)

        self.nav_group.idClicked.connect(self.navigate_to_page)
        layout.addStretch(1)

        # Sidebar Footer
        footer_frame = QFrame(sidebar)
        footer_frame.setProperty("class", "card")
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(4)

        ws_label = QLabel("Workstation Status", footer_frame)
        ws_label.setStyleSheet("font-weight: 600; font-size: 11px;")
        footer_layout.addWidget(ws_label)

        status_label = QLabel("Isolated Process Pool: Idle", footer_frame)
        status_label.setProperty("class", "muted")
        footer_layout.addWidget(status_label)

        version_label = QLabel(f"CoreSync v{APP_VERSION}", footer_frame)
        version_label.setStyleSheet("color: #58a6ff; font-size: 10px; font-weight: 600;")
        footer_layout.addWidget(version_label)

        layout.addWidget(footer_frame)
        return sidebar

    @Slot(int)
    def navigate_to_page(self, index: int) -> None:
        """Switch active page and update sidebar button and header bar."""
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)
            # Ensure corresponding button is checked
            if index in self.nav_buttons and not self.nav_buttons[index].isChecked():
                self.nav_buttons[index].setChecked(True)

            # Update header bar breadcrumb and title
            section_name, subtitle = self.NAV_SECTIONS.get(index, ("CoreSync", ""))
            self.header_bar.update_header(section_name, subtitle)

            self.statusBar().showMessage(f"Viewing: {section_name} | Multiprocessing spawn context active")

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready | Multiprocessing context: spawn | 14 Physical Cores / 20 Logical Threads")
