"""Dashboard Page for CoreSync Workstation.

Consumes centralized SystemSummary and live CPUMetricsSnapshot.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
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
from utils.system_info import SystemSummary, get_system_summary
from monitoring.cpu_monitor import CPUMetricsSnapshot
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard
from gui.components.action_card import ActionCard


class DashboardPage(QWidget):
    """Workstation Dashboard Page providing hardware summary, architecture status, and quick module launchers."""

    navigate_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary: SystemSummary = get_system_summary()
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

        tag = StatusBadge(self.summary.detection_status, "info")
        text_col.addWidget(tag, alignment=Qt.AlignLeft)

        title = QLabel(f"{APP_NAME} Workstation - {self.summary.cpu_model}")
        title.setProperty("class", "heading-1")
        text_col.addWidget(title)

        desc = QLabel(
            f"Host System: {self.summary.os_name} ({self.summary.os_kernel}, {self.summary.architecture}).\n"
            f"Hardware: {self.summary.physical_cores} Physical Cores, {self.summary.logical_cores} Logical Execution Threads. "
            f"Active process affinity: {len(self.summary.current_affinity)} cores."
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

        # 1. Overall Live CPU Utilization Card
        self.card_cpu_load = MetricCard(
            title="Overall CPU Load",
            value="0.0 %",
            subtitle="Aggregated CPU utilization across all cores",
            status_text="Live Sampler",
            status_theme="success",
            show_progress=True,
            progress_val=0,
        )
        grid.addWidget(self.card_cpu_load, 0, 0)

        # 2. System RAM Usage Card
        self.card_ram = MetricCard(
            title="System Memory",
            value="Sampling...",
            subtitle="Host physical RAM allocation",
            status_text="psutil",
            status_theme="info",
            show_progress=True,
            progress_val=0,
        )
        grid.addWidget(self.card_ram, 0, 1)

        # 3. Physical Cores
        self.card_physical = MetricCard(
            title="Physical Cores",
            value=f"{self.summary.physical_cores} Cores",
            subtitle=f"{self.summary.cpu_vendor} hardware units",
            status_text="Verified",
            status_theme="success",
        )
        grid.addWidget(self.card_physical, 0, 2)

        # 4. Logical Threads
        self.card_logical = MetricCard(
            title="Logical CPUs",
            value=f"{self.summary.logical_cores} Threads",
            subtitle="SMT / Hyperthreading addressable",
            status_text="Optimal",
            status_theme="success",
        )
        grid.addWidget(self.card_logical, 0, 3)

        return grid

    def _create_modules_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        card_core = ActionCard(
            title="Real Core Monitor",
            description="Inspect physical vs logical CPU core topologies, SMT threads, and live per-core utilization.",
            button_text="Inspect Real Cores →",
            badge_text="Real Hardware",
            badge_theme="success",
            on_click=lambda: self.navigate_requested.emit(1),
        )
        grid.addWidget(card_core, 0, 0)

        card_proc = ActionCard(
            title="Real Process Monitor",
            description="Observe top CPU/memory consuming operating system processes and active CoreSync workers.",
            button_text="View Processes →",
            badge_text="Real Hardware",
            badge_theme="success",
            on_click=lambda: self.navigate_requested.emit(2),
        )
        grid.addWidget(card_proc, 0, 1)

        card_stress = ActionCard(
            title="Real CPU Stress Tool",
            description="Safely generate multicore CPU load with duty-cycle throttling and automatic timeout caps.",
            button_text="Launch Stress Lab →",
            badge_text="Safety Guarded",
            badge_theme="danger",
            on_click=lambda: self.navigate_requested.emit(3),
        )
        grid.addWidget(card_stress, 0, 2)

        card_vconfig = ActionCard(
            title="Virtual CPU Architect",
            description="Design custom simulated processors with 1-128 cores and asymmetric P/E hybrid ratios.",
            button_text="Configure CPU →",
            badge_text="Virtual Lab",
            badge_theme="info",
            on_click=lambda: self.navigate_requested.emit(4),
        )
        grid.addWidget(card_vconfig, 1, 0)

        card_vmonitor = ActionCard(
            title="Virtual Core Monitor",
            description="Visualize simulated multicore execution matrices and individual virtual core utilization.",
            button_text="View Matrix →",
            badge_text="Virtual Lab",
            badge_theme="info",
            on_click=lambda: self.navigate_requested.emit(5),
        )
        grid.addWidget(card_vmonitor, 1, 1)

        card_vscheduler = ActionCard(
            title="Virtual Scheduling Lab",
            description="Experiment with FCFS, Priority, and Round Robin scheduling algorithms on virtual cores.",
            button_text="Launch Scheduler →",
            badge_text="Virtual Lab",
            badge_theme="info",
            on_click=lambda: self.navigate_requested.emit(6),
        )
        grid.addWidget(card_vscheduler, 1, 2)

        return grid

    def _create_status_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "card-alt")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        header = QLabel("System Concurrency Status & Architecture Notice")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        hybrid_status = "Intel Hybrid (P/E Cores Detected)" if self.summary.topology.is_hybrid else "Symmetric Multiprocessing (SMP)"
        notice = QLabel(
            f"• CPU Architecture: {self.summary.cpu_model} [{hybrid_status}]\n"
            f"• Concurrency Engine: Initialized under POSIX 'spawn' start method.\n"
            f"• Real Execution Guarantee: CoreSync strictly avoids simulated delays or synthetic CPU metrics.\n"
            f"• Live Monitoring Service: Active in background QThread ({self.summary.logical_cores} cores sampled concurrently)."
        )
        notice.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        layout.addWidget(notice)

        return panel

    @Slot(CPUMetricsSnapshot)
    def update_metrics(self, snapshot: CPUMetricsSnapshot) -> None:
        """Receive live overall CPU metrics update."""
        val = snapshot.overall_percent
        self.card_cpu_load.set_value(f"{val:.1f} %")
        if self.card_cpu_load.progress_bar:
            self.card_cpu_load.progress_bar.setValue(int(round(val)))

        if hasattr(self, "card_ram") and snapshot.ram_total_gb > 0:
            self.card_ram.set_value(f"{snapshot.ram_used_gb:.1f} / {snapshot.ram_total_gb:.1f} GB")
            self.card_ram.set_subtitle(f"{snapshot.ram_percent:.1f}% utilized")
            if self.card_ram.progress_bar:
                self.card_ram.progress_bar.setValue(int(round(snapshot.ram_percent)))
