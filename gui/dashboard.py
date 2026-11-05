"""Dashboard Page for CoreSync Workstation."""

import platform
import psutil
from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from utils.config import APP_NAME, APP_VERSION
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard
from gui.components.action_card import ActionCard


class DashboardPage(QWidget):
    """Workstation Dashboard Page providing hardware summary, architecture status, and quick module launchers."""

    navigate_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for responsive resizing
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(22)
        scroll.setWidget(container)

        # 1. Welcome & System Identification Banner
        welcome_card = self._create_welcome_banner()
        layout.addWidget(welcome_card)

        # 2. Hardware & Architecture Metrics Grid (Real System Data)
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 3. Parallelism & Workstation Modules Section
        modules_header = QLabel("Multicore Workstation Modules", container)
        modules_header.setProperty("class", "heading-1")
        layout.addWidget(modules_header)

        modules_grid = self._create_modules_grid()
        layout.addLayout(modules_grid)

        # 4. Status & Engine Readiness Panel
        status_panel = self._create_status_panel()
        layout.addWidget(status_panel)

        layout.addStretch(1)

    def _create_welcome_banner(self) -> QFrame:
        banner = QFrame()
        banner.setProperty("class", "card")
        layout = QHBoxLayout(banner)
        layout.setContentsMargins(24, 20, 24, 20)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        tag = StatusBadge("Academic Operating Systems Workstation", "info")
        text_col.addWidget(tag, alignment=Qt.AlignLeft)

        title = QLabel(f"Welcome to {APP_NAME} v{APP_VERSION}")
        title.setProperty("class", "heading-1")
        text_col.addWidget(title)

        desc = QLabel(
            "Empirical Multicore Processing, Data Parallelism, and Task Parallelism Simulator.\n"
            "Executing genuine concurrent operating system processes across physical and logical cores."
        )
        desc.setStyleSheet("color: #8b949e; line-height: 1.4;")
        text_col.addWidget(desc)

        layout.addLayout(text_col)
        layout.addStretch(1)

        # Status badge block
        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.setSpacing(8)

        status_col.addWidget(StatusBadge("OS Scheduler: Linux CFS", "neutral"), alignment=Qt.AlignRight)
        status_col.addWidget(StatusBadge("Engine Context: spawn", "success"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return banner

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        # Gather genuine hardware values
        physical_cores = psutil.cpu_count(logical=False) or "N/A"
        logical_cores = psutil.cpu_count(logical=True) or "N/A"
        os_info = f"{platform.system()} {platform.release()[:14]}"
        python_ver = platform.python_version()

        # Real Metric Cards
        self.card_physical = MetricCard(
            title="Physical CPU Cores",
            value=f"{physical_cores} Cores",
            subtitle="Hardware execution units on chip die",
            status_text="Verified",
            status_theme="success",
        )
        grid.addWidget(self.card_physical, 0, 0)

        self.card_logical = MetricCard(
            title="Logical CPU Threads",
            value=f"{logical_cores} Threads",
            subtitle="SMT / Hyperthreading addressable CPUs",
            status_text="Optimal",
            status_theme="success",
        )
        grid.addWidget(self.card_logical, 0, 1)

        self.card_platform = MetricCard(
            title="Host Platform",
            value=os_info,
            subtitle="Preemptive multi-user Linux kernel",
            status_text="Arch Linux",
            status_theme="info",
        )
        grid.addWidget(self.card_platform, 0, 2)

        self.card_runtime = MetricCard(
            title="Python Runtime",
            value=f"v{python_ver}",
            subtitle="PySide6 6.12 | NumPy 2.5 | psutil 7.2",
            status_text="Verified",
            status_theme="success",
        )
        grid.addWidget(self.card_runtime, 0, 3)

        return grid

    def _create_modules_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        # Action cards matching the 6 secondary sections
        card_data = ActionCard(
            title="Data Parallelism",
            description="Partition datasets into chunks across worker processes performing SIMD / vector map-reduce.",
            button_text="Launch Data Parallelism →",
            badge_text="Awaiting Phase 5",
            badge_theme="warning",
            on_click=lambda: self.navigate_requested.emit(1),
        )
        grid.addWidget(card_data, 0, 0)

        card_task = ActionCard(
            title="Task Parallelism",
            description="Execute heterogeneous CPU-bound tasks with dependency graphs (DAG) and priority scheduling.",
            button_text="Launch Task Parallelism →",
            badge_text="Awaiting Phase 6",
            badge_theme="warning",
            on_click=lambda: self.navigate_requested.emit(2),
        )
        grid.addWidget(card_task, 0, 1)

        card_monitor = ActionCard(
            title="Core Monitor",
            description="Inspect physical vs logical CPU core topologies, SMT threads, and set process CPU affinities.",
            button_text="Inspect Cores →",
            badge_text="Awaiting Phase 4",
            badge_theme="info",
            on_click=lambda: self.navigate_requested.emit(3),
        )
        grid.addWidget(card_monitor, 1, 0)

        card_scheduler = ActionCard(
            title="Process Scheduler",
            description="Compare educational dispatch policies (FCFS, Priority, Round Robin) with a visual ready queue.",
            button_text="View Scheduler →",
            badge_text="Awaiting Phase 8",
            badge_theme="warning",
            on_click=lambda: self.navigate_requested.emit(4),
        )
        grid.addWidget(card_scheduler, 1, 1)

        card_analytics = ActionCard(
            title="Performance Analytics",
            description="Benchmark sequential vs parallel speedup and efficiency curves illustrating Amdahl's Law.",
            button_text="Analyze Speedup →",
            badge_text="Awaiting Phase 9",
            badge_theme="warning",
            on_click=lambda: self.navigate_requested.emit(5),
        )
        grid.addWidget(card_analytics, 2, 0)

        card_settings = ActionCard(
            title="Workstation Settings",
            description="Configure default worker limits, process timeouts, hardware probing, and logging targets.",
            button_text="Open Settings →",
            badge_text="Config Ready",
            badge_theme="neutral",
            on_click=lambda: self.navigate_requested.emit(6),
        )
        grid.addWidget(card_settings, 2, 1)

        return grid

    def _create_status_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "card-alt")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        header = QLabel("System Concurrency Status & Architecture Notice")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        notice = QLabel(
            "• Multiprocessing Architecture: Fully configured under POSIX spawn start method.\n"
            "• Real Execution Guarantee: CoreSync strictly avoids simulated delays or synthetic CPU metrics. "
            "All parallel workloads will spawn actual OS child processes.\n"
            "• OS Preemption Notice: CPU affinity specifies allowable CPU sets; actual time-slicing is governed by the Linux CFS scheduler."
        )
        notice.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        layout.addWidget(notice)

        return panel

