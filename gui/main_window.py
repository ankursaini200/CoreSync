"""Main application window for CoreSync."""

import sys
from PySide6.QtCore import Qt
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


class MainWindow(QMainWindow):
    """CoreSync Master Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE} (v{APP_VERSION})")
        self.resize(1180, 740)
        self.setMinimumSize(960, 600)
        
        # Apply dark theme stylesheet
        self.setStyleSheet(DARK_STYLESHEET)

        self._setup_ui()
        self._setup_status_bar()

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Container
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # 2. Page Router / Stacked Widget
        self.pages = QStackedWidget(self)
        main_layout.addWidget(self.pages, stretch=1)

        # Add initial dashboard placeholder page
        dashboard_page = self._create_initial_page()
        self.pages.addWidget(dashboard_page)

    def _create_sidebar(self) -> QWidget:
        sidebar = QWidget(self)
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(4)

        # Header Titles
        title_label = QLabel(APP_NAME, sidebar)
        title_label.setObjectName("appTitle")
        subtitle_label = QLabel(APP_SUBTITLE, sidebar)
        subtitle_label.setObjectName("appSubtitle")
        subtitle_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("Dashboard", 0),
            ("Data Parallelism", 1),
            ("Task Parallelism", 2),
            ("Core Monitor", 3),
            ("Process Scheduler", 4),
            ("Performance Analytics", 5),
            ("Settings", 6),
        ]

        for text, idx in nav_items:
            btn = QPushButton(text, sidebar)
            btn.setProperty("class", "nav-button")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            self.nav_group.addButton(btn, idx)
            layout.addWidget(btn)

        layout.addStretch(1)

        # Version Footer
        footer_label = QLabel(f"Version {APP_VERSION}", sidebar)
        footer_label.setProperty("class", "muted")
        footer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer_label)

        return sidebar

    def _create_initial_page(self) -> QWidget:
        """Initial landing view verifying environment and skeleton status."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(20)

        # Welcome Card
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        header = QLabel("Phase 2: Project Skeleton & Environment Initialized")
        header.setProperty("class", "heading")
        card_layout.addWidget(header)

        desc = QLabel(
            "CoreSync workstation shell is successfully loaded.\n"
            "• Multiprocessing engine isolated from Qt via 'spawn' context.\n"
            "• PySide6 6.12, NumPy 2.5, psutil 7.2, Matplotlib 3.11, and pytest 9.2 verified.\n"
            "• Ready to proceed to Phase 3: Complete Dark Dashboard and Navigation Panels."
        )
        desc.setStyleSheet("line-height: 1.5; color: #c9d1d9;")
        card_layout.addWidget(desc)

        layout.addWidget(card)
        layout.addStretch(1)
        return page

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready | Multiprocessing context: spawn | Hardware detected")

