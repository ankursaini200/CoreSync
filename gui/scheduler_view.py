"""Interactive CPU Scheduling Simulator View for CoreSync Workstation.

Provides full process input management, scheduling algorithm configuration,
live Gantt chart timeline rendering, execution results table, summary metrics,
and multi-algorithm comparison benchmark.
"""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.process_scheduler import (
    AlgorithmType,
    ComparisonSummaryRow,
    PriorityDirection,
    Process,
    ProcessSchedulerSimulator,
    SimulationResult,
    compare_all_algorithms,
    get_all_presets,
    get_preset_by_id,
)
from gui.components.badge import StatusBadge
from gui.components.gantt_canvas import GanttCanvasWidget
from gui.components.metric_card import MetricCard


class ComparisonDialog(QDialog):
    """Modal dialog displaying side-by-side comparative benchmark metrics."""

    def __init__(self, rows: List[ComparisonSummaryRow], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Algorithm Comparison Benchmark")
        self.resize(880, 420)
        self.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("CPU Scheduling Algorithm Comparative Analysis")
        header.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        layout.addWidget(header)

        notice = QLabel(
            "All algorithms were executed on the identical process dataset with the configured parameters. "
            "Examine differences in average waiting time, response time, and context switches."
        )
        notice.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(notice)

        table = QTableWidget(len(rows), 8, self)
        table.setHorizontalHeaderLabels([
            "Algorithm",
            "Avg Waiting",
            "Avg Turnaround",
            "Avg Response",
            "CPU Utilization",
            "Throughput",
            "Context Switches",
            "Total Time",
        ])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, 8):
            table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #161b24;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QHeaderView::section {
                background-color: #1c2330;
                color: #c9d1d9;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #30363d;
            }
        """)

        # Identify minimum waiting time for subtle highlighting
        min_wt = min(r.average_waiting_time for r in rows) if rows else 0.0

        for row_idx, r in enumerate(rows):
            name_item = QTableWidgetItem(r.algorithm_name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row_idx, 0, name_item)

            wt_item = QTableWidgetItem(f"{r.average_waiting_time:.2f} ms")
            wt_item.setTextAlignment(Qt.AlignCenter)
            if abs(r.average_waiting_time - min_wt) < 1e-4:
                wt_item.setForeground(Qt.green)
            table.setItem(row_idx, 1, wt_item)

            tat_item = QTableWidgetItem(f"{r.average_turnaround_time:.2f} ms")
            tat_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 2, tat_item)

            rt_item = QTableWidgetItem(f"{r.average_response_time:.2f} ms")
            rt_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 3, rt_item)

            util_item = QTableWidgetItem(f"{r.cpu_utilization_pct:.1f}%")
            util_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 4, util_item)

            tp_item = QTableWidgetItem(f"{r.throughput:.3f} p/ms")
            tp_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 5, tp_item)

            cs_item = QTableWidgetItem(str(r.context_switches))
            cs_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 6, cs_item)

            tot_item = QTableWidgetItem(f"{r.total_simulation_time:.2f} ms")
            tot_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, 7, tot_item)

        layout.addWidget(table)

        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        btn_close = QPushButton("Close")
        btn_close.setProperty("class", "btn-secondary")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)
        layout.addLayout(btn_box)


class SchedulerViewPage(QWidget):
    """Interactive Educational CPU Scheduling Simulator View."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._processes: List[Process] = []
        self._last_simulation_result: Optional[SimulationResult] = None
        self._next_pid_counter: int = 1

        self._setup_ui()
        self._load_default_preset()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(18)
        scroll.setWidget(container)

        # 1. Header Card with Presets
        layout.addWidget(self._create_header_card())

        # 2. Process Input & Batch Management Card
        layout.addWidget(self._create_process_input_card())

        # 3. Algorithm Dispatch Configuration Card
        layout.addWidget(self._create_algorithm_config_card())

        # 4. Gantt Timeline Visualization
        self.gantt_widget = GanttCanvasWidget(self)
        layout.addWidget(self.gantt_widget)

        # 5. Summary Metrics Grid
        layout.addLayout(self._create_metrics_grid())

        # 6. Process Execution Results Table
        layout.addWidget(self._create_results_table_card())

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("CPU Scheduling Simulator & Timeline Visualizer")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Simulate classical CPU scheduling algorithms (FCFS, SJF, SRTF, Priority with Aging, and Round Robin). "
            "Generate deterministic execution timelines, analyze Gantt event blocks, and compare throughput and turnaround metrics."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        desc.setWordWrap(True)
        left_col.addWidget(desc)
        layout.addLayout(left_col, stretch=1)

        # Preset Loader Controls
        preset_box = QVBoxLayout()
        preset_box.setSpacing(6)
        preset_box.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        preset_row = QHBoxLayout()
        self.combo_presets = QComboBox()
        self.combo_presets.setMinimumWidth(220)
        for p in get_all_presets():
            self.combo_presets.addItem(p.name, p.preset_id)

        btn_load_preset = QPushButton("Load Preset")
        btn_load_preset.setProperty("class", "btn-secondary")
        btn_load_preset.clicked.connect(self._on_load_preset)
        preset_row.addWidget(self.combo_presets)
        preset_row.addWidget(btn_load_preset)

        preset_box.addLayout(preset_row)
        layout.addLayout(preset_box)

        return card

    def _create_process_input_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Process Workload Configuration")
        title.setProperty("class", "heading-2")
        header_row.addWidget(title)
        header_row.addStretch(1)

        btn_clear = QPushButton("Clear All")
        btn_clear.setProperty("class", "btn-secondary")
        btn_clear.clicked.connect(self._on_clear_processes)
        header_row.addWidget(btn_clear)

        layout.addLayout(header_row)

        # Process Table
        self.table_processes = QTableWidget(0, 5)
        self.table_processes.setHorizontalHeaderLabels(["Process ID", "Arrival Time", "Burst Time", "Priority", "Actions"])
        self.table_processes.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_processes.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_processes.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_processes.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_processes.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_processes.verticalHeader().setVisible(False)
        self.table_processes.setFixedHeight(160)
        self.table_processes.setStyleSheet("""
            QTableWidget {
                background-color: #161b24;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QHeaderView::section {
                background-color: #1c2330;
                color: #c9d1d9;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.table_processes)

        # Inline Add Process Controls
        add_bar = QHBoxLayout()
        add_bar.setSpacing(10)

        add_bar.addWidget(QLabel("PID:"))
        self.edit_pid = QLineEdit()
        self.edit_pid.setFixedWidth(70)
        self.edit_pid.setText("P1")
        add_bar.addWidget(self.edit_pid)

        add_bar.addWidget(QLabel("Arrival Time:"))
        self.spin_arrival = QDoubleSpinBox()
        self.spin_arrival.setRange(0.0, 999.0)
        self.spin_arrival.setValue(0.0)
        self.spin_arrival.setSingleStep(1.0)
        self.spin_arrival.setSuffix(" ms")
        self.spin_arrival.setFixedWidth(95)
        add_bar.addWidget(self.spin_arrival)

        add_bar.addWidget(QLabel("Burst Time:"))
        self.spin_burst = QDoubleSpinBox()
        self.spin_burst.setRange(0.1, 999.0)
        self.spin_burst.setValue(4.0)
        self.spin_burst.setSingleStep(1.0)
        self.spin_burst.setSuffix(" ms")
        self.spin_burst.setFixedWidth(95)
        add_bar.addWidget(self.spin_burst)

        add_bar.addWidget(QLabel("Priority:"))
        self.spin_priority = QSpinBox()
        self.spin_priority.setRange(0, 99)
        self.spin_priority.setValue(1)
        self.spin_priority.setFixedWidth(75)
        add_bar.addWidget(self.spin_priority)

        add_bar.addStretch(1)

        btn_add = QPushButton("+ Add Process")
        btn_add.setProperty("class", "btn-secondary")
        btn_add.clicked.connect(self._on_add_process)
        add_bar.addWidget(btn_add)

        layout.addLayout(add_bar)
        return card

    def _create_algorithm_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Algorithm Selection & Dispatch Parameters")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Algorithm Selection
        grid.addWidget(QLabel("Scheduling Algorithm:"), 0, 0)
        self.combo_algo = QComboBox()
        self.combo_algo.addItem("First Come First Serve (FCFS)", AlgorithmType.FCFS)
        self.combo_algo.addItem("Shortest Job First (SJF - Non-Preemptive)", AlgorithmType.SJF)
        self.combo_algo.addItem("Shortest Remaining Time First (SRTF - Preemptive)", AlgorithmType.SRTF)
        self.combo_algo.addItem("Priority Scheduling (Non-Preemptive)", AlgorithmType.PRIORITY_NON_PREEMPTIVE)
        self.combo_algo.addItem("Priority Scheduling (Preemptive)", AlgorithmType.PRIORITY_PREEMPTIVE)
        self.combo_algo.addItem("Round Robin (RR)", AlgorithmType.ROUND_ROBIN)
        self.combo_algo.currentIndexChanged.connect(self._on_algorithm_changed)
        grid.addWidget(self.combo_algo, 0, 1)

        # 2. Time Quantum (Round Robin)
        self.lbl_quantum = QLabel("Time Quantum (RR):")
        grid.addWidget(self.lbl_quantum, 0, 2)
        self.spin_quantum = QDoubleSpinBox()
        self.spin_quantum.setRange(0.1, 100.0)
        self.spin_quantum.setValue(2.0)
        self.spin_quantum.setSingleStep(0.5)
        self.spin_quantum.setSuffix(" ms")
        grid.addWidget(self.spin_quantum, 0, 3)

        # 3. Priority Direction
        self.lbl_direction = QLabel("Priority Direction:")
        grid.addWidget(self.lbl_direction, 1, 0)
        self.combo_direction = QComboBox()
        self.combo_direction.addItem("Lower Value = Higher Priority (Unix Nice)", PriorityDirection.LOWER_IS_HIGHER)
        self.combo_direction.addItem("Higher Value = Higher Priority (RTOS/Windows)", PriorityDirection.HIGHER_IS_HIGHER)
        grid.addWidget(self.combo_direction, 1, 1)

        # 4. Context Switch Overhead
        grid.addWidget(QLabel("Context Switch Overhead:"), 1, 2)
        self.spin_cs_overhead = QDoubleSpinBox()
        self.spin_cs_overhead.setRange(0.0, 10.0)
        self.spin_cs_overhead.setValue(0.0)
        self.spin_cs_overhead.setSingleStep(0.1)
        self.spin_cs_overhead.setSuffix(" ms")
        grid.addWidget(self.spin_cs_overhead, 1, 3)

        # 5. Priority Aging Row
        aging_box = QHBoxLayout()
        self.chk_aging = QCheckBox("Enable Priority Aging (mitigates starvation)")
        self.chk_aging.stateChanged.connect(self._on_aging_toggle)
        aging_box.addWidget(self.chk_aging)

        self.lbl_aging_interval = QLabel("Interval:")
        aging_box.addWidget(self.lbl_aging_interval)
        self.spin_aging_interval = QDoubleSpinBox()
        self.spin_aging_interval.setRange(0.5, 50.0)
        self.spin_aging_interval.setValue(5.0)
        self.spin_aging_interval.setSuffix(" ms")
        self.spin_aging_interval.setFixedWidth(90)
        self.spin_aging_interval.setEnabled(False)
        aging_box.addWidget(self.spin_aging_interval)
        aging_box.addStretch(1)

        grid.addLayout(aging_box, 2, 0, 1, 4)

        layout.addLayout(grid)

        # Action Buttons
        btn_bar = QHBoxLayout()
        btn_bar.addStretch(1)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setProperty("class", "btn-secondary")
        btn_reset.clicked.connect(self._on_reset_defaults)
        btn_bar.addWidget(btn_reset)

        self.btn_compare = QPushButton("📊 Compare All Algorithms")
        self.btn_compare.setProperty("class", "btn-secondary")
        self.btn_compare.clicked.connect(self._on_compare_all)
        btn_bar.addWidget(self.btn_compare)

        self.btn_run = QPushButton("▶ Run Simulation")
        self.btn_run.setProperty("class", "btn-primary")
        self.btn_run.clicked.connect(self.run_simulation)
        btn_bar.addWidget(self.btn_run)

        layout.addLayout(btn_bar)

        self._on_algorithm_changed()
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_tat = MetricCard(
            title="Avg Turnaround Time",
            value="-- ms",
            subtitle="Arrival to completion time",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_tat, 0, 0)

        self.card_wt = MetricCard(
            title="Avg Waiting Time",
            value="-- ms",
            subtitle="Total ready queue waiting time",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_wt, 0, 1)

        self.card_rt = MetricCard(
            title="Avg Response Time",
            value="-- ms",
            subtitle="Arrival to first CPU dispatch",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_rt, 0, 2)

        self.card_util = MetricCard(
            title="CPU Utilization",
            value="-- %",
            subtitle="Busy CPU ratio over total time",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_util, 1, 0)

        self.card_throughput = MetricCard(
            title="Throughput",
            value="-- p/ms",
            subtitle="Completed processes per time unit",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_throughput, 1, 1)

        self.card_cs = MetricCard(
            title="Context Switches",
            value="--",
            subtitle="Process state transition count",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_cs, 1, 2)

        return grid

    def _create_results_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        header = QLabel("Process Execution Results Table")
        header.setProperty("class", "heading-2")
        layout.addWidget(header)

        self.table_results = QTableWidget(0, 10)
        self.table_results.setHorizontalHeaderLabels([
            "PID",
            "Arrival",
            "Burst",
            "Priority",
            "Start Time",
            "Completion",
            "Turnaround",
            "Waiting",
            "Response",
            "Status",
        ])
        for c in range(10):
            self.table_results.horizontalHeader().setSectionResizeMode(c, QHeaderView.Stretch)
        self.table_results.verticalHeader().setVisible(False)
        self.table_results.setFixedHeight(180)
        self.table_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_results.setStyleSheet("""
            QTableWidget {
                background-color: #161b24;
                border: 1px solid #30363d;
                border-radius: 6px;
                gridline-color: #21262d;
            }
            QHeaderView::section {
                background-color: #1c2330;
                color: #c9d1d9;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #30363d;
            }
        """)
        layout.addWidget(self.table_results)

        return card

    # -------------------------------------------------------------------------
    # Process Management Slots
    # -------------------------------------------------------------------------
    def _refresh_process_table(self) -> None:
        """Render current process list in input table."""
        self.table_processes.setRowCount(len(self._processes))
        for row_idx, p in enumerate(self._processes):
            pid_item = QTableWidgetItem(p.process_id)
            pid_item.setTextAlignment(Qt.AlignCenter)
            self.table_processes.setItem(row_idx, 0, pid_item)

            arr_item = QTableWidgetItem(f"{p.arrival_time:g} ms")
            arr_item.setTextAlignment(Qt.AlignCenter)
            self.table_processes.setItem(row_idx, 1, arr_item)

            burst_item = QTableWidgetItem(f"{p.burst_time:g} ms")
            burst_item.setTextAlignment(Qt.AlignCenter)
            self.table_processes.setItem(row_idx, 2, burst_item)

            prio_item = QTableWidgetItem(str(p.priority))
            prio_item.setTextAlignment(Qt.AlignCenter)
            self.table_processes.setItem(row_idx, 3, prio_item)

            btn_del = QPushButton("Delete")
            btn_del.setProperty("class", "btn-secondary")
            btn_del.setFixedSize(65, 24)
            btn_del.clicked.connect(lambda _, idx=row_idx: self._on_delete_process(idx))
            self.table_processes.setCellWidget(row_idx, 4, btn_del)

    def _on_add_process(self) -> None:
        """Add new process from inline input bar."""
        pid = self.edit_pid.text().strip()
        if not pid:
            QMessageBox.warning(self, "Invalid PID", "Process ID cannot be empty.")
            return

        if any(p.process_id == pid for p in self._processes):
            QMessageBox.warning(self, "Duplicate PID", f"Process ID '{pid}' already exists.")
            return

        arr = self.spin_arrival.value()
        burst = self.spin_burst.value()
        prio = self.spin_priority.value()

        new_p = Process(process_id=pid, arrival_time=arr, burst_time=burst, priority=prio)
        self._processes.append(new_p)
        self._next_pid_counter += 1
        self.edit_pid.setText(f"P{self._next_pid_counter}")
        self._refresh_process_table()

    def _on_delete_process(self, idx: int) -> None:
        if 0 <= idx < len(self._processes):
            self._processes.pop(idx)
            self._refresh_process_table()

    def _on_clear_processes(self) -> None:
        self._processes.clear()
        self._refresh_process_table()

    def _load_default_preset(self) -> None:
        """Load initial textbook preset."""
        preset = get_preset_by_id("staggered_arrivals")
        self._processes = preset.get_cloned_processes()
        self._next_pid_counter = len(self._processes) + 1
        self.edit_pid.setText(f"P{self._next_pid_counter}")
        self._refresh_process_table()

    def _on_load_preset(self) -> None:
        """Load selected educational preset."""
        preset_id = self.combo_presets.currentData()
        preset = get_preset_by_id(preset_id)
        self._processes = preset.get_cloned_processes()
        self._next_pid_counter = len(self._processes) + 1
        self.edit_pid.setText(f"P{self._next_pid_counter}")
        self._refresh_process_table()
        # Automatically run simulation for convenience
        self.run_simulation()

    # -------------------------------------------------------------------------
    # Algorithm Config Slots
    # -------------------------------------------------------------------------
    def _on_algorithm_changed(self) -> None:
        """Toggle parameter fields based on selected algorithm."""
        algo = self.combo_algo.currentData()
        is_rr = (algo == AlgorithmType.ROUND_ROBIN)
        is_prio = (algo in (AlgorithmType.PRIORITY_NON_PREEMPTIVE, AlgorithmType.PRIORITY_PREEMPTIVE))

        self.lbl_quantum.setEnabled(is_rr)
        self.spin_quantum.setEnabled(is_rr)

        self.lbl_direction.setEnabled(is_prio)
        self.combo_direction.setEnabled(is_prio)
        self.chk_aging.setEnabled(is_prio)
        self.lbl_aging_interval.setEnabled(is_prio and self.chk_aging.isChecked())
        self.spin_aging_interval.setEnabled(is_prio and self.chk_aging.isChecked())

    def _on_aging_toggle(self, state: int) -> None:
        is_prio = self.combo_algo.currentData() in (AlgorithmType.PRIORITY_NON_PREEMPTIVE, AlgorithmType.PRIORITY_PREEMPTIVE)
        enabled = (state == Qt.Checked) and is_prio
        self.lbl_aging_interval.setEnabled(enabled)
        self.spin_aging_interval.setEnabled(enabled)

    def _on_reset_defaults(self) -> None:
        self.combo_algo.setCurrentIndex(0)
        self.spin_quantum.setValue(2.0)
        self.combo_direction.setCurrentIndex(0)
        self.spin_cs_overhead.setValue(0.0)
        self.chk_aging.setChecked(False)
        self.spin_aging_interval.setValue(5.0)

    # -------------------------------------------------------------------------
    # Simulation Execution
    # -------------------------------------------------------------------------
    def run_simulation(self) -> None:
        """Execute selected scheduling algorithm on current process batch."""
        if not self._processes:
            QMessageBox.information(self, "No Processes", "Please add at least one process or load a preset.")
            return

        algo = self.combo_algo.currentData()
        quantum = self.spin_quantum.value()
        direction = self.combo_direction.currentData()
        enable_aging = self.chk_aging.isChecked()
        aging_interval = self.spin_aging_interval.value()
        cs_overhead = self.spin_cs_overhead.value()

        try:
            result = ProcessSchedulerSimulator.simulate(
                processes=self._processes,
                algorithm_type=algo,
                time_quantum=quantum,
                direction=direction,
                enable_aging=enable_aging,
                aging_interval=aging_interval,
                context_switch_overhead=cs_overhead,
            )
            self._last_simulation_result = result
            self._display_simulation_results(result)
        except Exception as e:
            QMessageBox.critical(self, "Simulation Error", f"Simulation failed: {e}")

    def _display_simulation_results(self, result: SimulationResult) -> None:
        """Update Gantt timeline, metrics cards, and results table."""
        # 1. Update Gantt Chart
        self.gantt_widget.set_timeline(result.timeline)

        # 2. Update Metric Cards
        m = result.metrics
        self.card_tat.set_value(f"{m.average_turnaround_time:.2f} ms")
        self.card_tat.set_status(f"{m.total_simulation_time:.1f}ms total", "info")

        self.card_wt.set_value(f"{m.average_waiting_time:.2f} ms")
        self.card_wt.set_status("Calculated", "success")

        self.card_rt.set_value(f"{m.average_response_time:.2f} ms")
        self.card_rt.set_status("Calculated", "success")

        self.card_util.set_value(f"{m.cpu_utilization_pct:.1f} %")
        self.card_util.set_status(f"{m.busy_cpu_time:.1f}ms busy", "info")

        self.card_throughput.set_value(f"{m.throughput:.3f} p/ms")
        self.card_throughput.set_status(f"{m.completed_processes} jobs", "success")

        self.card_cs.set_value(str(m.context_switches))
        self.card_cs.set_status(
            f"{m.context_switch_time:.1f}ms overhead",
            "warning" if m.context_switches > 0 else "neutral",
        )

        # 3. Update Results Table
        self.table_results.setRowCount(len(result.processes))
        for row_idx, p in enumerate(result.processes):
            pid_item = QTableWidgetItem(p.process_id)
            pid_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 0, pid_item)

            arr_item = QTableWidgetItem(f"{p.arrival_time:g}")
            arr_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 1, arr_item)

            burst_item = QTableWidgetItem(f"{p.burst_time:g}")
            burst_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 2, burst_item)

            prio_item = QTableWidgetItem(str(p.priority))
            prio_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 3, prio_item)

            start_str = f"{p.start_time:g}" if p.start_time is not None else "—"
            start_item = QTableWidgetItem(start_str)
            start_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 4, start_item)

            comp_str = f"{p.completion_time:g}" if p.completion_time is not None else "—"
            comp_item = QTableWidgetItem(comp_str)
            comp_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 5, comp_item)

            tat_item = QTableWidgetItem(f"{p.turnaround_time:.2f}")
            tat_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 6, tat_item)

            wt_item = QTableWidgetItem(f"{p.waiting_time:.2f}")
            wt_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 7, wt_item)

            rt_item = QTableWidgetItem(f"{p.response_time:.2f}")
            rt_item.setTextAlignment(Qt.AlignCenter)
            self.table_results.setItem(row_idx, 8, rt_item)

            status_item = QTableWidgetItem("Completed" if p.is_completed else "Ready")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(Qt.green if p.is_completed else Qt.yellow)
            self.table_results.setItem(row_idx, 9, status_item)

    # -------------------------------------------------------------------------
    # Comparison Mode
    # -------------------------------------------------------------------------
    def _on_compare_all(self) -> None:
        """Run all algorithms on current workload and open ComparisonDialog."""
        if not self._processes:
            QMessageBox.information(self, "No Processes", "Please add processes or load a preset before comparing.")
            return

        quantum = self.spin_quantum.value()
        direction = self.combo_direction.currentData()
        enable_aging = self.chk_aging.isChecked()
        aging_interval = self.spin_aging_interval.value()
        cs_overhead = self.spin_cs_overhead.value()

        try:
            _, rows = compare_all_algorithms(
                processes=self._processes,
                time_quantum=quantum,
                direction=direction,
                enable_aging=enable_aging,
                aging_interval=aging_interval,
                context_switch_overhead=cs_overhead,
            )
            dlg = ComparisonDialog(rows, self)
            dlg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", f"Comparison failed: {e}")
