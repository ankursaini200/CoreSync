"""Performance Analytics, Benchmarking and Amdahl's Law Page for CoreSync Workstation.

Features 7 distinct analytics sections:
1. Overall Performance Dashboard (Dual Environment Paradigm & Global Rollup)
2. Data Parallelism Analytics (Multi-run empirical sweeps, warm-up isolation, timing breakdown)
3. Task Parallelism Analytics (DAG makespan, actual speedup vs baseline, worker utilization)
4. CPU Scheduling Analytics (Algorithmic comparison table, waiting/turnaround rankings)
5. Virtual Lab Analytics (Multicore simulation, discrete tick throughput, core capacity)
6. Benchmark History (Persistent JSON session storage, statistical sample inspection, deletion)
7. Amdahl's Law Calculator (Interactive theoretical speedup curve, asymptote, limitations)
"""

from datetime import datetime
import math
import os
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.analytics.amdahl import AmdahlCalculator
from engine.analytics.benchmarking import (
    BenchmarkingEngine,
    BenchmarkEngineType,
    BenchmarkSessionResult,
    get_sanitized_hardware_metadata,
)
from engine.analytics.history import BenchmarkHistoryManager
from engine.analytics.models import MetricClassification
from engine.data_parallel.operations import get_supported_operations
from engine.process_scheduler.presets import get_all_presets
from gui.analytics_runner import AnalyticsBenchmarkRunnerThread
from gui.components.analytics_chart import (
    AmdahlCurveWidget,
    ScalabilityChartWidget,
    TimingBreakdownWidget,
)
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class PerformancePage(QWidget):
    """Workstation Performance Analytics, Benchmarking, and Scalability Page."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._history_mgr = BenchmarkHistoryManager()
        self._runner_thread = AnalyticsBenchmarkRunnerThread(self)
        self._runner_thread.progress_updated.connect(self._on_progress_updated)
        self._runner_thread.benchmark_finished.connect(self._on_benchmark_finished)
        self._runner_thread.benchmark_failed.connect(self._on_benchmark_failed)

        self._active_tab_engine: Optional[BenchmarkEngineType] = None
        self._setup_ui()
        self._refresh_history_table()
        self._update_amdahl_display()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Main Tab Widget
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        outer_layout.addWidget(self.tabs)

        # Tab 1: Dashboard
        self.tabs.addTab(self._create_dashboard_tab(), "Overview Dashboard")

        # Tab 2: Data Parallelism
        self.tabs.addTab(self._create_data_parallel_tab(), "Data Parallelism")

        # Tab 3: Task Parallelism
        self.tabs.addTab(self._create_task_parallel_tab(), "Task Parallelism")

        # Tab 4: CPU Scheduling
        self.tabs.addTab(self._create_scheduling_tab(), "CPU Scheduling")

        # Tab 5: Virtual Lab
        self.tabs.addTab(self._create_virtual_lab_tab(), "Virtual Lab")

        # Tab 6: Benchmark History
        self.tabs.addTab(self._create_history_tab(), "Benchmark History")

        # Tab 7: Amdahl's Law Calculator
        self.tabs.addTab(self._create_amdahl_tab(), "Amdahl's Law")

    # =========================================================================
    # TAB 1: OVERVIEW DASHBOARD
    # =========================================================================
    def _create_dashboard_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(18)
        scroll.setWidget(container)

        # Header Card
        header = QFrame()
        header.setProperty("class", "card")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 16, 20, 16)
        col = QVBoxLayout()
        t = QLabel("Workstation Performance Analytics & Scalability Engine")
        t.setProperty("class", "heading-1")
        col.addWidget(t)
        desc = QLabel(
            "Empirical multi-run benchmarking, statistical variance rollups, and theoretical Amdahl scalability models. "
            "Rigorously segregates directly measured hardware metrics from mathematically derived and simulated indicators."
        )
        desc.setStyleSheet("color: #8b949e; line-height: 1.4;")
        col.addWidget(desc)
        h_layout.addLayout(col)
        h_layout.addStretch(1)
        badge = StatusBadge("Engine Active", "success")
        h_layout.addWidget(badge, alignment=Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(header)

        # Top Metric Cards
        grid = QGridLayout()
        grid.setSpacing(14)
        self.dash_card_speedup = MetricCard(
            title="Max Recorded Speedup",
            value="-- x",
            subtitle="Derived: S = T_seq / T_par",
            status_text="Mathematically Derived",
            status_theme="info",
        )
        grid.addWidget(self.dash_card_speedup, 0, 0)

        self.dash_card_efficiency = MetricCard(
            title="Peak Parallel Efficiency",
            value="-- %",
            subtitle="Derived: E = S / W * 100%",
            status_text="Mathematically Derived",
            status_theme="info",
        )
        grid.addWidget(self.dash_card_efficiency, 0, 1)

        self.dash_card_sessions = MetricCard(
            title="Persisted Benchmarks",
            value=str(len(self._history_mgr.list_summaries())),
            subtitle="Historical runs saved in local JSON archive",
            status_text="Directly Measured",
            status_theme="success",
        )
        grid.addWidget(self.dash_card_sessions, 0, 2)

        self.dash_card_virtual = MetricCard(
            title="Virtual Lab Clock",
            value="Discrete Ticks",
            subtitle="Simulated educational multicore scheduler",
            status_text="Simulated Virtual",
            status_theme="warning",
        )
        grid.addWidget(self.dash_card_virtual, 0, 3)
        layout.addLayout(grid)

        # Metric Provenance Guide Card
        prov_card = QFrame()
        prov_card.setProperty("class", "card")
        p_layout = QVBoxLayout(prov_card)
        p_layout.setSpacing(10)
        p_title = QLabel("Metric Provenance & Classification Standard")
        p_title.setProperty("class", "heading-2")
        p_layout.addWidget(p_title)

        p_desc = QLabel(
            "• DIRECTLY_MEASURED: Monotonic wall-clock elapsed time (time.perf_counter_ns), process RSS memory usage (RAM footprint), and OS CPU times (user + system).\n"
            "• MATHEMATICALLY_DERIVED: Deterministic formulas and reductions computed from measured inputs (Actual Speedup S = T_seq / T_par, Parallel Efficiency E = S / W, Compute Interval Union = | ⋃ [s_i, e_i] |, No-Worker-Compute Time = T_makespan - T_union, Concurrency Density).\n"
            "• ESTIMATED_RESIDUAL: Used strictly when a value represents an approximation or estimate rather than a deterministic reduction from verified timing boundaries.\n"
            "• SIMULATED_VIRTUAL: Discrete logical tick steps and virtual core capacity allocations generated inside the single-threaded Virtual Lab simulator (never presented as real host measurements)."
        )
        p_desc.setStyleSheet("color: #8b949e; line-height: 1.6; font-size: 12px;")
        p_layout.addWidget(p_desc)
        layout.addWidget(prov_card)

        # Host Hardware Architecture & Core Topology Card
        hw = get_sanitized_hardware_metadata()
        hw_card = QFrame()
        hw_card.setProperty("class", "card")
        hw_layout = QVBoxLayout(hw_card)
        hw_layout.setSpacing(10)
        hw_title = QLabel("Host Hardware Architecture & Verified Topology")
        hw_title.setProperty("class", "heading-2")
        hw_layout.addWidget(hw_title)

        hw_grid = QGridLayout()
        hw_grid.setHorizontalSpacing(24)
        hw_grid.setVerticalSpacing(8)

        phys = hw.get("physical_cores", "Unknown")
        logi = hw.get("total_logical_cores", "Unknown")
        model = hw.get("cpu_model", "Unknown")
        arch = hw.get("architecture", "Unknown")
        os_str = hw.get("operating_system", "Unknown")
        ram_tot = f"{hw.get('total_ram_gb', 0.0):.2f} GB" if hw.get("total_ram_gb") is not None else "Unknown"
        ram_avail = f"{hw.get('available_ram_gb', 0.0):.2f} GB" if hw.get("available_ram_gb") is not None else "Unknown"
        hybrid_info = "Hybrid Architecture (P-Cores + E-Cores)" if hw.get("is_hybrid") else "Symmetric Topology"

        hw_grid.addWidget(QLabel("CPU Model:"), 0, 0)
        l_model = QLabel(str(model))
        l_model.setStyleSheet("color: #58a6ff; font-weight: bold;")
        hw_grid.addWidget(l_model, 0, 1)

        hw_grid.addWidget(QLabel("Physical Cores:"), 0, 2)
        l_phys = QLabel(f"{phys} Physical Cores ({hybrid_info})")
        l_phys.setStyleSheet("color: #7ee787; font-weight: bold;")
        hw_grid.addWidget(l_phys, 0, 3)

        hw_grid.addWidget(QLabel("Logical Threads:"), 1, 0)
        l_logi = QLabel(f"{logi} Logical Processors")
        l_logi.setStyleSheet("color: #7ee787; font-weight: bold;")
        hw_grid.addWidget(l_logi, 1, 1)

        hw_grid.addWidget(QLabel("Architecture:"), 1, 2)
        l_arch = QLabel(f"{arch} (64-bit Monotonic)")
        l_arch.setStyleSheet("color: #8b949e;")
        hw_grid.addWidget(l_arch, 1, 3)

        hw_grid.addWidget(QLabel("Operating System:"), 2, 0)
        l_os = QLabel(str(os_str))
        l_os.setStyleSheet("color: #8b949e;")
        hw_grid.addWidget(l_os, 2, 1)

        hw_grid.addWidget(QLabel("System Memory (RAM):"), 2, 2)
        l_ram = QLabel(f"{ram_tot} Total / {ram_avail} Available")
        l_ram.setStyleSheet("color: #8b949e;")
        hw_grid.addWidget(l_ram, 2, 3)

        hw_layout.addLayout(hw_grid)
        layout.addWidget(hw_card)

        # Dual Environment Architecture Card
        dual_card = QFrame()
        dual_card.setProperty("class", "card-alt")
        d_layout = QVBoxLayout(dual_card)
        d_layout.setSpacing(10)
        d_title = QLabel("Dual Execution Environments: Real Multiprocessing vs Virtual Lab")
        d_title.setProperty("class", "heading-2")
        d_layout.addWidget(d_title)

        d_text = QLabel(
            "1. Real Host Multiprocessing: Executes true CPU-bound algorithms across isolated spawned processes. "
            "Exhibits physical cache coherency effects, thermal throttling, POSIX IPC pipe latency, and OS scheduling jitter.\n"
            "2. Virtual Lab Scheduler: Pure deterministic simulation running within a single logical thread. "
            "Allows observing Round Robin quantum expiration, starvation, and queueing dynamics without hardware noise."
        )
        d_text.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        d_layout.addWidget(d_text)
        layout.addWidget(dual_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 2: DATA PARALLELISM ANALYTICS
    # =========================================================================
    def _create_data_parallel_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        # Controls Card
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        c_title = QLabel("Data Parallelism Scalability Benchmark Configuration")
        c_title.setProperty("class", "heading-2")
        c_layout.addWidget(c_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Workload:"), 0, 0)
        self.dp_combo_op = QComboBox()
        for op_id, spec in get_supported_operations().items():
            self.dp_combo_op.addItem(f"{spec.name} ({op_id})", op_id)
        grid.addWidget(self.dp_combo_op, 0, 1)

        grid.addWidget(QLabel("Dataset Elements:"), 0, 2)
        self.dp_spin_size = QSpinBox()
        self.dp_spin_size.setRange(5_000, 2_000_000)
        self.dp_spin_size.setValue(100_000)
        self.dp_spin_size.setSingleStep(50_000)
        grid.addWidget(self.dp_spin_size, 0, 3)

        grid.addWidget(QLabel("Worker Processes:"), 1, 0)
        self.dp_spin_workers = QSpinBox()
        self.dp_spin_workers.setRange(2, min(32, (os.cpu_count() or 4) * 2))
        self.dp_spin_workers.setValue(4)
        grid.addWidget(self.dp_spin_workers, 1, 1)

        grid.addWidget(QLabel("Measured Passes:"), 1, 2)
        self.dp_spin_repeats = QSpinBox()
        self.dp_spin_repeats.setRange(1, 10)
        self.dp_spin_repeats.setValue(3)
        grid.addWidget(self.dp_spin_repeats, 1, 3)

        grid.addWidget(QLabel("Warm-up Passes:"), 2, 0)
        self.dp_spin_warmup = QSpinBox()
        self.dp_spin_warmup.setRange(0, 5)
        self.dp_spin_warmup.setValue(1)
        grid.addWidget(self.dp_spin_warmup, 2, 1)

        btn_row = QHBoxLayout()
        self.dp_btn_run = QPushButton("Run Data Parallel Benchmark")
        self.dp_btn_run.setProperty("class", "btn-primary")
        self.dp_btn_run.clicked.connect(self._run_dp_benchmark)
        btn_row.addWidget(self.dp_btn_run)

        self.dp_btn_cancel = QPushButton("Cancel")
        self.dp_btn_cancel.setProperty("class", "btn-danger")
        self.dp_btn_cancel.setEnabled(False)
        self.dp_btn_cancel.clicked.connect(self._cancel_running_benchmark)
        btn_row.addWidget(self.dp_btn_cancel)
        grid.addLayout(btn_row, 2, 2, 1, 2)

        c_layout.addLayout(grid)

        # Progress bar
        self.dp_progress = QProgressBar()
        self.dp_progress.setVisible(False)
        c_layout.addWidget(self.dp_progress)

        self.dp_status_lbl = QLabel("")
        self.dp_status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        c_layout.addWidget(self.dp_status_lbl)

        layout.addWidget(ctrl_card)

        # Metrics Grid
        m_grid = QGridLayout()
        m_grid.setSpacing(12)

        self.dp_card_speedup = MetricCard(
            title="Actual Speedup (S)",
            value="-- x",
            subtitle="Derived: S = T_seq / T_par",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.dp_card_speedup, 0, 0)

        self.dp_card_efficiency = MetricCard(
            title="Parallel Efficiency (E)",
            value="-- %",
            subtitle="Derived: E = S / W * 100%",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.dp_card_efficiency, 0, 1)

        self.dp_card_throughput = MetricCard(
            title="Empirical Throughput",
            value="-- items/s",
            subtitle="Direct: elements / makespan",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.dp_card_throughput, 0, 2)

        self.dp_card_overhead = MetricCard(
            title="No-Worker-Compute Time",
            value="-- ms",
            subtitle="Makespan - Compute Interval Union",
            status_text="Mathematically Derived",
            status_theme="info",
        )
        m_grid.addWidget(self.dp_card_overhead, 0, 3)
        layout.addLayout(m_grid)

        # Visualizations Row: Scalability Curve & Timing Breakdown
        vis_row = QHBoxLayout()
        self.dp_chart_scalability = ScalabilityChartWidget()
        vis_row.addWidget(self.dp_chart_scalability, 1)

        self.dp_chart_timings = TimingBreakdownWidget()
        vis_row.addWidget(self.dp_chart_timings, 1)
        layout.addLayout(vis_row)

        # Iterations Table
        tbl_card = QFrame()
        tbl_card.setProperty("class", "card")
        t_layout = QVBoxLayout(tbl_card)
        t_title = QLabel("Measured Benchmark Iteration Records")
        t_title.setProperty("class", "heading-2")
        t_layout.addWidget(t_title)

        self.dp_table = QTableWidget()
        self.dp_table.setColumnCount(7)
        self.dp_table.setHorizontalHeaderLabels([
            "Pass", "Type", "Seq Time (ms)", "Par Time (ms)", "Speedup", "Efficiency", "Verification"
        ])
        self.dp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.dp_table.setMinimumHeight(150)
        t_layout.addWidget(self.dp_table)
        layout.addWidget(tbl_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 3: TASK PARALLELISM ANALYTICS
    # =========================================================================
    def _create_task_parallel_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        c_title = QLabel("Task Parallelism DAG Scalability Benchmark Configuration")
        c_title.setProperty("class", "heading-2")
        c_layout.addWidget(c_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("DAG Preset:"), 0, 0)
        self.tp_combo_dag = QComboBox()
        self.tp_combo_dag.addItem("Diamond Dependency Pipeline", "diamond")
        self.tp_combo_dag.addItem("Scientific Research Pipeline", "scientific")
        self.tp_combo_dag.addItem("Independent Tasks Benchmark Suite", "independent")
        grid.addWidget(self.tp_combo_dag, 0, 1)

        grid.addWidget(QLabel("Worker Processes:"), 0, 2)
        self.tp_spin_workers = QSpinBox()
        self.tp_spin_workers.setRange(2, min(32, (os.cpu_count() or 4) * 2))
        self.tp_spin_workers.setValue(4)
        grid.addWidget(self.tp_spin_workers, 0, 3)

        grid.addWidget(QLabel("Measured Passes:"), 1, 0)
        self.tp_spin_repeats = QSpinBox()
        self.tp_spin_repeats.setRange(1, 10)
        self.tp_spin_repeats.setValue(3)
        grid.addWidget(self.tp_spin_repeats, 1, 1)

        grid.addWidget(QLabel("Warm-up Passes:"), 1, 2)
        self.tp_spin_warmup = QSpinBox()
        self.tp_spin_warmup.setRange(0, 5)
        self.tp_spin_warmup.setValue(1)
        grid.addWidget(self.tp_spin_warmup, 1, 3)

        btn_row = QHBoxLayout()
        self.tp_btn_run = QPushButton("Run Task DAG Benchmark")
        self.tp_btn_run.setProperty("class", "btn-primary")
        self.tp_btn_run.clicked.connect(self._run_tp_benchmark)
        btn_row.addWidget(self.tp_btn_run)

        self.tp_btn_cancel = QPushButton("Cancel")
        self.tp_btn_cancel.setProperty("class", "btn-danger")
        self.tp_btn_cancel.setEnabled(False)
        self.tp_btn_cancel.clicked.connect(self._cancel_running_benchmark)
        btn_row.addWidget(self.tp_btn_cancel)
        grid.addLayout(btn_row, 2, 0, 1, 4)

        c_layout.addLayout(grid)

        self.tp_progress = QProgressBar()
        self.tp_progress.setVisible(False)
        c_layout.addWidget(self.tp_progress)

        self.tp_status_lbl = QLabel("")
        self.tp_status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        c_layout.addWidget(self.tp_status_lbl)

        layout.addWidget(ctrl_card)

        # Metrics Grid
        m_grid = QGridLayout()
        m_grid.setSpacing(12)

        self.tp_card_actual_speedup = MetricCard(
            title="Actual Speedup (S)",
            value="-- x",
            subtitle="Derived: S = T_seq / T_par",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.tp_card_actual_speedup, 0, 0)

        self.tp_card_parallelism_ratio = MetricCard(
            title="Parallelism Ratio (P)",
            value="-- x",
            subtitle="Derived: P = T_comp_sum / T_par",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.tp_card_parallelism_ratio, 0, 1)

        self.tp_card_utilization = MetricCard(
            title="Worker Utilization (U)",
            value="-- %",
            subtitle="Derived: U = P / W * 100%",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.tp_card_utilization, 0, 2)

        self.tp_card_makespan = MetricCard(
            title="Parallel Makespan (T_par)",
            value="-- ms",
            subtitle="Direct: End-to-end wall clock",
            status_text="Pending",
            status_theme="neutral",
        )
        m_grid.addWidget(self.tp_card_makespan, 0, 3)
        layout.addLayout(m_grid)

        # Visualizations Row
        vis_row = QHBoxLayout()
        self.tp_chart_scalability = ScalabilityChartWidget()
        vis_row.addWidget(self.tp_chart_scalability, 1)

        self.tp_chart_timings = TimingBreakdownWidget()
        vis_row.addWidget(self.tp_chart_timings, 1)
        layout.addLayout(vis_row)

        # Iterations Table
        tbl_card = QFrame()
        tbl_card.setProperty("class", "card")
        t_layout = QVBoxLayout(tbl_card)
        t_title = QLabel("Task Parallelism Iteration Rollup")
        t_title.setProperty("class", "heading-2")
        t_layout.addWidget(t_title)

        self.tp_table = QTableWidget()
        self.tp_table.setColumnCount(7)
        self.tp_table.setHorizontalHeaderLabels([
            "Pass", "Type", "Seq Baseline (ms)", "Makespan (ms)", "Actual Speedup", "Worker Util %", "Verified"
        ])
        self.tp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tp_table.setMinimumHeight(150)
        t_layout.addWidget(self.tp_table)
        layout.addWidget(tbl_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 4: CPU SCHEDULING ANALYTICS
    # =========================================================================
    def _create_scheduling_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        c_title = QLabel("CPU Scheduling Algorithm Comparative Benchmark")
        c_title.setProperty("class", "heading-2")
        c_layout.addWidget(c_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Workload Preset:"), 0, 0)
        self.sched_combo_preset = QComboBox()
        for p in get_all_presets():
            self.sched_combo_preset.addItem(f"{p.name} ({len(p.processes)} Procs)", p.preset_id)
        grid.addWidget(self.sched_combo_preset, 0, 1)

        grid.addWidget(QLabel("Time Quantum:"), 0, 2)
        self.sched_spin_quantum = QDoubleSpinBox()
        self.sched_spin_quantum.setRange(0.5, 20.0)
        self.sched_spin_quantum.setValue(2.0)
        self.sched_spin_quantum.setSingleStep(0.5)
        grid.addWidget(self.sched_spin_quantum, 0, 3)

        grid.addWidget(QLabel("Context Switch Overhead:"), 1, 0)
        self.sched_spin_cs = QDoubleSpinBox()
        self.sched_spin_cs.setRange(0.0, 5.0)
        self.sched_spin_cs.setValue(0.1)
        self.sched_spin_cs.setSingleStep(0.1)
        grid.addWidget(self.sched_spin_cs, 1, 1)

        self.sched_btn_run = QPushButton("Compare All 6 Scheduling Algorithms")
        self.sched_btn_run.setProperty("class", "btn-primary")
        self.sched_btn_run.clicked.connect(self._run_sched_benchmark)
        grid.addWidget(self.sched_btn_run, 1, 2, 1, 2)

        c_layout.addLayout(grid)

        self.sched_status_lbl = QLabel("")
        self.sched_status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        c_layout.addWidget(self.sched_status_lbl)

        layout.addWidget(ctrl_card)

        # Summary Cards
        m_grid = QGridLayout()
        m_grid.setSpacing(12)

        self.sched_card_best_wait = MetricCard(
            title="Optimal Waiting Time",
            value="-- units",
            subtitle="Lowest average queueing latency",
            status_text="Simulated",
            status_theme="neutral",
        )
        m_grid.addWidget(self.sched_card_best_wait, 0, 0)

        self.sched_card_best_turnaround = MetricCard(
            title="Optimal Turnaround",
            value="-- units",
            subtitle="Lowest completion elapsed time",
            status_text="Simulated",
            status_theme="neutral",
        )
        m_grid.addWidget(self.sched_card_best_turnaround, 0, 1)

        self.sched_card_lowest_cs = MetricCard(
            title="Min Context Switches",
            value="-- switches",
            subtitle="Lowest preemption/dispatch cost",
            status_text="Simulated",
            status_theme="neutral",
        )
        m_grid.addWidget(self.sched_card_lowest_cs, 0, 2)

        self.sched_card_max_util = MetricCard(
            title="Peak CPU Utilization",
            value="-- %",
            subtitle="Active burst / total makespan",
            status_text="Simulated",
            status_theme="neutral",
        )
        m_grid.addWidget(self.sched_card_max_util, 0, 3)
        layout.addLayout(m_grid)

        # Comparison Table
        tbl_card = QFrame()
        tbl_card.setProperty("class", "card")
        t_layout = QVBoxLayout(tbl_card)
        t_title = QLabel("Cross-Algorithm Comparative Matrix")
        t_title.setProperty("class", "heading-2")
        t_layout.addWidget(t_title)

        self.sched_table = QTableWidget()
        self.sched_table.setColumnCount(7)
        self.sched_table.setHorizontalHeaderLabels([
            "Algorithm", "Type", "Avg Waiting", "Avg Turnaround", "Context Switches", "CPU Util %", "Throughput"
        ])
        self.sched_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sched_table.setMinimumHeight(220)
        t_layout.addWidget(self.sched_table)
        layout.addWidget(tbl_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 5: VIRTUAL LAB ANALYTICS
    # =========================================================================
    def _create_virtual_lab_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        c_title = QLabel("Virtual Lab Multicore Simulation Benchmark")
        c_title.setProperty("class", "heading-2")
        c_layout.addWidget(c_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Virtual Cores (N):"), 0, 0)
        self.vlab_spin_cores = QSpinBox()
        self.vlab_spin_cores.setRange(1, 32)
        self.vlab_spin_cores.setValue(8)
        grid.addWidget(self.vlab_spin_cores, 0, 1)

        grid.addWidget(QLabel("Virtual Task Load:"), 0, 2)
        self.vlab_spin_tasks = QSpinBox()
        self.vlab_spin_tasks.setRange(10, 500)
        self.vlab_spin_tasks.setValue(60)
        grid.addWidget(self.vlab_spin_tasks, 0, 3)

        grid.addWidget(QLabel("Hybrid P/E Architecture:"), 1, 0)
        self.vlab_combo_hybrid = QComboBox()
        self.vlab_combo_hybrid.addItem("Homogeneous Symmetrical Cores", False)
        self.vlab_combo_hybrid.addItem("Heterogeneous P-Core / E-Core Matrix", True)
        grid.addWidget(self.vlab_combo_hybrid, 1, 1)

        self.vlab_btn_run = QPushButton("Run Multicore Simulation Benchmark")
        self.vlab_btn_run.setProperty("class", "btn-primary")
        self.vlab_btn_run.clicked.connect(self._run_vlab_benchmark)
        grid.addWidget(self.vlab_btn_run, 1, 2, 1, 2)

        c_layout.addLayout(grid)

        self.vlab_status_lbl = QLabel("")
        self.vlab_status_lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
        c_layout.addWidget(self.vlab_status_lbl)

        layout.addWidget(ctrl_card)

        # Metrics Grid
        m_grid = QGridLayout()
        m_grid.setSpacing(12)

        self.vlab_card_ticks = MetricCard(
            title="Simulation Duration",
            value="-- ticks",
            subtitle="Simulated discrete clock steps",
            status_text="Simulated Virtual",
            status_theme="warning",
        )
        m_grid.addWidget(self.vlab_card_ticks, 0, 0)

        self.vlab_card_util = MetricCard(
            title="Virtual Core Utilization",
            value="-- %",
            subtitle="Capacity: sum(busy_ticks) / (N * makespan)",
            status_text="Simulated Virtual",
            status_theme="warning",
        )
        m_grid.addWidget(self.vlab_card_util, 0, 1)

        self.vlab_card_throughput = MetricCard(
            title="Simulator Wall-Clock Time",
            value="-- ms",
            subtitle="Monotonic process execution duration",
            status_text="Directly Measured",
            status_theme="success",
        )
        m_grid.addWidget(self.vlab_card_throughput, 0, 2)

        self.vlab_card_verified = MetricCard(
            title="Task Completion Integrity",
            value="--",
            subtitle="100% of submitted tasks executed",
            status_text="Simulated Virtual",
            status_theme="warning",
        )
        m_grid.addWidget(self.vlab_card_verified, 0, 3)
        layout.addLayout(m_grid)

        # Educational Explainer Card
        edu_card = QFrame()
        edu_card.setProperty("class", "card-alt")
        e_layout = QVBoxLayout(edu_card)
        e_title = QLabel("Educational Note: Virtual Discrete Ticks vs Physical Time")
        e_title.setProperty("class", "heading-2")
        e_layout.addWidget(e_title)

        e_desc = QLabel(
            "The Virtual Lab simulates execution in discrete, deterministic logical units ('ticks'). "
            "Unlike real multiprocessing, where one second corresponds to billions of CPU clock cycles subjected to OS context switching, "
            "the Virtual Lab step() method executes synchronously without spawning actual OS threads. "
            "This pedagogical abstraction enables students and engineers to isolate algorithm logic from hardware noise."
        )
        e_desc.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        e_layout.addWidget(e_desc)
        layout.addWidget(edu_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 6: BENCHMARK HISTORY
    # =========================================================================
    def _create_history_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QHBoxLayout(ctrl_card)
        c_layout.setContentsMargins(16, 12, 16, 12)

        t_lbl = QLabel("Persisted Benchmark Session Archive")
        t_lbl.setProperty("class", "heading-2")
        c_layout.addWidget(t_lbl)
        c_layout.addStretch(1)

        self.hist_btn_refresh = QPushButton("Refresh Archive")
        self.hist_btn_refresh.clicked.connect(self._refresh_history_table)
        c_layout.addWidget(self.hist_btn_refresh)

        self.hist_btn_delete = QPushButton("Delete Selected")
        self.hist_btn_delete.setProperty("class", "btn-danger")
        self.hist_btn_delete.clicked.connect(self._delete_selected_history)
        c_layout.addWidget(self.hist_btn_delete)

        self.hist_btn_clear = QPushButton("Clear All")
        self.hist_btn_clear.clicked.connect(self._clear_all_history)
        c_layout.addWidget(self.hist_btn_clear)

        layout.addWidget(ctrl_card)

        # History Table
        self.hist_table = QTableWidget()
        self.hist_table.setColumnCount(8)
        self.hist_table.setHorizontalHeaderLabels([
            "Benchmark ID", "Engine", "Workload", "Workers", "Mean Speedup", "Mean Eff %", "Date", "Verified"
        ])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.hist_table.itemSelectionChanged.connect(self._on_history_row_selected)
        self.hist_table.setMinimumHeight(240)
        layout.addWidget(self.hist_table)

        # Details Viewer
        det_card = QFrame()
        det_card.setProperty("class", "card-alt")
        d_layout = QVBoxLayout(det_card)
        d_title = QLabel("Selected Benchmark Run Inspection & Multi-Run Statistics")
        d_title.setProperty("class", "heading-2")
        d_layout.addWidget(d_title)

        self.hist_details_text = QTextEdit()
        self.hist_details_text.setReadOnly(True)
        self.hist_details_text.setMinimumHeight(180)
        self.hist_details_text.setStyleSheet(
            "background-color: #0d1117; color: #c9d1d9; font-family: monospace; font-size: 11px;"
        )
        d_layout.addWidget(self.hist_details_text)
        layout.addWidget(det_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # TAB 7: AMDAHL'S LAW CALCULATOR
    # =========================================================================
    def _create_amdahl_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(16)
        scroll.setWidget(container)

        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(14)

        c_title = QLabel("Amdahl's Law Theoretical Scalability Modeler")
        c_title.setProperty("class", "heading-2")
        c_layout.addWidget(c_title)

        c_desc = QLabel(
            "Gene Amdahl's 1967 Law dictates the maximum theoretical speedup achievable by parallelizing a fixed workload: "
            "Speedup(P, N) = 1 / ((1 - P) + P / N), where P is the parallelizable fraction and N is the processor count."
        )
        c_desc.setStyleSheet("color: #8b949e; line-height: 1.4;")
        c_layout.addWidget(c_desc)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Parallel Fraction Slider
        grid.addWidget(QLabel("Parallel Fraction (P):"), 0, 0)
        self.amdahl_slider_p = QSlider(Qt.Horizontal)
        self.amdahl_slider_p.setRange(0, 100)
        self.amdahl_slider_p.setValue(85)
        self.amdahl_slider_p.valueChanged.connect(self._on_amdahl_slider_changed)
        grid.addWidget(self.amdahl_slider_p, 0, 1)

        self.amdahl_lbl_p_val = QLabel("85.0% (Serial: 15.0%)")
        self.amdahl_lbl_p_val.setStyleSheet("font-weight: bold; color: #58a6ff;")
        grid.addWidget(self.amdahl_lbl_p_val, 0, 2)

        # Processor Count Slider
        grid.addWidget(QLabel("Processors / Cores (N):"), 1, 0)
        self.amdahl_slider_n = QSlider(Qt.Horizontal)
        self.amdahl_slider_n.setRange(1, 64)
        self.amdahl_slider_n.setValue(8)
        self.amdahl_slider_n.valueChanged.connect(self._on_amdahl_slider_changed)
        grid.addWidget(self.amdahl_slider_n, 1, 1)

        self.amdahl_lbl_n_val = QLabel("8 Cores")
        self.amdahl_lbl_n_val.setStyleSheet("font-weight: bold; color: #3fb950;")
        grid.addWidget(self.amdahl_lbl_n_val, 1, 2)

        c_layout.addLayout(grid)
        layout.addWidget(ctrl_card)

        # Metrics Grid
        m_grid = QGridLayout()
        m_grid.setSpacing(12)

        self.amdahl_card_speedup = MetricCard(
            title="Theoretical Speedup S(P, N)",
            value="-- x",
            subtitle="Formula: 1 / ((1 - P) + P / N)",
            status_text="Amdahl Model",
            status_theme="info",
        )
        m_grid.addWidget(self.amdahl_card_speedup, 0, 0)

        self.amdahl_card_eff = MetricCard(
            title="Theoretical Efficiency",
            value="-- %",
            subtitle="Formula: Speedup / N * 100%",
            status_text="Amdahl Model",
            status_theme="info",
        )
        m_grid.addWidget(self.amdahl_card_eff, 0, 1)

        self.amdahl_card_max_speedup = MetricCard(
            title="Maximum Asymptote (S_max)",
            value="-- x",
            subtitle="Formula: 1 / (1 - P) as N -> inf",
            status_text="Amdahl Limit",
            status_theme="warning",
        )
        m_grid.addWidget(self.amdahl_card_max_speedup, 0, 2)

        self.amdahl_card_serial_frac = MetricCard(
            title="Serial Bottleneck (1 - P)",
            value="-- %",
            subtitle="Unparallelizable sequential fraction",
            status_text="Serial Constraint",
            status_theme="danger",
        )
        m_grid.addWidget(self.amdahl_card_serial_frac, 0, 3)
        layout.addLayout(m_grid)

        # Interactive Canvas
        chart_card = QFrame()
        chart_card.setProperty("class", "card")
        ch_layout = QVBoxLayout(chart_card)
        ch_layout.setSpacing(10)
        ch_title = QLabel("Theoretical Speedup Curve vs Processors Sweep")
        ch_title.setProperty("class", "heading-2")
        ch_layout.addWidget(ch_title)

        self.amdahl_chart = AmdahlCurveWidget()
        ch_layout.addWidget(self.amdahl_chart)
        layout.addWidget(chart_card)

        # Educational Assumptions & Limitations Panel
        limit_card = QFrame()
        limit_card.setProperty("class", "card-alt")
        l_layout = QVBoxLayout(limit_card)
        l_layout.setSpacing(10)

        l_title = QLabel("Fundamental Assumptions & Limitations of Amdahl's Law")
        l_title.setProperty("class", "heading-2")
        l_layout.addWidget(l_title)

        limits = AmdahlCalculator.explain_limitations()
        bullets = (
            f"1. Strong Scaling (Fixed Problem Size): {limits['fixed_problem_size']}\n\n"
            f"2. Zero Communication Overhead: {limits['zero_communication_overhead']}\n\n"
            f"3. Homogeneous Hardware Assumption: {limits['homogeneous_hardware_assumption']}\n\n"
            f"4. Memory Bus & Cache Contention: {limits['memory_bus_and_cache_contention']}"
        )
        l_text = QLabel(bullets)
        l_text.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        l_layout.addWidget(l_text)
        layout.addWidget(limit_card)

        layout.addStretch(1)
        return scroll

    # =========================================================================
    # BENCHMARK EXECUTION SLOTS & COORDINATION
    # =========================================================================
    @Slot()
    def _run_dp_benchmark(self) -> None:
        op_id = self.dp_combo_op.currentData()
        size = self.dp_spin_size.value()
        workers = self.dp_spin_workers.value()
        repeats = self.dp_spin_repeats.value()
        warmup = self.dp_spin_warmup.value()

        self._active_tab_engine = BenchmarkEngineType.DATA_PARALLEL
        self.dp_btn_run.setEnabled(False)
        self.dp_btn_cancel.setEnabled(True)
        self.dp_progress.setVisible(True)
        self.dp_progress.setValue(0)
        self.dp_status_lbl.setText("Starting Data Parallel benchmark sweep...")

        self._runner_thread.configure_data_parallel(
            op_id=op_id,
            dataset_size=size,
            worker_count=workers,
            iterations=repeats,
            warmup_runs=warmup,
        )
        self._runner_thread.start()

    @Slot()
    def _run_tp_benchmark(self) -> None:
        dag_type = self.tp_combo_dag.currentData()
        workers = self.tp_spin_workers.value()
        repeats = self.tp_spin_repeats.value()
        warmup = self.tp_spin_warmup.value()

        self._active_tab_engine = BenchmarkEngineType.TASK_PARALLEL
        self.tp_btn_run.setEnabled(False)
        self.tp_btn_cancel.setEnabled(True)
        self.tp_progress.setVisible(True)
        self.tp_progress.setValue(0)
        self.tp_status_lbl.setText("Starting Task Parallel DAG benchmark sweep...")

        self._runner_thread.configure_task_parallel(
            dag_type=dag_type,
            worker_count=workers,
            iterations=repeats,
            warmup_runs=warmup,
        )
        self._runner_thread.start()

    @Slot()
    def _run_sched_benchmark(self) -> None:
        preset_id = self.sched_combo_preset.currentData()
        quantum = self.sched_spin_quantum.value()
        cs = self.sched_spin_cs.value()

        self._active_tab_engine = BenchmarkEngineType.CPU_SCHEDULING
        self.sched_btn_run.setEnabled(False)
        self.sched_status_lbl.setText("Executing algorithm comparison matrix...")

        self._runner_thread.configure_scheduling(
            preset_id=preset_id,
            time_quantum=quantum,
            context_switch_overhead=cs,
        )
        self._runner_thread.start()

    @Slot()
    def _run_vlab_benchmark(self) -> None:
        cores = self.vlab_spin_cores.value()
        tasks = self.vlab_spin_tasks.value()
        hybrid = bool(self.vlab_combo_hybrid.currentData())

        self._active_tab_engine = BenchmarkEngineType.VIRTUAL_LAB
        self.vlab_btn_run.setEnabled(False)
        self.vlab_status_lbl.setText("Running virtual multicore dispatch simulation...")

        self._runner_thread.configure_virtual_lab(
            virtual_cores=cores,
            task_count=tasks,
            enable_hybrid=hybrid,
        )
        self._runner_thread.start()

    @Slot()
    def _cancel_running_benchmark(self) -> None:
        self._runner_thread.cancel()
        if self._active_tab_engine == BenchmarkEngineType.DATA_PARALLEL:
            self.dp_status_lbl.setText("Cancellation requested...")
        elif self._active_tab_engine == BenchmarkEngineType.TASK_PARALLEL:
            self.tp_status_lbl.setText("Cancellation requested...")

    @Slot(int, int, str)
    def _on_progress_updated(self, cur: int, total: int, msg: str) -> None:
        pct = int((cur / max(1, total)) * 100)
        if self._active_tab_engine == BenchmarkEngineType.DATA_PARALLEL:
            self.dp_progress.setValue(pct)
            self.dp_status_lbl.setText(msg)
        elif self._active_tab_engine == BenchmarkEngineType.TASK_PARALLEL:
            self.tp_progress.setValue(pct)
            self.tp_status_lbl.setText(msg)

    @Slot(object)
    def _on_benchmark_finished(self, session: BenchmarkSessionResult) -> None:
        # Save session to persistent history manager
        try:
            self._history_mgr.save_session(session)
        except Exception:
            pass

        # Update Dashboard global cards
        self._update_dashboard_summary()

        # Update UI according to active engine
        if session.engine_type == BenchmarkEngineType.DATA_PARALLEL:
            self._render_dp_results(session)
        elif session.engine_type == BenchmarkEngineType.TASK_PARALLEL:
            self._render_tp_results(session)
        elif session.engine_type == BenchmarkEngineType.CPU_SCHEDULING:
            self._render_sched_results(session)
        elif session.engine_type == BenchmarkEngineType.VIRTUAL_LAB:
            self._render_vlab_results(session)

        self._refresh_history_table()

    @Slot(str)
    def _on_benchmark_failed(self, error_msg: str) -> None:
        if self._active_tab_engine == BenchmarkEngineType.DATA_PARALLEL:
            self.dp_btn_run.setEnabled(True)
            self.dp_btn_cancel.setEnabled(False)
            self.dp_progress.setVisible(False)
            self.dp_status_lbl.setText(f"Error: {error_msg}")
        elif self._active_tab_engine == BenchmarkEngineType.TASK_PARALLEL:
            self.tp_btn_run.setEnabled(True)
            self.tp_btn_cancel.setEnabled(False)
            self.tp_progress.setVisible(False)
            self.tp_status_lbl.setText(f"Error: {error_msg}")
        elif self._active_tab_engine == BenchmarkEngineType.CPU_SCHEDULING:
            self.sched_btn_run.setEnabled(True)
            self.sched_status_lbl.setText(f"Error: {error_msg}")
        elif self._active_tab_engine == BenchmarkEngineType.VIRTUAL_LAB:
            self.vlab_btn_run.setEnabled(True)
            self.vlab_status_lbl.setText(f"Error: {error_msg}")

    # =========================================================================
    # RENDER RESULT HELPERS
    # =========================================================================
    def _render_dp_results(self, session: BenchmarkSessionResult) -> None:
        self.dp_btn_run.setEnabled(True)
        self.dp_btn_cancel.setEnabled(False)
        self.dp_progress.setVisible(False)

        mean_speedup = session.statistics.get("speedup", {}).get("mean", 0.0)
        mean_eff = session.statistics.get("efficiency_pct", {}).get("mean", 0.0)
        mean_thru = session.statistics.get("throughput", {}).get("mean", 0.0)

        speedup_std = session.statistics.get("speedup", {}).get("std_dev")
        eff_std = session.statistics.get("efficiency_pct", {}).get("std_dev")

        speedup_sub = f"StdDev: ±{speedup_std:.2f}" if speedup_std is not None else "N/A (N=1 iteration)"
        eff_sub = f"StdDev: ±{eff_std:.1f}%" if eff_std is not None else "N/A (N=1 iteration)"

        # Calculate average no-worker-compute time
        all_recs = session.measured_records
        avg_overhead_ms = 0.0
        if all_recs:
            overheads = [
                r.extra_metrics.get("no_worker_compute_time_s", r.extra_metrics.get("idle_gap_time_s", r.extra_metrics.get("aggregate_estimated_residual_s", 0.0))) * 1000.0
                for r in all_recs
            ]
            avg_overhead_ms = max(0.0, sum(overheads) / len(overheads))

        v_text = "Verified Equivalence" if session.verification_passed else "Verification Failed"
        v_theme = "success" if session.verification_passed else "danger"

        self.dp_card_speedup.set_value(f"{mean_speedup:.2f} x", speedup_sub, v_theme, v_text)
        self.dp_card_efficiency.set_value(f"{mean_eff:.1f} %", eff_sub, v_theme, v_text)
        self.dp_card_throughput.set_value(f"{mean_thru:,.0f} it/s", f"{session.workload_name}", v_theme, v_text)
        self.dp_card_overhead.set_value(f"{avg_overhead_ms:.2f} ms", "Makespan - Compute Interval Union", "info", "Mathematically Derived")

        self.dp_status_lbl.setText(f"Benchmark completed in {session.total_wall_clock_s:.2f}s ({len(session.measured_records)} measured passes).")

        # Update Iterations Table
        self.dp_table.setRowCount(len(session.warmup_records) + len(session.measured_records))
        row = 0
        for r in session.warmup_records:
            self.dp_table.setItem(row, 0, QTableWidgetItem(f"W-{r.iteration_idx}"))
            self.dp_table.setItem(row, 1, QTableWidgetItem("Warm-up"))
            self.dp_table.setItem(row, 2, QTableWidgetItem(f"{r.sequential_time_s * 1000.0:.2f}"))
            self.dp_table.setItem(row, 3, QTableWidgetItem(f"{r.parallel_time_s * 1000.0:.2f}"))
            self.dp_table.setItem(row, 4, QTableWidgetItem(f"{r.speedup:.2f}x"))
            self.dp_table.setItem(row, 5, QTableWidgetItem(f"{r.efficiency_pct:.1f}%"))
            self.dp_table.setItem(row, 6, QTableWidgetItem("Pass" if r.verification_passed else "Fail"))
            row += 1

        for r in session.measured_records:
            self.dp_table.setItem(row, 0, QTableWidgetItem(f"M-{r.iteration_idx}"))
            self.dp_table.setItem(row, 1, QTableWidgetItem("Measured"))
            self.dp_table.setItem(row, 2, QTableWidgetItem(f"{r.sequential_time_s * 1000.0:.2f}"))
            self.dp_table.setItem(row, 3, QTableWidgetItem(f"{r.parallel_time_s * 1000.0:.2f}"))
            self.dp_table.setItem(row, 4, QTableWidgetItem(f"{r.speedup:.2f}x"))
            self.dp_table.setItem(row, 5, QTableWidgetItem(f"{r.efficiency_pct:.1f}%"))
            self.dp_table.setItem(row, 6, QTableWidgetItem("Pass" if r.verification_passed else "Fail"))
            row += 1

        # Update Charts
        if session.measured_records:
            last = session.measured_records[-1]
            workers = session.worker_count
            pts = [(1, 1.0, 100.0), (workers, last.speedup, last.efficiency_pct)]
            self.dp_chart_scalability.set_data(pts, title=f"Speedup ({session.workload_name})")

            comp_union = last.extra_metrics.get("compute_interval_union_s", max(0.0, last.parallel_time_s - last.extra_metrics.get("no_worker_compute_time_s", last.extra_metrics.get("idle_gap_time_s", 0.0))))
            no_compute_gap = last.extra_metrics.get("no_worker_compute_time_s", last.extra_metrics.get("idle_gap_time_s", last.extra_metrics.get("aggregate_estimated_residual_s", 0.0)))
            timings = {
                "startup_s": last.extra_metrics.get("startup_s", 0.0),
                "dispatch_s": last.extra_metrics.get("dispatch_s", 0.0),
                "compute_s": comp_union,
                "collection_s": last.extra_metrics.get("collection_s", 0.0),
                "merge_s": last.extra_metrics.get("merge_s", 0.0),
                "residual_s": no_compute_gap,
            }
            self.dp_chart_timings.set_timings(timings)

    def _render_tp_results(self, session: BenchmarkSessionResult) -> None:
        self.tp_btn_run.setEnabled(True)
        self.tp_btn_cancel.setEnabled(False)
        self.tp_progress.setVisible(False)

        mean_speedup = session.statistics.get("speedup", {}).get("mean", 0.0)
        speedup_std = session.statistics.get("speedup", {}).get("std_dev")
        speedup_sub = f"StdDev: ±{speedup_std:.2f}" if speedup_std is not None else "N/A (N=1 iteration)"

        last_rec = session.measured_records[-1] if session.measured_records else None
        p_ratio = last_rec.extra_metrics.get("parallelism_ratio", 0.0) if last_rec else 0.0
        util_pct = last_rec.extra_metrics.get("worker_utilization_pct", 0.0) if last_rec else 0.0
        makespan_ms = (last_rec.parallel_time_s * 1000.0) if last_rec else 0.0

        v_text = "Verified Equivalence" if session.verification_passed else "Verification Failed"
        v_theme = "success" if session.verification_passed else "danger"

        self.tp_card_actual_speedup.set_value(f"{mean_speedup:.2f} x", speedup_sub, v_theme, v_text)
        self.tp_card_parallelism_ratio.set_value(f"{p_ratio:.2f} x", "Concurrency density", "info", "Mathematically Derived")
        self.tp_card_utilization.set_value(f"{util_pct:.1f} %", "Worker core busy ratio", "info", "Mathematically Derived")
        self.tp_card_makespan.set_value(f"{makespan_ms:.1f} ms", f"{session.workload_name}", "success", "Directly Measured")

        self.tp_status_lbl.setText(f"DAG Benchmark completed in {session.total_wall_clock_s:.2f}s.")

        # Update Table
        self.tp_table.setRowCount(len(session.warmup_records) + len(session.measured_records))
        row = 0
        for r in session.warmup_records:
            self.tp_table.setItem(row, 0, QTableWidgetItem(f"W-{r.iteration_idx}"))
            self.tp_table.setItem(row, 1, QTableWidgetItem("Warm-up"))
            self.tp_table.setItem(row, 2, QTableWidgetItem(f"{r.sequential_time_s * 1000.0:.2f}"))
            self.tp_table.setItem(row, 3, QTableWidgetItem(f"{r.parallel_time_s * 1000.0:.2f}"))
            self.tp_table.setItem(row, 4, QTableWidgetItem(f"{r.speedup:.2f}x"))
            self.tp_table.setItem(row, 5, QTableWidgetItem(f"{r.extra_metrics.get('worker_utilization_pct', 0.0):.1f}%"))
            self.tp_table.setItem(row, 6, QTableWidgetItem("Pass" if r.verification_passed else "Fail"))
            row += 1

        for r in session.measured_records:
            self.tp_table.setItem(row, 0, QTableWidgetItem(f"M-{r.iteration_idx}"))
            self.tp_table.setItem(row, 1, QTableWidgetItem("Measured"))
            self.tp_table.setItem(row, 2, QTableWidgetItem(f"{r.sequential_time_s * 1000.0:.2f}"))
            self.tp_table.setItem(row, 3, QTableWidgetItem(f"{r.parallel_time_s * 1000.0:.2f}"))
            self.tp_table.setItem(row, 4, QTableWidgetItem(f"{r.speedup:.2f}x"))
            self.tp_table.setItem(row, 5, QTableWidgetItem(f"{r.extra_metrics.get('worker_utilization_pct', 0.0):.1f}%"))
            self.tp_table.setItem(row, 6, QTableWidgetItem("Pass" if r.verification_passed else "Fail"))
            row += 1

        if session.measured_records:
            last = session.measured_records[-1]
            workers = session.worker_count
            pts = [(1, 1.0, 100.0), (workers, last.speedup, last.efficiency_pct)]
            self.tp_chart_scalability.set_data(pts, title=f"Speedup ({session.workload_name})")

            # Timing breakdown
            comp_union = last.extra_metrics.get("compute_interval_union_s", last.parallel_time_s)
            no_compute_gap = last.extra_metrics.get("no_worker_compute_time_s", last.extra_metrics.get("idle_gap_time_s", max(0.0, last.parallel_time_s - comp_union)))
            timings = {
                "compute_s": comp_union,
                "residual_s": max(0.0, no_compute_gap),
            }
            self.tp_chart_timings.set_timings(timings)

    def _render_sched_results(self, session: BenchmarkSessionResult) -> None:
        self.sched_btn_run.setEnabled(True)
        self.sched_status_lbl.setText("Algorithm matrix comparison complete.")

        recs = session.measured_records
        if not recs:
            return

        # Find best waiting, best turnaround, min CS, max util
        best_wait = min(recs, key=lambda r: r.extra_metrics.get("average_waiting_time", 9999.0))
        best_turn = min(recs, key=lambda r: r.extra_metrics.get("average_turnaround_time", 9999.0))
        min_cs = min(recs, key=lambda r: r.extra_metrics.get("context_switches", 9999))
        max_util = max(recs, key=lambda r: r.efficiency_pct)

        self.sched_card_best_wait.set_value(
            f"{best_wait.extra_metrics.get('average_waiting_time', 0.0):.2f}",
            f"Best: {best_wait.extra_metrics.get('algorithm_name', '')}",
            "success",
            "Optimal",
        )
        self.sched_card_best_turnaround.set_value(
            f"{best_turn.extra_metrics.get('average_turnaround_time', 0.0):.2f}",
            f"Best: {best_turn.extra_metrics.get('algorithm_name', '')}",
            "success",
            "Optimal",
        )
        self.sched_card_lowest_cs.set_value(
            f"{min_cs.extra_metrics.get('context_switches', 0)} switches",
            f"Best: {min_cs.extra_metrics.get('algorithm_name', '')}",
            "info",
            "Minimal",
        )
        self.sched_card_max_util.set_value(
            f"{max_util.efficiency_pct:.1f} %",
            f"Best: {max_util.extra_metrics.get('algorithm_name', '')}",
            "success",
            "Peak",
        )

        # Populate Table
        self.sched_table.setRowCount(len(recs))
        for row, r in enumerate(recs):
            m = r.extra_metrics
            self.sched_table.setItem(row, 0, QTableWidgetItem(m.get("algorithm_name", "")))
            self.sched_table.setItem(row, 1, QTableWidgetItem(m.get("algorithm_type", "")))
            self.sched_table.setItem(row, 2, QTableWidgetItem(f"{m.get('average_waiting_time', 0.0):.2f}"))
            self.sched_table.setItem(row, 3, QTableWidgetItem(f"{m.get('average_turnaround_time', 0.0):.2f}"))
            self.sched_table.setItem(row, 4, QTableWidgetItem(str(m.get("context_switches", 0))))
            self.sched_table.setItem(row, 5, QTableWidgetItem(f"{r.efficiency_pct:.1f}%"))
            self.sched_table.setItem(row, 6, QTableWidgetItem(f"{r.throughput:.2f}"))

    def _render_vlab_results(self, session: BenchmarkSessionResult) -> None:
        self.vlab_btn_run.setEnabled(True)
        self.vlab_status_lbl.setText("Virtual Lab multicore simulation complete.")

        recs = session.measured_records
        if not recs:
            return
        r = recs[0]
        m = r.extra_metrics

        ticks = m.get("simulated_ticks_elapsed", m.get("ticks_elapsed", 0))
        virtual_util = m.get("virtual_core_util_pct", m.get("virtual_util_pct", 0.0))
        wall_clock_s = m.get("simulator_wall_clock_s", session.total_wall_clock_s)
        completed = m.get("completed_tasks", 0)
        total_tasks = session.config_parameters.get("task_count", completed)

        self.vlab_card_ticks.set_value(
            f"{ticks} ticks",
            f"Simulated Clock ({session.workload_name})",
            "warning",
            "Simulated Virtual",
        )
        self.vlab_card_util.set_value(
            f"{virtual_util:.1f} %",
            f"{session.worker_count} Virtual Cores Capacity",
            "warning",
            "Simulated Virtual",
        )
        self.vlab_card_throughput.set_value(
            f"{wall_clock_s * 1000.0:.2f} ms",
            "Direct Monotonic Wall-Clock Time",
            "success",
            "Directly Measured",
        )
        self.vlab_card_verified.set_value(
            f"{completed} / {total_tasks}",
            "Deterministic Virtual Completion",
            "warning",
            "Simulated Virtual",
        )

    # =========================================================================
    # AMDAHL'S LAW SLIDER HANDLING
    # =========================================================================
    @Slot()
    def _on_amdahl_slider_changed(self) -> None:
        self._update_amdahl_display()

    def _update_amdahl_display(self) -> None:
        p_pct = self.amdahl_slider_p.value()
        p = p_pct / 100.0
        n = self.amdahl_slider_n.value()

        pred = AmdahlCalculator.predict(parallel_fraction=p, processors=n)

        self.amdahl_lbl_p_val.setText(f"{p_pct:.1f}% (Serial: {pred.serial_fraction * 100.0:.1f}%)")
        self.amdahl_lbl_n_val.setText(f"{n} Cores")

        s_str = f"{pred.theoretical_speedup:.2f} x"
        eff_str = f"{pred.theoretical_efficiency_pct:.1f} %"
        if math.isinf(pred.theoretical_max_speedup):
            max_s_str = "Unbounded (∞)"
            max_s_sub = "S_max as N -> ∞ (Zero Serial Bottleneck)"
        else:
            max_s_str = f"{pred.theoretical_max_speedup:.2f} x"
            max_s_sub = "S_max as N -> ∞ (Amdahl Asymptote)"
        ser_str = f"{pred.serial_fraction * 100.0:.1f} %"

        self.amdahl_card_speedup.set_value(s_str, f"Speedup on {n} Cores", "info", "Theoretical")
        self.amdahl_card_eff.set_value(eff_str, f"Efficiency on {n} Cores", "info", "Theoretical")
        self.amdahl_card_max_speedup.set_value(max_s_str, max_s_sub, "warning", "Theoretical Limit")
        self.amdahl_card_serial_frac.set_value(ser_str, "Mandatory serial portion", "danger", "Constraint")

        self.amdahl_chart.set_parameters(parallel_fraction=p, operating_processors=n, max_processors=32)

    # =========================================================================
    # BENCHMARK HISTORY TABLE
    # =========================================================================
    def _refresh_history_table(self) -> None:
        summaries = self._history_mgr.list_summaries()
        self.hist_table.setRowCount(len(summaries))

        for row, s in enumerate(summaries):
            self.hist_table.setItem(row, 0, QTableWidgetItem(s.get("benchmark_id", "")))
            self.hist_table.setItem(row, 1, QTableWidgetItem(s.get("engine_name", str(s.get("engine_type", "")))))
            self.hist_table.setItem(row, 2, QTableWidgetItem(s.get("workload_name", "")))
            self.hist_table.setItem(row, 3, QTableWidgetItem(str(s.get("worker_count", 1))))
            self.hist_table.setItem(row, 4, QTableWidgetItem(f"{s.get('mean_speedup', 1.0):.2f}x"))
            self.hist_table.setItem(row, 5, QTableWidgetItem(f"{s.get('mean_efficiency_pct', 100.0):.1f}%"))
            # format date
            ts = s.get("start_timestamp", "")
            dt_str = ts[:19].replace("T", " ") if "T" in ts else ts
            self.hist_table.setItem(row, 6, QTableWidgetItem(dt_str))
            self.hist_table.setItem(row, 7, QTableWidgetItem("Pass" if s.get("verification_passed", False) else "Fail"))

        self._update_dashboard_summary()

    def _update_dashboard_summary(self) -> None:
        summaries = self._history_mgr.list_summaries()
        self.dash_card_sessions.set_value(
            str(len(summaries)),
            "Persistent JSON session runs",
            "success",
            "Directly Measured",
        )
        if summaries:
            max_s = max(s.get("mean_speedup", 1.0) for s in summaries)
            max_e = max(s.get("mean_efficiency_pct", 100.0) for s in summaries)
            self.dash_card_speedup.set_value(f"{max_s:.2f} x", "Across all historical sweeps", "info", "Derived")
            self.dash_card_efficiency.set_value(f"{max_e:.1f} %", "Across all historical sweeps", "info", "Derived")

    @Slot()
    def _on_history_row_selected(self) -> None:
        selected_rows = self.hist_table.selectionModel().selectedRows()
        if not selected_rows:
            self.hist_details_text.setText("")
            return

        row = selected_rows[0].row()
        b_id_item = self.hist_table.item(row, 0)
        if not b_id_item:
            return

        b_id = b_id_item.text()
        session = self._history_mgr.load_session(b_id)
        if not session:
            self.hist_details_text.setText(f"Unable to load session {b_id}")
            return

        import json
        payload = session.to_dict() if hasattr(session, "to_dict") else session
        details_json = json.dumps(payload, indent=2)
        self.hist_details_text.setText(details_json)

    @Slot()
    def _delete_selected_history(self) -> None:
        selected_rows = self.hist_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        b_id_item = self.hist_table.item(row, 0)
        if b_id_item:
            self._history_mgr.delete_session(b_id_item.text())
            self._refresh_history_table()
            self.hist_details_text.setText("")

    @Slot()
    def _clear_all_history(self) -> None:
        self._history_mgr.clear_all()
        self._refresh_history_table()
        self.hist_details_text.setText("")
