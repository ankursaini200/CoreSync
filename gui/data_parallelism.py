"""Data Parallelism Workstation Page for CoreSync.

Interactive interface for configuring, running, and visualizing genuine data-parallel
computational workloads on host CPU cores with verification against sequential baselines.
"""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.system_info import get_system_summary
from engine.data_parallel.operations import (
    OperationSpec,
    get_supported_operations,
)
from engine.data_parallel.executor import (
    DataParallelBenchmarkResult,
    DataParallelExecutor,
)
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard
from gui.data_parallel_runner import DataParallelRunnerThread


class DataParallelismPage(QWidget):
    """Workstation page for executing and visualizing genuine Data Parallelism on the host CPU."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary = get_system_summary()
        self.operations: Dict[str, OperationSpec] = get_supported_operations()
        self.runner_thread = DataParallelRunnerThread(self)
        self.runner_thread.progress_updated.connect(self._on_progress_updated)
        self.runner_thread.benchmark_finished.connect(self._on_benchmark_finished)
        self.runner_thread.benchmark_failed.connect(self._on_benchmark_failed)

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

        # 2. Configuration & Execution Controls Card
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Live Benchmark Results Grid
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Verification & Timing Breakdown Card
        timing_card = self._create_verification_and_timing_card()
        layout.addWidget(timing_card)

        # 5. Chunk Distribution & Worker Table Card
        table_card = self._create_worker_table_card()
        layout.addWidget(table_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Data Parallelism Engine (SIMD / Multiprocess Map-Reduce)")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Partition uniform numerical datasets into contiguous chunks across isolated worker processes. "
            "Each worker executes identical CPU operations concurrently, and results are reassembled and verified "
            "against sequential baseline execution."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.badge_hardware = StatusBadge("Real Hardware Execution (Host CPU)", "success")
        status_col.addWidget(self.badge_hardware, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        title = QLabel("Workload Configuration & Process Allocation")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(3, 2)

        # Row 1: Operation Selection & Worker Allocation Mode
        lbl_op = QLabel("Computational Kernel:")
        lbl_op.setProperty("class", "metric-label")
        self.combo_ops = QComboBox()
        for op in self.operations.values():
            self.combo_ops.addItem(f"{op.name} ({op.category})", op.op_id)
        self.combo_ops.currentIndexChanged.connect(self._on_operation_changed)
        grid.addWidget(lbl_op, 0, 0)
        grid.addWidget(self.combo_ops, 0, 1)

        lbl_mode = QLabel("Worker Allocation Mode:")
        lbl_mode.setProperty("class", "metric-label")
        self.combo_mode = QComboBox()
        self.combo_mode.addItems([
            "Automatic (Recommended based on workload & CPU capacity)",
            "Manual Worker Count Selection",
        ])
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        grid.addWidget(lbl_mode, 0, 2)
        grid.addWidget(self.combo_mode, 0, 3)

        # Row 2: Dataset Size & Worker Count
        self.lbl_size = QLabel("Dataset Size (Elements):")
        self.lbl_size.setProperty("class", "metric-label")
        self.spin_size = QSpinBox()
        self.spin_size.setRange(1_000, 20_000_000)
        self.spin_size.setSingleStep(100_000)
        self.spin_size.setValue(1_000_000)
        grid.addWidget(self.lbl_size, 1, 0)
        grid.addWidget(self.spin_size, 1, 1)

        lbl_workers = QLabel("Worker Process Count (P):")
        lbl_workers.setProperty("class", "metric-label")
        self.spin_workers = QSpinBox()
        max_limit = max(self.summary.logical_cores or 4, 32)
        self.spin_workers.setRange(1, max_limit)
        auto_w = DataParallelExecutor.determine_automatic_workers(1_000_000, "transcendental")
        self.spin_workers.setValue(auto_w)
        self.spin_workers.setEnabled(False)  # Starts in Automatic mode
        grid.addWidget(lbl_workers, 1, 2)
        grid.addWidget(self.spin_workers, 1, 3)

        # Row 3: Random Seed & Hardware Info Note
        lbl_seed = QLabel("Random Seed:")
        lbl_seed.setProperty("class", "metric-label")
        self.spin_seed = QSpinBox()
        self.spin_seed.setRange(0, 999999)
        self.spin_seed.setValue(42)
        grid.addWidget(lbl_seed, 2, 0)
        grid.addWidget(self.spin_seed, 2, 1)

        self.lbl_hw_info = QLabel(
            f"Detected Host: {self.summary.cpu_model} ({self.summary.physical_cores}P / {self.summary.logical_cores}L Cores)"
        )
        self.lbl_hw_info.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: 600;")
        grid.addWidget(self.lbl_hw_info, 2, 2, 1, 2)

        # Row 4: Warmup checkbox
        self.check_warmup = QCheckBox("Enable Initial Warm-up Run (stabilizes CPU clock governors)")
        self.check_warmup.setChecked(False)
        grid.addWidget(self.check_warmup, 3, 0, 1, 4)

        layout.addLayout(grid)

        # Execution Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_run_benchmark = QPushButton("Start Full Parallel Benchmark")
        self.btn_run_benchmark.setProperty("class", "btn-primary")
        self.btn_run_benchmark.clicked.connect(self._on_start_benchmark)
        btn_layout.addWidget(self.btn_run_benchmark)

        self.btn_cancel = QPushButton("Cancel Execution")
        self.btn_cancel.setProperty("class", "btn-secondary")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # Progress bar & live activity readout
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("Ready. Select parameters and click Start Full Parallel Benchmark.")
        self.lbl_progress_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.lbl_progress_status)

        return card

    def _create_metrics_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.card_speedup = MetricCard(
            title="Parallel Speedup (S)",
            value="-- x",
            subtitle="T_seq / T_par",
            status_text="Pending",
            status_theme="neutral",
        )
        layout.addWidget(self.card_speedup)

        self.card_efficiency = MetricCard(
            title="Parallel Efficiency (E)",
            value="-- %",
            subtitle="(Speedup / Workers) * 100%",
            status_text="Pending",
            status_theme="neutral",
        )
        layout.addWidget(self.card_efficiency)

        self.card_seq_time = MetricCard(
            title="Sequential Time",
            value="-- ms",
            subtitle="Single-core baseline execution",
            status_text="Pending",
            status_theme="neutral",
        )
        layout.addWidget(self.card_seq_time)

        self.card_par_time = MetricCard(
            title="Parallel Time",
            value="-- ms",
            subtitle="Spawn + Compute + Merge wall-clock",
            status_text="Pending",
            status_theme="neutral",
        )
        layout.addWidget(self.card_par_time)

        self.card_throughput = MetricCard(
            title="Processing Throughput",
            value="-- items/s",
            subtitle="Elements evaluated per second",
            status_text="Pending",
            status_theme="neutral",
        )
        layout.addWidget(self.card_throughput)

        return layout

    def _create_verification_and_timing_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(20)

        # Left Column: Verification Badge & Diagnostics
        v_col = QVBoxLayout()
        v_col.setSpacing(6)

        title_v = QLabel("Correctness Verification (Sequential vs Parallel)")
        title_v.setProperty("class", "heading-3")
        v_col.addWidget(title_v)

        self.badge_verification = StatusBadge("Verification: Awaiting Benchmark", "neutral")
        v_col.addWidget(self.badge_verification, alignment=Qt.AlignLeft)

        self.lbl_v_details = QLabel(
            "Every parallel output element is compared against the sequential baseline.\n"
            "Tolerances: rtol=1e-5, atol=1e-8. Discrepancies are flagged immediately."
        )
        self.lbl_v_details.setStyleSheet("color: #8b949e; font-size: 11px;")
        v_col.addWidget(self.lbl_v_details)
        layout.addLayout(v_col, stretch=2)

        # Right Column: Multiprocessing Overhead Breakdown
        o_col = QVBoxLayout()
        o_col.setSpacing(4)

        title_o = QLabel("Non-Overlapping Timing Breakdown")
        title_o.setProperty("class", "heading-3")
        o_col.addWidget(title_o)

        self.lbl_overhead_spawn = QLabel("• Process Spawn: -- ms")
        self.lbl_overhead_spawn.setStyleSheet("color: #8b949e; font-size: 11px; font-family: monospace;")
        o_col.addWidget(self.lbl_overhead_spawn)

        self.lbl_overhead_dispatch = QLabel("• Input Prep & IPC Dispatch: -- ms")
        self.lbl_overhead_dispatch.setStyleSheet("color: #8b949e; font-size: 11px; font-family: monospace;")
        o_col.addWidget(self.lbl_overhead_dispatch)

        self.lbl_overhead_compute = QLabel("• Worker Pure Compute (Critical Path): -- ms")
        self.lbl_overhead_compute.setStyleSheet("color: #8b949e; font-size: 11px; font-family: monospace;")
        o_col.addWidget(self.lbl_overhead_compute)

        self.lbl_overhead_collection = QLabel("• Result Dequeue & Collection Residual: -- ms")
        self.lbl_overhead_collection.setStyleSheet("color: #8b949e; font-size: 11px; font-family: monospace;")
        o_col.addWidget(self.lbl_overhead_collection)

        self.lbl_overhead_merge = QLabel("• Output Reassembly & Merge: -- ms")
        self.lbl_overhead_merge.setStyleSheet("color: #8b949e; font-size: 11px; font-family: monospace;")
        o_col.addWidget(self.lbl_overhead_merge)

        self.lbl_overhead_ipc_total = QLabel("• Estimated Distribution and Collection Overhead: -- ms")
        self.lbl_overhead_ipc_total.setStyleSheet("color: #58a6ff; font-size: 11px; font-family: monospace; font-weight: 600;")
        o_col.addWidget(self.lbl_overhead_ipc_total)

        layout.addLayout(o_col, stretch=2)
        return card

    def _create_worker_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Dataset Chunk Distribution & Worker Process Telemetry")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        self.table_workers = QTableWidget()
        self.table_workers.setColumnCount(6)
        self.table_workers.setHorizontalHeaderLabels([
            "Chunk ID",
            "Assigned Worker",
            "Process PID",
            "Index Range [Start, End)",
            "Chunk Size",
            "Compute Time (Input Delivery Latency)",
        ])
        self.table_workers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_workers.verticalHeader().setVisible(False)
        self.table_workers.setFixedHeight(180)
        self.table_workers.setAlternatingRowColors(True)
        self.table_workers.setStyleSheet("""
            QTableWidget {
                background-color: #161b24;
                border: 1px solid #283344;
                border-radius: 6px;
                gridline-color: #283344;
            }
            QHeaderView::section {
                background-color: #1c2330;
                color: #e6edf3;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #283344;
            }
        """)
        layout.addWidget(self.table_workers)

        return card

    def _on_operation_changed(self) -> None:
        op_id = self.combo_ops.currentData()
        if op_id in self.operations:
            spec = self.operations[op_id]
            self.spin_size.setValue(spec.default_dataset_size)
            self.lbl_size.setText(f"Dataset Size ({spec.size_label}):")
            self._update_auto_worker_count()

    def _on_mode_changed(self, index: int) -> None:
        if index == 0:  # Automatic
            self.spin_workers.setEnabled(False)
            self._update_auto_worker_count()
        else:           # Manual
            self.spin_workers.setEnabled(True)

    def _update_auto_worker_count(self) -> None:
        if self.combo_mode.currentIndex() == 0:
            op_id = self.combo_ops.currentData() or "transcendental"
            size = self.spin_size.value()
            auto_w = DataParallelExecutor.determine_automatic_workers(size, op_id)
            self.spin_workers.setValue(auto_w)

    def _on_start_benchmark(self) -> None:
        op_id = self.combo_ops.currentData()
        size = self.spin_size.value()
        workers = self.spin_workers.value()
        seed = self.spin_seed.value()
        warmup = self.check_warmup.isChecked()

        self.btn_run_benchmark.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_progress_status.setText("Initializing benchmark engine...")
        self.badge_hardware.set_status("Benchmark In Progress", "warning")

        self.runner_thread.configure(
            op_id=op_id,
            dataset_size=size,
            worker_count=workers,
            seed=seed,
            warm_up=warmup,
        )
        self.runner_thread.start()

    def _on_cancel_clicked(self) -> None:
        self.lbl_progress_status.setText("Cancelling execution and reaping workers...")
        self.runner_thread.cancel()

    @Slot(int, int, str)
    def _on_progress_updated(self, completed: int, total: int, msg: str) -> None:
        self.lbl_progress_status.setText(msg)
        if total > 0:
            pct = int((completed / total) * 100)
            self.progress_bar.setValue(pct)

    @Slot(object)
    def _on_benchmark_finished(self, result: DataParallelBenchmarkResult) -> None:
        self.btn_run_benchmark.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setValue(100)
        self.badge_hardware.set_status("Benchmark Completed", "success")

        # Speedup & Efficiency cards
        self.card_speedup.set_value(f"{result.speedup:.2f} x")
        self.card_speedup.set_status("Speedup Achieved" if result.speedup >= 1.0 else "Overhead Bound", "success" if result.speedup >= 1.0 else "warning")

        self.card_efficiency.set_value(f"{result.efficiency_pct:.1f} %")
        self.card_efficiency.set_status("Optimal" if result.efficiency_pct > 60 else "Sub-linear", "info")

        self.card_seq_time.set_value(f"{result.sequential_time_s * 1000:.1f} ms")
        self.card_seq_time.set_status("Baseline", "neutral")

        self.card_par_time.set_value(f"{result.parallel_time_s * 1000:.1f} ms")
        self.card_par_time.set_status(f"{result.worker_count} Workers", "success")

        if result.throughput_items_per_s >= 1_000_000:
            tp_str = f"{result.throughput_items_per_s / 1_000_000:.2f} M/s"
        else:
            tp_str = f"{result.throughput_items_per_s / 1_000:.1f} K/s"
        self.card_throughput.set_value(tp_str)
        self.card_throughput.set_status("Peak", "info")

        # Verification
        v = result.verification
        if v.passed:
            self.badge_verification.set_status("VERIFICATION PASSED", "success")
            self.lbl_v_details.setText(f"✓ 100% matched ({v.total_items:,} items). Max numerical diff: {v.max_difference:.2e}")
        else:
            self.badge_verification.set_status("VERIFICATION FAILED", "danger")
            self.lbl_v_details.setText(f"✗ FAILED: {v.mismatch_count:,} mismatches. {v.status_message}")

        # Timing breakdown
        tb = result.timings
        ipc_dequeue_delay = max(0.0, tb.collection_s - tb.max_worker_compute_s)
        self.lbl_overhead_spawn.setText(f"• Process Spawn: {tb.startup_s * 1000:.2f} ms")
        self.lbl_overhead_dispatch.setText(f"• Input Prep & IPC Dispatch: {tb.dispatch_s * 1000:.2f} ms")
        self.lbl_overhead_compute.setText(f"• Worker Pure Compute (Critical Path): {tb.max_worker_compute_s * 1000:.2f} ms")
        self.lbl_overhead_collection.setText(f"• Result Dequeue & Collection Residual: {ipc_dequeue_delay * 1000:.2f} ms")
        self.lbl_overhead_merge.setText(f"• Output Reassembly & Merge: {tb.merge_s * 1000:.2f} ms")
        self.lbl_overhead_ipc_total.setText(f"• Estimated Distribution and Collection Overhead: {tb.estimated_distribution_overhead_s * 1000:.2f} ms")

        # Update Worker Telemetry Table
        results_by_chunk = {r.chunk_id: r for r in result.worker_results}
        self.table_workers.setRowCount(len(result.chunks))
        for row, chunk in enumerate(result.chunks):
            r = results_by_chunk.get(chunk.chunk_id)
            pid_str = str(r.worker_pid) if r else "Pending"
            time_str = f"{r.compute_time_s * 1000:.1f} ms ({r.input_delivery_latency_s * 1000:.2f}ms delivery delay)" if r else "--"

            self.table_workers.setItem(row, 0, QTableWidgetItem(f"Chunk #{chunk.chunk_id}"))
            self.table_workers.setItem(row, 1, QTableWidgetItem(f"Worker {chunk.chunk_id % result.worker_count}"))
            self.table_workers.setItem(row, 2, QTableWidgetItem(pid_str))
            self.table_workers.setItem(row, 3, QTableWidgetItem(f"[{chunk.start_idx:,}, {chunk.end_idx:,})"))
            self.table_workers.setItem(row, 4, QTableWidgetItem(f"{chunk.size:,} items"))
            self.table_workers.setItem(row, 5, QTableWidgetItem(time_str))

        self.lbl_progress_status.setText(
            f"Benchmark completed in {result.parallel_time_s * 1000:.1f} ms. "
            f"Speedup: {result.speedup:.2f}x ({result.efficiency_pct:.1f}% efficiency)."
        )

    @Slot(str)
    def _on_benchmark_failed(self, error_msg: str) -> None:
        self.btn_run_benchmark.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.badge_hardware.set_status("Benchmark Failed / Cancelled", "danger")
        self.lbl_progress_status.setText(error_msg)

    def shutdown(self) -> None:
        """Clean up thread and active workers upon window close."""
        if self.runner_thread.isRunning():
            self.runner_thread.cancel()
            self.runner_thread.wait(1000)
