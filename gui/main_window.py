"""Main application window for CoreSync."""

import sys
from typing import Dict, Optional, Tuple
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QCloseEvent
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
from utils.system_info import get_system_summary
from monitoring.cpu_monitor import CPUMetricsSnapshot, CPUMonitorService
from gui.styles import DARK_STYLESHEET
from gui.components.header_bar import HeaderBar
from gui.dashboard import DashboardPage
from gui.core_monitor import CoreMonitorPage
from gui.real_system.process_view import RealProcessPage
from gui.real_system.stress_view import RealStressPage
from gui.virtual_lab.config_view import VirtualConfigPage
from gui.virtual_lab.monitor_view import VirtualMonitorPage
from gui.virtual_lab.scheduler_view import VirtualSchedulerPage
from gui.scheduler_view import SchedulerViewPage
from gui.data_parallelism import DataParallelismPage
from gui.task_parallelism import TaskParallelismPage
from gui.performance import PerformancePage
from gui.settings import SettingsPage

from engine.virtual_lab.virtual_cpu import VirtualCPU
from engine.virtual_lab.virtual_scheduler import VirtualScheduler


class MainWindow(QMainWindow):
    """CoreSync Master Workstation Window."""

    NAV_SECTIONS: Dict[int, Tuple[str, str]] = {
        0: ("Dashboard", "Workstation Overview & Activity Feed"),
        1: ("Core Monitor", "CPU Core Topology & Live Utilization"),
        2: ("Process Monitor", "Live OS Processes & CoreSync Workers"),
        3: ("Real CPU Stress", "Safety-Bounded Multi-Process Stress Generator"),
        4: ("Virtual CPU Config", "Topology Architect & Heterogeneous P/E Presets"),
        5: ("Virtual Core Monitor", "Simulated Core Matrix & Utilization Grid"),
        6: ("Virtual Scheduler", "FCFS, Priority & Round Robin Lab"),
        7: ("Data Parallelism", "Scatter / SIMD Compute / Gather Visualizer"),
        8: ("Task Parallelism", "Heterogeneous Workloads & DAG Dependency Manager"),
        9: ("Performance Analytics", "Speedup, Efficiency & Amdahl's Law"),
        10: ("Settings", "Process Timeouts, Engine & Probing Config"),
        11: ("Process Scheduler", "CPU Scheduling Algorithms & Gantt Timeline"),
    }

    def __init__(self, start_monitor: bool = True):
        super().__init__()
        self.summary = get_system_summary()
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE} (v{APP_VERSION})")
        self.resize(1300, 840)
        self.setMinimumSize(1024, 680)

        # Apply dark workstation styling
        self.setStyleSheet(DARK_STYLESHEET)

        # Setup Virtual Lab Engine Instances
        self.virtual_cpu = VirtualCPU()
        self.virtual_scheduler = VirtualScheduler(self.virtual_cpu)

        # Setup UI layouts and pages
        self._setup_ui()
        self._setup_status_bar()

        # Initialize and start CPU monitoring service in background QThread
        self.cpu_monitor: Optional[CPUMonitorService] = None
        if start_monitor:
            self._init_monitoring_service()

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
        self.header_bar.hardware_pill.setText(f"{self.summary.physical_cores}P / {self.summary.logical_cores}L Cores")
        content_layout.addWidget(self.header_bar)

        # Stacked Pages
        self.pages = QStackedWidget(content_container)
        content_layout.addWidget(self.pages, stretch=1)
        main_layout.addWidget(content_container, stretch=1)

        # 3. Instantiate & Add All Functional Pages
        # Real System
        self.page_dashboard = DashboardPage(self)
        self.page_core = CoreMonitorPage(self)
        self.page_real_proc = RealProcessPage(self)
        self.page_real_stress = RealStressPage(self)

        # Virtual Lab
        self.page_vconfig = VirtualConfigPage(self.virtual_cpu, self)
        self.page_vmonitor = VirtualMonitorPage(self.virtual_cpu, self)
        self.page_vscheduler = VirtualSchedulerPage(self.virtual_scheduler, self)

        # Concurrency & Analytics
        self.page_data = DataParallelismPage(self)
        self.page_task = TaskParallelismPage(self)
        self.page_performance = PerformancePage(self)
        self.page_settings = SettingsPage(self)
        self.page_process_scheduler = SchedulerViewPage(self)

        self.pages.addWidget(self.page_dashboard)    # Index 0
        self.pages.addWidget(self.page_core)         # Index 1
        self.pages.addWidget(self.page_real_proc)    # Index 2
        self.pages.addWidget(self.page_real_stress)  # Index 3
        self.pages.addWidget(self.page_vconfig)      # Index 4
        self.pages.addWidget(self.page_vmonitor)     # Index 5
        self.pages.addWidget(self.page_vscheduler)   # Index 6
        self.pages.addWidget(self.page_data)         # Index 7
        self.pages.addWidget(self.page_task)         # Index 8
        self.pages.addWidget(self.page_performance)  # Index 9
        self.pages.addWidget(self.page_settings)     # Index 10
        self.pages.addWidget(self.page_process_scheduler)  # Index 11

        # Connect Dashboard quick navigation requests
        self.page_dashboard.navigate_requested.connect(self.navigate_to_page)

        # Connect Virtual Lab inter-page signals
        self.page_vconfig.configuration_applied.connect(lambda cfg: self.page_vmonitor.rebuild_for_new_config())
        self.page_vconfig.configuration_applied.connect(lambda cfg: self.page_vscheduler._reset_scheduler())
        self.page_vscheduler.simulation_stepped.connect(self.page_vmonitor.refresh_display)

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
            ("OVERVIEW", [
                ("Dashboard", 0),
            ]),
            ("REAL SYSTEM", [
                ("Core Monitor", 1),
                ("Process Monitor", 2),
                ("Real CPU Stress", 3),
            ]),
            ("CPU SCHEDULING", [
                ("Process Scheduler", 11),
            ]),
            ("VIRTUAL LAB", [
                ("Virtual CPU Config", 4),
                ("Virtual Core Monitor", 5),
                ("Virtual Scheduler", 6),
            ]),
            ("PARALLEL PROCESSING", [
                ("Data Parallelism", 7),
                ("Task Parallelism", 8),
            ]),
            ("ANALYTICS & CONFIG", [
                ("Performance Analytics", 9),
                ("Settings", 10),
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

        self.sidebar_load_label = QLabel("Sampling CPU...", footer_frame)
        self.sidebar_load_label.setProperty("class", "muted")
        footer_layout.addWidget(self.sidebar_load_label)

        version_label = QLabel(f"CoreSync v{APP_VERSION}", footer_frame)
        version_label.setStyleSheet("color: #58a6ff; font-size: 10px; font-weight: 600;")
        footer_layout.addWidget(version_label)

        layout.addWidget(footer_frame)
        return sidebar

    def _init_monitoring_service(self) -> None:
        """Initialize single shared CPU monitoring service and connect consumer signals."""
        self.cpu_monitor = CPUMonitorService(refresh_interval_ms=1000, parent=self)
        self.cpu_monitor.metrics_updated.connect(self.page_dashboard.update_metrics)
        self.cpu_monitor.metrics_updated.connect(self.page_core.update_metrics)
        self.cpu_monitor.metrics_updated.connect(self.page_real_proc.update_metrics)
        self.cpu_monitor.metrics_updated.connect(self._on_metrics_updated)
        self.cpu_monitor.start()

    @Slot(CPUMetricsSnapshot)
    def _on_metrics_updated(self, snapshot: CPUMetricsSnapshot) -> None:
        """Handle metrics in main window status displays."""
        self.sidebar_load_label.setText(f"System Load: {snapshot.overall_percent:.1f}%")

    @Slot(int)
    def navigate_to_page(self, index: int) -> None:
        """Switch active page and update sidebar button and header bar."""
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)
            if index in self.nav_buttons and not self.nav_buttons[index].isChecked():
                self.nav_buttons[index].setChecked(True)

            section_name, subtitle = self.NAV_SECTIONS.get(index, ("CoreSync", ""))
            self.header_bar.update_header(section_name, subtitle)
            self.statusBar().showMessage(
                f"Viewing: {section_name} | {self.summary.physical_cores} Physical / {self.summary.logical_cores} Logical CPUs"
            )

    def _setup_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)
        status_bar.showMessage(
            f"Ready | {self.summary.cpu_model} ({self.summary.physical_cores} Physical / {self.summary.logical_cores} Logical CPUs)"
        )

    def shutdown(self) -> None:
        """Explicitly stop background services, simulation timers, and workers."""
        if hasattr(self, "page_real_stress"):
            self.page_real_stress.shutdown()
        if hasattr(self, "page_vscheduler"):
            self.page_vscheduler.shutdown()
        if hasattr(self, "page_data"):
            self.page_data.shutdown()
        if hasattr(self, "page_task"):
            self.page_task.shutdown()
        if getattr(self, "cpu_monitor", None) is not None and self.cpu_monitor.is_running():
            self.cpu_monitor.stop(timeout_ms=1000)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure background monitoring thread stops cleanly on application close."""
        self.shutdown()
        super().closeEvent(event)
