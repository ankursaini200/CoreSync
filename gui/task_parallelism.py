"""Task Parallelism Page for CoreSync Workstation."""

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


class TaskParallelismPage(QWidget):
    """Workstation page for configuring and visualizing Task Parallelism (Heterogeneous Workloads & DAGs)."""

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

        # 2. Configuration & Task Selection
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Task State Metrics (Placeholders clearly marked)
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Task Dependency & DAG Queue Details
        details_card = self._create_details_card()
        layout.addWidget(details_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Task Parallelism Simulator (Heterogeneous Concurrency)")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Execute distinct, heterogeneous CPU-bound tasks concurrently across worker processes. "
            "Supports task dependencies (DAG), priority queues, and dynamic worker dispatching."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Engine Status: Phase 6 Pending", "warning"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(16)

        title = QLabel("Heterogeneous Task Set & Dispatch Controls")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Task Preset
        grid.addWidget(QLabel("Workload Preset:"), 0, 0)
        self.combo_preset = QComboBox()
        self.combo_preset.addItems([
            "Scientific Pipeline (Matrix + FFT + Primes)",
            "Data Analytics (Aggregation + Stats + Sorting)",
            "Rendering Pipeline (Mandelbrot Fractal Chunks)",
            "Independent Benchmark Suite",
        ])
        grid.addWidget(self.combo_preset, 0, 1)

        # Task Scheduling Mode
        grid.addWidget(QLabel("Dispatch Strategy:"), 0, 2)
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Priority Queue", "First-Come First-Served (FCFS)", "Dependency Ordered (DAG)"])
        grid.addWidget(self.combo_mode, 0, 3)

        # Worker Allocation
        grid.addWidget(QLabel("Worker Processes:"), 1, 0)
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 32)
        self.spin_workers.setValue(4)
        grid.addWidget(self.spin_workers, 1, 1)

        # Failure Handling
        grid.addWidget(QLabel("Fault Tolerance:"), 1, 2)
        self.combo_fault = QComboBox()
        self.combo_fault.addItems(["Fail-Fast (Abort on Error)", "Continue on Error", "Retry Failed Tasks"])
        grid.addWidget(self.combo_fault, 1, 3)

        layout.addLayout(grid)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.btn_run = QPushButton("Dispatch Task Workload")
        self.btn_run.setProperty("class", "btn-primary")
        self.btn_run.setEnabled(False)
        self.btn_run.setToolTip("Will be enabled in Phase 6")
        btn_layout.addWidget(self.btn_run)

        layout.addLayout(btn_layout)
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_queued = MetricCard(
            title="Queued Tasks",
            value="0",
            subtitle="Tasks awaiting worker allocation",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_queued, 0, 0)

        self.card_running = MetricCard(
            title="Running Tasks",
            value="0",
            subtitle="Tasks actively executing in child PIDs",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_running, 0, 1)

        self.card_completed = MetricCard(
            title="Completed Tasks",
            value="0",
            subtitle="Successfully reduced and verified",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_completed, 0, 2)

        self.card_failed = MetricCard(
            title="Failed / Cancelled",
            value="0",
            subtitle="Tasks encountering exceptions or timeout",
            status_text="None",
            status_theme="neutral",
        )
        grid.addWidget(self.card_failed, 0, 3)

        return grid

    def _create_details_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        header = QLabel("Task Queue, DAG Dependencies, and Execution Timeline")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        info = QLabel(
            "When implemented in Phase 6, this panel will display:\n"
            "• Directed Acyclic Graph (DAG) dependency resolution (topological ordering).\n"
            "• Live task states: READY, RUNNING, COMPLETED, FAILED.\n"
            "• Execution duration per task without artificial delays.\n"
            "• Worker affinity binding and PID tracing per heterogeneous job."
        )
        info.setStyleSheet("color: #8b949e; line-height: 1.5;")
        layout.addWidget(info)

        return card

