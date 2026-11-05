"""Performance Analytics Page for CoreSync Workstation."""

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


class PerformancePage(QWidget):
    """Workstation page for empirical speedup, parallel efficiency, and Amdahl's Law analytics."""

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

        # 2. Benchmark Configuration
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Performance Metrics
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Embedded Graph / Amdahl Chart Panel Placeholder
        chart_card = self._create_chart_card()
        layout.addWidget(chart_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Performance Analytics & Amdahl's Law Benchmark")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Empirical scalability analysis comparing sequential vs parallel execution times across worker process sweeps. "
            "Quantifies speedup (S = T_seq / T_par), parallel efficiency (E = S/P * 100%), and Amdahl's Law limits."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Analytics Engine: Phase 9 Pending", "warning"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Benchmark Sweep Parameters")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Workload Type
        grid.addWidget(QLabel("Benchmark Workload:"), 0, 0)
        self.combo_workload = QComboBox()
        self.combo_workload.addItems([
            "Array Square & Summation (10M Elements)",
            "Dense Matrix Multiplication (1000x1000)",
            "Mandelbrot Fractal Compute (4K)",
            "Prime Factorization Sweep",
        ])
        grid.addWidget(self.combo_workload, 0, 1)

        # Max Workers
        grid.addWidget(QLabel("Max Workers Sweep (P):"), 0, 2)
        self.spin_max_workers = QSpinBox()
        self.spin_max_workers.setRange(2, 64)
        self.spin_max_workers.setValue(16)
        grid.addWidget(self.spin_max_workers, 0, 3)

        # Repetitions
        grid.addWidget(QLabel("Benchmark Repetitions:"), 1, 0)
        self.spin_repeats = QSpinBox()
        self.spin_repeats.setRange(1, 10)
        self.spin_repeats.setValue(3)
        grid.addWidget(self.spin_repeats, 1, 1)

        # Warm-up runs
        grid.addWidget(QLabel("Warm-up Runs:"), 1, 2)
        self.spin_warmup = QSpinBox()
        self.spin_warmup.setRange(0, 5)
        self.spin_warmup.setValue(1)
        grid.addWidget(self.spin_warmup, 1, 3)

        layout.addLayout(grid)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.btn_run_benchmark = QPushButton("Start Full Scalability Benchmark")
        self.btn_run_benchmark.setProperty("class", "btn-primary")
        self.btn_run_benchmark.setEnabled(False)
        self.btn_run_benchmark.setToolTip("Will be enabled in Phase 9")
        btn_layout.addWidget(self.btn_run_benchmark)

        layout.addLayout(btn_layout)
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_peak_speedup = MetricCard(
            title="Peak Speedup",
            value="-- x",
            subtitle="Maximum speedup observed across worker count",
            status_text="Pending Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_peak_speedup, 0, 0)

        self.card_peak_eff = MetricCard(
            title="Optimal Efficiency",
            value="-- %",
            subtitle="Parallel efficiency at peak speedup",
            status_text="Pending Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_peak_eff, 0, 1)

        self.card_overhead = MetricCard(
            title="Avg Process Overhead",
            value="-- ms",
            subtitle="Spawn latency + IPC data transfer cost",
            status_text="Pending Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_overhead, 0, 2)

        self.card_throughput = MetricCard(
            title="Peak Throughput",
            value="-- items/s",
            subtitle="Processed elements per unit time",
            status_text="Pending Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_throughput, 0, 3)

        return grid

    def _create_chart_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        header = QLabel("Scalability Curves & Matplotlib Canvas (Preview)")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        notice = QLabel(
            "When implemented in Phase 9, this area will embed interactive Matplotlib plots showing:\n"
            "1. Speedup Curve: Observed speedup vs Linear Ideal ($S = P$) vs Theoretical Amdahl limit.\n"
            "2. Efficiency Curve: Efficiency percentage drop-off as worker count increases.\n"
            "3. Time Breakdown: Stacked bar chart showing Process Startup, IPC Transfer, Raw Compute, and Result Gather.\n"
            "4. Asymmetric Scaling: Distinct speedup inflection points when spilling from P-cores onto E-cores."
        )
        notice.setStyleSheet("color: #8b949e; line-height: 1.5;")
        layout.addWidget(notice)

        return card

