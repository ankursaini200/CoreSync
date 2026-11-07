"""Real System vs Virtual Lab Comparison Workstation GUI Page for CoreSync."""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from engine.analytics.benchmarking import get_sanitized_hardware_metadata
from engine.comparison.models import (
    ComparisonAnalysis,
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonSessionResult,
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealExecutionResult,
    RealSystemConfig,
    VirtualExecutionResult,
    VirtualLabConfig,
)
from engine.comparison.workload_mapper import (
    SUPPORTED_DATA_PARALLEL_OPS,
    SUPPORTED_TASK_PARALLEL_PRESETS,
)
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm
from gui.comparison_runner_thread import ComparisonRunnerThread
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard
from utils.system_info import get_system_summary

logger = logging.getLogger("CoreSync.GUI.Comparison")


class ExecutionTimelineWidget(QFrame):
    """Custom canvas rendering worker/core execution intervals on a dedicated domain axis."""

    def __init__(self, domain_label: str = "seconds", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.domain_label = domain_label
        self._tracks: List[Dict[str, Any]] = []  # list of {"track_id": int/str, "intervals": [(s, e, label, color)]}
        self._max_val = 1.0
        self.setMinimumHeight(140)
        self.setProperty("class", "card")

    def set_timeline_data(self, tracks: List[Dict[str, Any]], max_val: float) -> None:
        self._tracks = tracks
        self._max_val = max(0.001, max_val)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#161b22"))

        if not self._tracks:
            painter.setPen(QColor("#8b949e"))
            painter.setFont(QFont("Inter", 10))
            painter.drawText(0, 0, w, h, Qt.AlignCenter, f"No execution timeline available ({self.domain_label}).")
            return

        margin_left = 70
        margin_right = 20
        margin_top = 25
        margin_bottom = 30
        plot_w = w - margin_left - margin_right
        plot_h = h - margin_top - margin_bottom

        num_tracks = len(self._tracks)
        row_h = max(14, min(30, int(plot_h / max(1, num_tracks))))

        # Draw axis line
        painter.setPen(QPen(QColor("#30363d"), 1))
        painter.drawLine(margin_left, margin_top + plot_h, margin_left + plot_w, margin_top + plot_h)

        # Draw axis ticks
        painter.setFont(QFont("Inter", 8))
        painter.setPen(QColor("#8b949e"))
        for i in range(5):
            frac = i / 4.0
            x = margin_left + int(frac * plot_w)
            val = frac * self._max_val
            label = f"{val:.3f} s" if self.domain_label == "seconds" else f"{int(val)} ticks"
            painter.drawLine(x, margin_top + plot_h, x, margin_top + plot_h + 4)
            painter.drawText(x - 30, margin_top + plot_h + 16, 60, 14, Qt.AlignCenter, label)

        # Draw tracks
        for idx, track in enumerate(self._tracks):
            y = margin_top + idx * row_h
            t_label = str(track.get("track_id", f"T-{idx}"))
            painter.setPen(QColor("#c9d1d9"))
            painter.drawText(8, y + 2, margin_left - 14, row_h, Qt.AlignRight | Qt.AlignVCenter, t_label)

            # Draw intervals
            for item in track.get("intervals", []):
                s, e = item[0], item[1]
                color = item[2] if len(item) > 2 else QColor("#58a6ff")
                x_s = margin_left + int((max(0.0, s) / self._max_val) * plot_w)
                x_e = margin_left + int((min(self._max_val, e) / self._max_val) * plot_w)
                box_w = max(2, x_e - x_s)

                painter.fillRect(x_s, y + 2, box_w, row_h - 4, color)
                painter.setPen(QPen(QColor("#ffffff"), 1))
                painter.drawRect(x_s, y + 2, box_w, row_h - 4)


class ComparisonPage(QWidget):
    """Workstation page comparing Real System execution with Virtual Lab simulation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary = get_system_summary()
        self.hw_metadata = get_sanitized_hardware_metadata()

        # Background runner thread
        self.runner_thread = ComparisonRunnerThread(self)
        self.runner_thread.progress_updated.connect(self._on_progress_updated)
        self.runner_thread.comparison_finished.connect(self._on_comparison_finished)
        self.runner_thread.comparison_failed.connect(self._on_comparison_failed)

        self._active_session: Optional[ComparisonSessionResult] = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(14)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # -------------------------------------------------------------
        # Section A: Configuration Panel
        # -------------------------------------------------------------
        cfg_card = QFrame()
        cfg_card.setProperty("class", "card")
        cfg_layout = QVBoxLayout(cfg_card)
        cfg_layout.setSpacing(12)

        cfg_title = QLabel("Comparison Workload & Architecture Configuration")
        cfg_title.setProperty("class", "heading-2")
        cfg_layout.addWidget(cfg_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(10)

        # Row 0: Execution Mode
        grid.addWidget(QLabel("Execution Mode:"), 0, 0)
        mode_box = QHBoxLayout()
        self.rb_compare_both = QRadioButton("Compare Both Environments")
        self.rb_compare_both.setChecked(True)
        self.rb_real_only = QRadioButton("Real System Only")
        self.rb_virtual_only = QRadioButton("Virtual Lab Only")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_compare_both, 1)
        self.mode_group.addButton(self.rb_real_only, 2)
        self.mode_group.addButton(self.rb_virtual_only, 3)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        mode_box.addWidget(self.rb_compare_both)
        mode_box.addWidget(self.rb_real_only)
        mode_box.addWidget(self.rb_virtual_only)
        mode_box.addStretch(1)
        grid.addLayout(mode_box, 0, 1, 1, 3)

        # Row 1: Workload Type & Specific Workload Selector
        grid.addWidget(QLabel("Workload Paradigm:"), 1, 0)
        self.combo_paradigm = QComboBox()
        self.combo_paradigm.addItem("Data Parallelism (SIMD / Chunks)", "data_parallel")
        self.combo_paradigm.addItem("Task Parallelism (DAG Dependencies)", "task_parallel")
        self.combo_paradigm.currentIndexChanged.connect(self._on_paradigm_changed)
        grid.addWidget(self.combo_paradigm, 1, 1)

        self.lbl_workload_item = QLabel("Computational Kernel:")
        grid.addWidget(self.lbl_workload_item, 1, 2)
        self.combo_workload = QComboBox()
        grid.addWidget(self.combo_workload, 1, 3)

        # Row 2: Parameters (Dataset Size / DAG options)
        self.lbl_param = QLabel("Dataset Elements:")
        grid.addWidget(self.lbl_param, 2, 0)
        param_layout = QHBoxLayout()
        self.slider_dataset = QSlider(Qt.Horizontal)
        self.slider_dataset.setRange(1_000, 200_000)
        self.slider_dataset.setValue(20_000)
        self.slider_dataset.setSingleStep(5_000)
        self.spin_dataset = QSpinBox()
        self.spin_dataset.setRange(1_000, 500_000)
        self.spin_dataset.setValue(20_000)
        self.spin_dataset.setSingleStep(5_000)
        self.slider_dataset.valueChanged.connect(self.spin_dataset.setValue)
        self.spin_dataset.valueChanged.connect(self.slider_dataset.setValue)

        param_layout.addWidget(self.slider_dataset, 1)
        param_layout.addWidget(self.spin_dataset)
        grid.addLayout(param_layout, 2, 1)

        # Row 2 (Right): Real Workers
        grid.addWidget(QLabel("Real System Workers:"), 2, 2)
        self.spin_real_workers = QSpinBox()
        max_logical = max(4, self.summary.logical_cores or 8)
        self.spin_real_workers.setRange(1, max_logical)
        self.spin_real_workers.setValue(min(4, self.summary.physical_cores or 4))
        self.spin_real_workers.valueChanged.connect(self._update_overview_cards)
        grid.addWidget(self.spin_real_workers, 2, 3)

        # Row 3: Virtual Cores & Scheduler
        grid.addWidget(QLabel("Virtual Lab Cores:"), 3, 0)
        self.spin_virtual_cores = QSpinBox()
        self.spin_virtual_cores.setRange(1, 64)
        self.spin_virtual_cores.setValue(8)
        self.spin_virtual_cores.valueChanged.connect(self._update_overview_cards)
        grid.addWidget(self.spin_virtual_cores, 3, 1)

        grid.addWidget(QLabel("Virtual Scheduling:"), 3, 2)
        sched_layout = QHBoxLayout()
        self.combo_virtual_sched = QComboBox()
        self.combo_virtual_sched.addItem("First Come First Served (FCFS)", "FCFS")
        self.combo_virtual_sched.addItem("Priority Scheduling", "PRIORITY")
        self.combo_virtual_sched.addItem("Round Robin (Preemptive)", "ROUND_ROBIN")
        self.combo_virtual_sched.currentIndexChanged.connect(self._update_overview_cards)

        self.spin_quantum = QSpinBox()
        self.spin_quantum.setRange(5, 200)
        self.spin_quantum.setValue(20)
        self.spin_quantum.setSuffix(" ticks")
        self.spin_quantum.setToolTip("Round Robin Time Quantum")

        sched_layout.addWidget(self.combo_virtual_sched, 1)
        sched_layout.addWidget(self.spin_quantum)
        grid.addLayout(sched_layout, 3, 3)

        # Row 4: Virtual Hybrid P/E Core Architecture Toggle
        self.chk_hybrid = QCheckBox("Simulate Heterogeneous P/E Core Architecture (Virtual Hybrid CPU)")
        self.chk_hybrid.stateChanged.connect(self._update_overview_cards)
        grid.addWidget(self.chk_hybrid, 4, 0, 1, 4)

        cfg_layout.addLayout(grid)
        layout.addWidget(cfg_card)

        # -------------------------------------------------------------
        # Section B: Environment Overview Cards
        # -------------------------------------------------------------
        over_row = QHBoxLayout()

        # Real System Card
        self.card_real_env = QFrame()
        self.card_real_env.setProperty("class", "card")
        r_layout = QVBoxLayout(self.card_real_env)
        r_layout.setSpacing(6)
        r_hdr = QHBoxLayout()
        r_title = QLabel("ENVIRONMENT A: REAL SYSTEM")
        r_title.setProperty("class", "heading-3")
        self.badge_real_status = StatusBadge("Ready", "success")
        r_hdr.addWidget(r_title)
        r_hdr.addStretch(1)
        r_hdr.addWidget(self.badge_real_status)
        r_layout.addLayout(r_hdr)

        self.lbl_real_cpu = QLabel(f"• CPU Model: {self.hw_metadata.get('cpu_model', 'Host CPU')}")
        self.lbl_real_topology = QLabel(
            f"• Verified Topology: {self.hw_metadata.get('physical_cores', '?')} Physical / {self.hw_metadata.get('total_logical_cores', '?')} Logical Cores"
        )
        self.lbl_real_os = QLabel(f"• OS Platform: {self.hw_metadata.get('operating_system', 'Linux')} (spawn-context)")
        self.lbl_real_workers = QLabel("• Active Workers: 4 Spawned Processes")
        for lbl in (self.lbl_real_cpu, self.lbl_real_topology, self.lbl_real_os, self.lbl_real_workers):
            lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
            r_layout.addWidget(lbl)
        over_row.addWidget(self.card_real_env, 1)

        # Virtual Lab Card
        self.card_virt_env = QFrame()
        self.card_virt_env.setProperty("class", "card")
        v_layout = QVBoxLayout(self.card_virt_env)
        v_layout.setSpacing(6)
        v_hdr = QHBoxLayout()
        v_title = QLabel("ENVIRONMENT B: VIRTUAL LAB")
        v_title.setProperty("class", "heading-3")
        self.badge_virt_status = StatusBadge("Idle", "neutral")
        v_hdr.addWidget(v_title)
        v_hdr.addStretch(1)
        v_hdr.addWidget(self.badge_virt_status)
        v_layout.addLayout(v_hdr)

        self.lbl_virt_cpu = QLabel("• Virtual CPU: Software-Emulated CoreSync-X8")
        self.lbl_virt_topology = QLabel("• Virtual Cores: 8 Symmetric Standard Cores (1.0x)")
        self.lbl_virt_scheduler = QLabel("• Virtual Scheduler: First Come First Served (FCFS)")
        self.lbl_virt_clock = QLabel("• Clock Domain: Discrete Logical Clock Ticks (integer steps)")
        for lbl in (self.lbl_virt_cpu, self.lbl_virt_topology, self.lbl_virt_scheduler, self.lbl_virt_clock):
            lbl.setStyleSheet("color: #8b949e; font-size: 11px;")
            v_layout.addWidget(lbl)
        over_row.addWidget(self.card_virt_env, 1)

        layout.addLayout(over_row)

        # -------------------------------------------------------------
        # Section C: Execution Controls
        # -------------------------------------------------------------
        ctl_card = QFrame()
        ctl_card.setProperty("class", "card")
        ctl_layout = QHBoxLayout(ctl_card)
        ctl_layout.setSpacing(12)

        self.btn_run = QPushButton("Compare Both Environments")
        self.btn_run.setProperty("class", "action-btn")
        self.btn_run.clicked.connect(self._on_run_clicked)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)

        self.btn_reset = QPushButton("Reset Results")
        self.btn_reset.clicked.connect(self._reset_results)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)

        self.status_label = QLabel("Ready to configure and execute comparison.")
        self.status_label.setStyleSheet("color: #8b949e; font-size: 11px;")

        ctl_layout.addWidget(self.btn_run)
        ctl_layout.addWidget(self.btn_cancel)
        ctl_layout.addWidget(self.btn_reset)
        ctl_layout.addWidget(self.progress_bar, 1)
        ctl_layout.addWidget(self.status_label)
        layout.addWidget(ctl_card)

        # -------------------------------------------------------------
        # Section D: Comparative Results Dashboard
        # -------------------------------------------------------------
        self.tabs_results = QTabWidget()

        # Tab 1: Real System Measured Results
        tab_real = QWidget()
        t_real_layout = QVBoxLayout(tab_real)
        t_real_layout.setSpacing(10)
        grid_r = QGridLayout()
        grid_r.setHorizontalSpacing(14)
        grid_r.setVerticalSpacing(10)

        self.card_r_makespan = MetricCard("Wall-Clock Makespan", "-- ms", "Elapsed monotonic time", "Directly Measured", "success")
        self.card_r_speedup = MetricCard("Actual Speedup", "-- x", "T_seq / T_par", "Mathematically Derived", "info")
        self.card_r_compute = MetricCard("Aggregate Compute", "-- ms", "Sum of worker durations (W*s)", "Mathematically Derived", "info")
        self.card_r_no_compute = MetricCard("No-Worker-Compute Time", "-- ms", "T_makespan - T_union", "Mathematically Derived", "info")
        self.card_r_util = MetricCard("Worker Utilization", "-- %", "Cumulative compute / capacity", "Mathematically Derived", "info")
        self.card_r_mem = MetricCard("Process Memory (RSS)", "-- MB", "RAM footprint", "Directly Measured", "neutral")

        grid_r.addWidget(self.card_r_makespan, 0, 0)
        grid_r.addWidget(self.card_r_speedup, 0, 1)
        grid_r.addWidget(self.card_r_compute, 0, 2)
        grid_r.addWidget(self.card_r_no_compute, 1, 0)
        grid_r.addWidget(self.card_r_util, 1, 1)
        grid_r.addWidget(self.card_r_mem, 1, 2)
        t_real_layout.addLayout(grid_r)
        self.timeline_real = ExecutionTimelineWidget(domain_label="seconds", parent=self)
        t_real_layout.addWidget(self.timeline_real)

        self.tabs_results.addTab(tab_real, "REAL SYSTEM: MEASURED RESULTS")

        # Tab 2: Virtual Lab Simulated Results
        tab_virt = QWidget()
        t_virt_layout = QVBoxLayout(tab_virt)
        t_virt_layout.setSpacing(10)
        grid_v = QGridLayout()
        grid_v.setHorizontalSpacing(14)
        grid_v.setVerticalSpacing(10)

        self.card_v_makespan = MetricCard("Virtual Makespan", "-- ticks", "Discrete simulation ticks", "Simulated Virtual", "neutral")
        self.card_v_util = MetricCard("Virtual Core Utilization", "-- %", "Busy ticks / capacity ticks", "Simulated Virtual", "neutral")
        self.card_v_wait = MetricCard("Avg Waiting Time", "-- ticks", "Ready queue latency", "Simulated Virtual", "neutral")
        self.card_v_turn = MetricCard("Avg Turnaround Time", "-- ticks", "Arrival to completion", "Simulated Virtual", "neutral")
        self.card_v_thru = MetricCard("Simulated Throughput", "-- tasks/tick", "Task completion rate", "Simulated Virtual", "neutral")
        self.card_v_preempt = MetricCard("Preemption Events", "0", "Quantum expirations", "Simulated Virtual", "neutral")

        grid_v.addWidget(self.card_v_makespan, 0, 0)
        grid_v.addWidget(self.card_v_util, 0, 1)
        grid_v.addWidget(self.card_v_wait, 0, 2)
        grid_v.addWidget(self.card_v_turn, 1, 0)
        grid_v.addWidget(self.card_v_thru, 1, 1)
        grid_v.addWidget(self.card_v_preempt, 1, 2)
        t_virt_layout.addLayout(grid_v)
        self.timeline_virt = ExecutionTimelineWidget(domain_label="ticks", parent=self)
        t_virt_layout.addWidget(self.timeline_virt)

        self.tabs_results.addTab(tab_virt, "VIRTUAL LAB: SIMULATED RESULTS")

        # Tab 3: Comparative Analysis & Task Table
        tab_comp = QWidget()
        t_comp_layout = QVBoxLayout(tab_comp)
        t_comp_layout.setSpacing(10)

        comp_grid = QGridLayout()
        comp_grid.setHorizontalSpacing(14)
        comp_grid.setVerticalSpacing(10)

        self.card_c_equiv = MetricCard("Workload Equivalence", "Pending", "Input & task verification", "Pending", "neutral")
        self.card_c_ratio = MetricCard("Resource Ratio", "--", "W_real / C_virtual", "Mathematically Derived", "info")
        self.card_c_concord = MetricCard("Order Concordance", "-- %", "Sequence rank agreement", "Mathematically Derived", "info")
        self.card_c_udiff = MetricCard("Utilization Delta", "-- %", "U_real - U_virtual", "Mathematically Derived", "info")

        comp_grid.addWidget(self.card_c_equiv, 0, 0)
        comp_grid.addWidget(self.card_c_ratio, 0, 1)
        comp_grid.addWidget(self.card_c_concord, 0, 2)
        comp_grid.addWidget(self.card_c_udiff, 0, 3)
        t_comp_layout.addLayout(comp_grid)

        self.equiv_detail_label = QLabel("Configure a workload and execute comparison to view analysis.")
        self.equiv_detail_label.setStyleSheet("color: #58a6ff; font-weight: 500; font-size: 11px;")
        t_comp_layout.addWidget(self.equiv_detail_label)

        # Task Comparison Table
        self.comp_table = QTableWidget(0, 7)
        self.comp_table.setHorizontalHeaderLabels([
            "Task / Chunk ID",
            "Real Duration (s)",
            "Real Worker PID",
            "Virtual Core",
            "Virtual Finish (Ticks)",
            "Virtual Wait (Ticks)",
            "Equivalence Status",
        ])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.comp_table.setAlternatingRowColors(True)
        t_comp_layout.addWidget(self.comp_table)

        self.tabs_results.addTab(tab_comp, "WORKLOAD EQUIVALENCE & COMPARATIVE ANALYSIS")
        layout.addWidget(self.tabs_results)

        # -------------------------------------------------------------
        # Section E: Educational Context / Clock Domain Separation Note
        # -------------------------------------------------------------
        edu_card = QFrame()
        edu_card.setProperty("class", "card")
        e_layout = QVBoxLayout(edu_card)
        e_layout.setSpacing(6)
        e_title = QLabel("Educational Measurement Principles & Clock Domain Distinction")
        e_title.setProperty("class", "heading-3")
        e_layout.addWidget(e_title)

        e_text = QLabel(
            "• CLOCK DOMAIN INDEPENDENCE: The Real System operates in continuous physical wall-clock seconds (measured via POSIX clock_gettime/perf_counter), "
            "while the Virtual Lab operates in discrete simulated logical ticks. Real seconds and virtual ticks belong to independent domains and MUST NEVER be divided.\n"
            "• PHYSICAL EXECUTION: Real System performance reflects OS process initialization, CPU cache hierarchies, memory paging, inter-process communication serialization, "
            "and kernel CFS/EEVDF scheduling decisions.\n"
            "• EDUCATIONAL SIMULATION: Virtual Lab models algorithmic task scheduling and virtual core allocations assuming idealized computational bursts without OS jitter.\n"
            "• EQUIVALENCE: Workload equivalence certifies identical logical task DAG topologies or array partitioning rather than identical elapsed execution time."
        )
        e_text.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 11px;")
        e_layout.addWidget(e_text)
        layout.addWidget(edu_card)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Populate initial dropdown items
        self._on_paradigm_changed(0)
        self._update_overview_cards()

    # -----------------------------------------------------------------
    # Dynamic Controls and Event Handlers
    # -----------------------------------------------------------------
    @Slot(int)
    def _on_paradigm_changed(self, idx: int) -> None:
        """Update workload selector based on selected paradigm."""
        self.combo_workload.clear()
        paradigm = self.combo_paradigm.currentData()

        if paradigm == "data_parallel":
            self.lbl_workload_item.setText("Computational Kernel:")
            for op_id, op_name in SUPPORTED_DATA_PARALLEL_OPS.items():
                self.combo_workload.addItem(op_name, op_id)
            self.lbl_param.setVisible(True)
            self.slider_dataset.setVisible(True)
            self.spin_dataset.setVisible(True)
        else:
            self.lbl_workload_item.setText("Task DAG Preset:")
            for p_id, p_name in SUPPORTED_TASK_PARALLEL_PRESETS.items():
                self.combo_workload.addItem(p_name, p_id)
            self.lbl_param.setVisible(False)
            self.slider_dataset.setVisible(False)
            self.spin_dataset.setVisible(False)

        self._update_overview_cards()

    @Slot(int)
    def _on_mode_changed(self, btn_id: int) -> None:
        """Update button label and card states based on execution mode."""
        if self.rb_compare_both.isChecked():
            self.btn_run.setText("Compare Both Environments")
            self.card_real_env.setEnabled(True)
            self.card_virt_env.setEnabled(True)
        elif self.rb_real_only.isChecked():
            self.btn_run.setText("Run Real System Only")
            self.card_real_env.setEnabled(True)
            self.card_virt_env.setEnabled(False)
        else:
            self.btn_run.setText("Run Virtual Lab Only")
            self.card_real_env.setEnabled(False)
            self.card_virt_env.setEnabled(True)

    def _update_overview_cards(self) -> None:
        """Synchronize overview card summary labels with current spinboxes."""
        r_workers = self.spin_real_workers.value()
        v_cores = self.spin_virtual_cores.value()
        self.lbl_real_workers.setText(f"• Active Workers: {r_workers} Spawned Process(es)")

        is_hybrid = self.chk_hybrid.isChecked()
        sched_name = self.combo_virtual_sched.currentText()

        self.lbl_virt_cpu.setText(f"• Virtual CPU: Software-Emulated CoreSync-X{v_cores}")
        if is_hybrid:
            p_cnt = max(1, v_cores // 2)
            e_cnt = max(1, v_cores - p_cnt)
            self.lbl_virt_topology.setText(f"• Virtual Cores: {p_cnt} P-Cores (1.5x) + {e_cnt} E-Cores (0.8x)")
        else:
            self.lbl_virt_topology.setText(f"• Virtual Cores: {v_cores} Symmetric Standard Cores (1.0x)")

        self.lbl_virt_scheduler.setText(f"• Virtual Scheduler: {sched_name}")

    def _build_configuration(self) -> ComparisonConfiguration:
        """Assemble current UI selections into a validated ComparisonConfiguration."""
        if self.rb_compare_both.isChecked():
            mode = ComparisonExecutionMode.COMPARE_BOTH
        elif self.rb_real_only.isChecked():
            mode = ComparisonExecutionMode.REAL_ONLY
        else:
            mode = ComparisonExecutionMode.VIRTUAL_ONLY

        p_data = self.combo_paradigm.currentData()
        w_type = ComparisonWorkloadType.DATA_PARALLEL if p_data == "data_parallel" else ComparisonWorkloadType.TASK_PARALLEL
        w_id = self.combo_workload.currentData()
        w_name = self.combo_workload.currentText()
        ds_size = self.spin_dataset.value()

        workload = ComparisonWorkloadConfig(
            workload_type=w_type,
            workload_id=w_id,
            workload_name=w_name,
            dataset_size=ds_size,
            task_count=self.spin_real_workers.value(),
        )

        real_cfg = RealSystemConfig(
            worker_count=self.spin_real_workers.value(),
        )

        v_cores = self.spin_virtual_cores.value()
        is_hybrid = self.chk_hybrid.isChecked()
        p_cnt = max(1, v_cores // 2) if is_hybrid else 0
        e_cnt = max(1, v_cores - p_cnt) if is_hybrid else 0

        virt_cfg = VirtualLabConfig(
            virtual_core_count=v_cores,
            enable_hybrid=is_hybrid,
            p_core_count=p_cnt,
            e_core_count=e_cnt,
            scheduling_algorithm=SchedulingAlgorithm[self.combo_virtual_sched.currentData()],
            time_quantum=self.spin_quantum.value(),
        )

        cid = f"comp_{w_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        return ComparisonConfiguration(
            comparison_id=cid,
            execution_mode=mode,
            workload=workload,
            real_config=real_cfg,
            virtual_config=virt_cfg,
        )

    # -----------------------------------------------------------------
    # Execution Lifecycle
    # -----------------------------------------------------------------
    @Slot()
    def _on_run_clicked(self) -> None:
        """Initiate comparative execution off the UI thread."""
        config = self._build_configuration()

        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing comparison environments...")

        if config.execution_mode in (ComparisonExecutionMode.REAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
            self.badge_real_status.set_status("Executing", "warning")
        if config.execution_mode in (ComparisonExecutionMode.VIRTUAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
            self.badge_virt_status.set_status("Simulating", "info")

        self.runner_thread.configure(config)
        self.runner_thread.start()

    @Slot()
    def _on_cancel_clicked(self) -> None:
        """Cancel running execution."""
        self.status_label.setText("Cancelling active comparison...")
        self.runner_thread.cancel_execution()
        self.btn_cancel.setEnabled(False)

    @Slot(int, int, str)
    def _on_progress_updated(self, completed: int, total: int, msg: str) -> None:
        self.progress_bar.setValue(completed)
        self.status_label.setText(msg)

    @Slot(object)
    def _on_comparison_finished(self, session: ComparisonSessionResult) -> None:
        """Handle completion of the comparison session."""
        self._active_session = session
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)

        if session.cancelled:
            self.status_label.setText("Comparison session was cancelled.")
            self.badge_real_status.set_status("Cancelled", "danger")
            self.badge_virt_status.set_status("Cancelled", "danger")
        elif not session.success:
            self.status_label.setText(f"Comparison finished with errors: {session.error_message}")
            self.badge_real_status.set_status("Error", "danger")
            self.badge_virt_status.set_status("Error", "danger")
        else:
            self.status_label.setText(f"Comparison completed successfully ({session.comparison_id}).")
            if session.real_result:
                self.badge_real_status.set_status("Completed", "success")
            if session.virtual_result:
                self.badge_virt_status.set_status("Completed", "success")

        self._render_results(session)

    @Slot(str)
    def _on_comparison_failed(self, error_msg: str) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Execution failed: {error_msg}")
        self.badge_real_status.set_status("Failed", "danger")
        self.badge_virt_status.set_status("Failed", "danger")

    @Slot()
    def _reset_results(self) -> None:
        """Clear all metric cards and tables."""
        for card in (
            self.card_r_makespan, self.card_r_speedup, self.card_r_compute,
            self.card_r_no_compute, self.card_r_util, self.card_r_mem,
            self.card_v_makespan, self.card_v_util, self.card_v_wait,
            self.card_v_turn, self.card_v_thru, self.card_v_preempt,
            self.card_c_equiv, self.card_c_ratio, self.card_c_concord, self.card_c_udiff,
        ):
            card.set_value("--", "", "neutral", "Pending")

        self.timeline_real.set_timeline_data([], 1.0)
        self.timeline_virt.set_timeline_data([], 1.0)
        self.comp_table.setRowCount(0)
        self.equiv_detail_label.setText("Results reset. Ready to configure a new comparison.")
        self.badge_real_status.set_status("Ready", "success")
        self.badge_virt_status.set_status("Idle", "neutral")

    # -----------------------------------------------------------------
    # Results Rendering
    # -----------------------------------------------------------------
    def _render_results(self, session: ComparisonSessionResult) -> None:
        """Render all telemetry and analytical cards from a completed session."""
        real_res = session.real_result
        virt_res = session.virtual_result
        analysis = session.analysis

        # 1. Render Real System Results
        if real_res:
            m_ms = real_res.wall_clock_time_s * 1000.0
            s_text = f"{real_res.actual_speedup:.2f} x" if real_res.actual_speedup is not None else "1.00 x"
            agg_ms = real_res.aggregate_worker_compute_time_s * 1000.0
            no_comp_ms = real_res.no_worker_compute_time_s * 1000.0

            self.card_r_makespan.set_value(f"{m_ms:.2f} ms", f"{real_res.worker_count} workers", "success", "Directly Measured")
            self.card_r_speedup.set_value(s_text, "Amdahl ratio", "info", "Mathematically Derived")
            self.card_r_compute.set_value(f"{agg_ms:.2f} ms", "Worker-seconds (W*s)", "info", "Mathematically Derived")
            self.card_r_no_compute.set_value(f"{no_comp_ms:.2f} ms", "Makespan - Interval Union", "info", "Mathematically Derived")
            self.card_r_util.set_value(f"{real_res.worker_utilization_pct:.1f} %", "Worker core busy ratio", "info", "Mathematically Derived")
            self.card_r_mem.set_value(f"{real_res.peak_memory_rss_mb:.1f} MB", "Process RSS", "neutral", "Directly Measured")

            # Timeline
            r_tracks = []
            for wr in real_res.task_completions:
                w_id = wr.get("worker_id", 0)
                dur = wr.get("duration_s", 0.0)
                r_tracks.append({
                    "track_id": f"W-{w_id}",
                    "intervals": [(0.0, dur, QColor("#3fb950"))],
                })
            self.timeline_real.set_timeline_data(r_tracks, max(0.001, real_res.wall_clock_time_s))

        # 2. Render Virtual Lab Results
        if virt_res:
            m_ticks = virt_res.virtual_makespan_ticks
            self.card_v_makespan.set_value(f"{m_ticks:,} ticks", f"{virt_res.virtual_core_count} virtual cores", "neutral", "Simulated Virtual")
            self.card_v_util.set_value(f"{virt_res.virtual_core_utilization_pct:.1f} %", "Busy ticks / capacity", "info", "Simulated Virtual")
            self.card_v_wait.set_value(f"{virt_res.avg_waiting_ticks:.1f} ticks", "Queue delay", "neutral", "Simulated Virtual")
            self.card_v_turn.set_value(f"{virt_res.avg_turnaround_ticks:.1f} ticks", "Total lifetime", "neutral", "Simulated Virtual")
            self.card_v_thru.set_value(f"{virt_res.simulated_throughput_tasks_per_tick:.4f}", "Tasks per tick", "neutral", "Simulated Virtual")
            self.card_v_preempt.set_value(str(virt_res.preemption_count), "Context switches", "neutral", "Simulated Virtual")

            # Timeline
            v_tracks = []
            for t in virt_res.task_completion_order:
                cid = t.get("assigned_core_id", 0)
                s = t.get("start_tick", 0) or 0
                f = t.get("finish_tick", m_ticks) or m_ticks
                v_tracks.append({
                    "track_id": f"Core-{cid}",
                    "intervals": [(s, f, QColor("#58a6ff"))],
                })
            self.timeline_virt.set_timeline_data(v_tracks, float(max(1, m_ticks)))

        # 3. Render Comparative Analysis & Equivalence
        if analysis:
            eq_theme = "success" if analysis.workload_equivalence else "warning"
            eq_status = "Verified" if analysis.workload_equivalence else "Review"
            self.card_c_equiv.set_value(eq_status, analysis.workload_id if hasattr(analysis, 'workload_id') else "Workload", eq_theme, "Equivalence Status")
            self.card_c_ratio.set_value(f"{analysis.resource_allocation_ratio:.2f}", f"{analysis.real_worker_count}W / {analysis.virtual_core_count}C", "info", "Mathematically Derived")
            self.card_c_concord.set_value(f"{analysis.completion_order_concordance * 100:.1f} %", "Rank agreement", "info", "Mathematically Derived")
            self.card_c_udiff.set_value(f"{analysis.utilization_difference_pct:+.1f} %", "Real - Virtual", "info", "Mathematically Derived")
            self.equiv_detail_label.setText(analysis.workload_equivalence_details)

        # 4. Populate Detailed Task Comparison Table
        r_tasks = real_res.task_completions if real_res else []
        v_tasks = virt_res.task_completion_order if virt_res else []
        max_rows = max(len(r_tasks), len(v_tasks))
        self.comp_table.setRowCount(max_rows)

        for row in range(max_rows):
            r_item = r_tasks[row] if row < len(r_tasks) else {}
            v_item = v_tasks[row] if row < len(v_tasks) else {}

            t_id = r_item.get("task_id", v_item.get("task_id", f"Task-{row+1}"))
            r_dur = f"{r_item.get('duration_s', 0.0) * 1000.0:.2f} ms" if r_item else "--"
            r_pid = str(r_item.get("process_id", "--")) if r_item else "--"
            v_core = f"Core {v_item.get('assigned_core_id', '?')}" if v_item else "--"
            v_finish = f"{v_item.get('finish_tick', 0)} ticks" if v_item else "--"
            v_wait = f"{v_item.get('waiting_ticks', 0)} ticks" if v_item else "--"
            status = "Verified" if (r_item and v_item) else "Single-Env"

            self.comp_table.setItem(row, 0, QTableWidgetItem(str(t_id)))
            self.comp_table.setItem(row, 1, QTableWidgetItem(r_dur))
            self.comp_table.setItem(row, 2, QTableWidgetItem(r_pid))
            self.comp_table.setItem(row, 3, QTableWidgetItem(v_core))
            self.comp_table.setItem(row, 4, QTableWidgetItem(v_finish))
            self.comp_table.setItem(row, 5, QTableWidgetItem(v_wait))
            self.comp_table.setItem(row, 6, QTableWidgetItem(status))

    def shutdown(self) -> None:
        """Cancel and wait for background runner thread if running."""
        if hasattr(self, "runner_thread") and self.runner_thread.isRunning():
            self.runner_thread.cancel_execution()
            self.runner_thread.wait(2000)

