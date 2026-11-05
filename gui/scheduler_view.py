"""Scheduler View Page for CoreSync Workstation."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class SchedulerViewPage(QWidget):
    """Workstation page for visualizing educational scheduling algorithms and process queues."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(20)
        scroll.setWidget(container)

        # 1. Header Card
        header_card = self._create_header_card()
        layout.addWidget(header_card)

        # 2. Algorithm Selector & Controls
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Queue State Metrics
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Ready Queue & Gantt Timeline Preview Panel
        timeline_panel = self._create_timeline_panel()
        layout.addWidget(timeline_panel)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Educational Process Scheduler & Queue Simulator")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Demonstrate classical Operating System scheduling algorithms (FCFS, Priority, Round Robin). "
            "Contrasts application-level dispatch logic with the underlying Linux kernel Completely Fair Scheduler (CFS)."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Scheduler Engine: Phase 8 Pending", "warning"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Algorithm Selection & Dispatch Parameters")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Algorithm
        grid.addWidget(QLabel("Scheduling Algorithm:"), 0, 0)
        self.combo_algo = QComboBox()
        self.combo_algo.addItems([
            "First Come First Served (FCFS)",
            "Non-Preemptive Priority Scheduling",
            "Preemptive Priority Scheduling",
            "Round Robin (Time-Sliced)",
        ])
        grid.addWidget(self.combo_algo, 0, 1)

        # Time Quantum (for Round Robin)
        grid.addWidget(QLabel("Time Quantum (RR):"), 0, 2)
        self.spin_quantum = QSpinBox()
        self.spin_quantum.setRange(10, 1000)
        self.spin_quantum.setValue(50)
        self.spin_quantum.setSuffix(" ms")
        grid.addWidget(self.spin_quantum, 0, 3)

        # Job Batch Count
        grid.addWidget(QLabel("Process Batch Count:"), 1, 0)
        self.spin_jobs = QSpinBox()
        self.spin_jobs.setRange(2, 20)
        self.spin_jobs.setValue(6)
        grid.addWidget(self.spin_jobs, 1, 1)

        # Workload Intensity
        grid.addWidget(QLabel("Burst Intensity:"), 1, 2)
        self.combo_burst = QComboBox()
        self.combo_burst.addItems(["Short Bursts (Interactive)", "Mixed Bursts (Realistic)", "Long CPU Bursts (Compute)"])
        grid.addWidget(self.combo_burst, 1, 3)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.btn_schedule = QPushButton("Simulate Dispatch Schedule")
        self.btn_schedule.setProperty("class", "btn-primary")
        self.btn_schedule.setEnabled(False)
        self.btn_schedule.setToolTip("Will be enabled in Phase 8")
        btn_layout.addWidget(self.btn_schedule)

        layout.addLayout(btn_layout)
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_ready = MetricCard(
            title="Ready Queue",
            value="0 Jobs",
            subtitle="Processes loaded and awaiting CPU dispatch",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_ready, 0, 0)

        self.card_running = MetricCard(
            title="Running on CPU",
            value="0 Jobs",
            subtitle="Processes actively executing burst slices",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_running, 0, 1)

        self.card_turnaround = MetricCard(
            title="Avg Turnaround Time",
            value="-- ms",
            subtitle="Submission to completion duration",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_turnaround, 0, 2)

        self.card_waiting = MetricCard(
            title="Avg Waiting Time",
            value="-- ms",
            subtitle="Total time spent in ready queue",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_waiting, 0, 3)

        return grid

    def _create_timeline_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "card-alt")
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header = QLabel("Execution Timeline & Gantt Chart (Preview)")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        notice = QLabel(
            "When implemented in Phase 8, this panel will feature:\n"
            "• Live graphical Gantt chart illustrating time slices and context switches.\n"
            "• Step-by-step queue evolution (Arrival → Ready Queue → Running → Terminated).\n"
            "• Theoretical comparison between FCFS, Priority, and Round Robin metrics.\n"
            "• OS concept notes explaining why modern kernels use multi-level dynamic priority queues (e.g. CFS/EEVDF) rather than simple FCFS."
        )
        notice.setStyleSheet("color: #8b949e; line-height: 1.5;")
        layout.addWidget(notice)

        return panel

