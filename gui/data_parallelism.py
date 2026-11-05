"""Data Parallelism Page for CoreSync Workstation."""

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


class DataParallelismPage(QWidget):
    """Workstation page for configuring and visualizing Data Parallelism workloads."""

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

        # 1. Page Header & Engine Status
        header_card = self._create_header_card()
        layout.addWidget(header_card)

        # 2. Workload & Chunking Configuration Card
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Execution Metrics Summary (Placeholders clearly marked)
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Worker Process Grid & Verification Status
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

        title = QLabel("Data Parallelism Simulator (Scatter / Compute / Gather)")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Partition uniform numerical datasets into contiguous chunks across multiple worker processes. "
            "Each worker executes identical SIMD operations, and results are reduced and verified against sequential execution."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Engine Status: Phase 5 Pending", "warning"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(16)

        title = QLabel("Workload Configuration & Process Allocation")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Dataset Size
        grid.addWidget(QLabel("Dataset Size (Elements):"), 0, 0)
        self.combo_size = QComboBox()
        self.combo_size.addItems(["100,000 Elements (Light)", "1,000,000 Elements (Medium)", "10,000,000 Elements (Heavy)"])
        self.combo_size.setCurrentIndex(1)
        grid.addWidget(self.combo_size, 0, 1)

        # Numerical Operation
        grid.addWidget(QLabel("Operation (Kernel):"), 0, 2)
        self.combo_op = QComboBox()
        self.combo_op.addItems(["Array Square (x²)", "Array Summation (Σx)", "Vector Square Root (√x)", "Matrix Multiplication"])
        grid.addWidget(self.combo_op, 0, 3)

        # Worker Process Count
        grid.addWidget(QLabel("Worker Processes (P):"), 1, 0)
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, 64)
        self.spin_workers.setValue(4)
        grid.addWidget(self.spin_workers, 1, 1)

        # Chunk Strategy
        grid.addWidget(QLabel("Chunking Strategy:"), 1, 2)
        self.combo_strategy = QComboBox()
        self.combo_strategy.addItems(["Equal Block Partitioning", "Dynamic Work Queue", "Shared Memory Zero-Copy"])
        grid.addWidget(self.combo_strategy, 1, 3)

        layout.addLayout(grid)

        # Control Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.btn_run_seq = QPushButton("Run Sequential Baseline")
        self.btn_run_seq.setProperty("class", "btn-secondary")
        self.btn_run_seq.setEnabled(False)
        self.btn_run_seq.setToolTip("Will be enabled in Phase 5")
        btn_layout.addWidget(self.btn_run_seq)

        self.btn_run_parallel = QPushButton("Execute Data Parallel")
        self.btn_run_parallel.setProperty("class", "btn-primary")
        self.btn_run_parallel.setEnabled(False)
        self.btn_run_parallel.setToolTip("Will be enabled in Phase 5")
        btn_layout.addWidget(self.btn_run_parallel)

        layout.addLayout(btn_layout)
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_seq_time = MetricCard(
            title="Sequential Time (T_seq)",
            value="-- ms",
            subtitle="Single-core baseline execution duration",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_seq_time, 0, 0)

        self.card_par_time = MetricCard(
            title="Parallel Time (T_par)",
            value="-- ms",
            subtitle="Multiprocess end-to-end execution duration",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_par_time, 0, 1)

        self.card_speedup = MetricCard(
            title="Speedup (S)",
            value="-- x",
            subtitle="S = T_seq / T_par (Amdahl's Law)",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_speedup, 0, 2)

        self.card_efficiency = MetricCard(
            title="Parallel Efficiency (E)",
            value="-- %",
            subtitle="E = (S / Workers) * 100%",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_efficiency, 0, 3)

        return grid

    def _create_details_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        header = QLabel("Scatter / Gather Worker Execution Details")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        info = QLabel(
            "When executed in Phase 5, this panel will display:\n"
            "• Active child worker process IDs (PIDs) assigned to each chunk slice.\n"
            "• IPC transfer and serialization latency ($T_{\\text{transfer}}$).\n"
            "• Pure mathematical compute time ($T_{\\text{compute}}$).\n"
            "• Result gathering and reduction integrity checks via NumPy (np.allclose)."
        )
        info.setStyleSheet("color: #8b949e; line-height: 1.5;")
        layout.addWidget(info)

        return card

