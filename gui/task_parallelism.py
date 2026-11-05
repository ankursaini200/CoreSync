"""Task Parallelism Workstation Page for CoreSync.

Integrates genuine CPU-bound task dependency graphs, pluggable scheduling policies,
dynamic spawn-based worker dispatch, real-time DAG canvas visualization, and telemetry.
"""

import logging
from typing import Dict, Optional

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

from engine.task_parallel.dispatcher import TaskDispatcher
from engine.task_parallel.presets import (
    PRESET_GENERATORS,
    create_diamond_pipeline,
)
from engine.task_parallel.result_collector import TaskDAGResult
from engine.task_parallel.task import Task, TaskPriority, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from engine.task_parallel.task_queue import SchedulingPolicy
from gui.components.badge import StatusBadge
from gui.components.dag_canvas import DAGCanvasWidget
from gui.components.metric_card import MetricCard
from gui.task_parallel_runner import TaskParallelRunnerThread
from utils.system_info import get_system_summary

logger = logging.getLogger("CoreSync.GUI.TaskParallelism")


class TaskParallelismPage(QWidget):
    """Interactive workstation interface for configuring, executing, and monitoring Task Parallelism DAGs."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary = get_system_summary()
        self.current_graph: Optional[TaskGraph] = None
        self.runner_thread = TaskParallelRunnerThread(self)
        self.runner_thread.task_status_changed.connect(self._on_task_status_changed)
        self.runner_thread.worker_status_changed.connect(self._on_worker_status_changed)
        self.runner_thread.progress_updated.connect(self._on_progress_updated)
        self.runner_thread.dag_finished.connect(self._on_dag_finished)
        self.runner_thread.dag_failed.connect(self._on_dag_failed)

        self._setup_ui()
        self._load_preset("Diamond Pipeline (4 Tasks)")

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

        # 2. Workload & Dispatch Configuration Card
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 3. Real-Time Execution Metrics Grid
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. DAG Visualizer Canvas Card
        dag_card = self._create_dag_card()
        layout.addWidget(dag_card)

        # 5. Active Worker Pool Status Cards
        worker_card = self._create_worker_pool_card()
        layout.addWidget(worker_card)

        # 6. Task Telemetry and Result Table
        table_card = self._create_task_table_card()
        layout.addWidget(table_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Task Parallelism Engine (DAG & Heterogeneous Workloads)")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Execute diverse CPU-bound tasks concurrently with Directed Acyclic Graph (DAG) dependencies, "
            "pluggable priority queues, fault tolerance retries, and isolated multiprocessing workers under spawn context."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.badge_status = StatusBadge("Engine: Ready", "success")
        status_col.addWidget(self.badge_status, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(16)

        title = QLabel("DAG Workload Configuration & Dispatch Controls")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Row 1: Preset selection & Scheduling Strategy
        lbl_preset = QLabel("DAG Workload Preset:")
        lbl_preset.setProperty("class", "metric-label")
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(list(PRESET_GENERATORS.keys()))
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)
        grid.addWidget(lbl_preset, 0, 0)
        grid.addWidget(self.combo_preset, 0, 1)

        lbl_policy = QLabel("Scheduling Policy:")
        lbl_policy.setProperty("class", "metric-label")
        self.combo_policy = QComboBox()
        self.combo_policy.addItem("First-Come, First-Served (FIFO)", SchedulingPolicy.FIFO)
        self.combo_policy.addItem("Priority Scheduling (Highest First)", SchedulingPolicy.PRIORITY)
        self.combo_policy.addItem("Shortest Job First (SJF)", SchedulingPolicy.SJF)
        grid.addWidget(lbl_policy, 0, 2)
        grid.addWidget(self.combo_policy, 0, 3)

        # Row 2: Worker allocation mode & Worker spinner
        lbl_mode = QLabel("Worker Allocation:")
        lbl_mode.setProperty("class", "metric-label")
        self.combo_worker_mode = QComboBox()
        self.combo_worker_mode.addItems(["Automatic (Hardware Optimal)", "Manual Allocation"])
        self.combo_worker_mode.currentIndexChanged.connect(self._on_worker_mode_changed)
        grid.addWidget(lbl_mode, 1, 0)
        grid.addWidget(self.combo_worker_mode, 1, 1)

        lbl_workers = QLabel("Worker Processes:")
        lbl_workers.setProperty("class", "metric-label")
        self.spin_workers = QSpinBox()
        max_limit = max(self.summary.logical_cores or 4, 32)
        self.spin_workers.setRange(1, max_limit)
        auto_w = TaskDispatcher.determine_automatic_workers()
        self.spin_workers.setValue(auto_w)
        self.spin_workers.setEnabled(False)  # Starts in Automatic mode
        grid.addWidget(lbl_workers, 1, 2)
        grid.addWidget(self.spin_workers, 1, 3)

        # Row 3: Host hardware note
        self.lbl_hw_info = QLabel(
            f"Detected Host: {self.summary.cpu_model} ({self.summary.physical_cores}P / {self.summary.logical_cores}L Cores)"
        )
        self.lbl_hw_info.setStyleSheet("color: #58a6ff; font-size: 11px; font-weight: 600;")
        grid.addWidget(self.lbl_hw_info, 2, 0, 1, 4)

        layout.addLayout(grid)

        # Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_run = QPushButton("Execute DAG Workload")
        self.btn_run.setProperty("class", "btn-primary")
        self.btn_run.clicked.connect(self._on_start_execution)
        btn_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton("Cancel Execution")
        self.btn_cancel.setProperty("class", "btn-secondary")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_reset = QPushButton("Reset Graph")
        self.btn_reset.setProperty("class", "btn-secondary")
        self.btn_reset.clicked.connect(self._on_reset_clicked)
        btn_layout.addWidget(self.btn_reset)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        # Progress bar & live activity readout
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("Ready. Select a DAG preset and click Execute DAG Workload.")
        self.lbl_progress_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(self.lbl_progress_status)

        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_total = MetricCard(
            title="Total Tasks",
            value="0",
            subtitle="Registered DAG nodes",
            status_text="Loaded",
            status_theme="neutral",
        )
        grid.addWidget(self.card_total, 0, 0)

        self.card_running = MetricCard(
            title="Running Tasks",
            value="0",
            subtitle="Actively executing in child PIDs",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_running, 0, 1)

        self.card_completed = MetricCard(
            title="Completed Tasks",
            value="0",
            subtitle="Successfully verified outputs",
            status_text="Pending",
            status_theme="neutral",
        )
        grid.addWidget(self.card_completed, 0, 2)

        self.card_failed = MetricCard(
            title="Failed / Blocked",
            value="0",
            subtitle="Exceptions or unfulfilled deps",
            status_text="None",
            status_theme="neutral",
        )
        grid.addWidget(self.card_failed, 0, 3)

        self.card_makespan = MetricCard(
            title="Parallel Makespan (T_par)",
            value="-- ms",
            subtitle="DAG wall-clock duration",
            status_text="Awaiting Run",
            status_theme="neutral",
        )
        grid.addWidget(self.card_makespan, 1, 0, 1, 2)

        self.card_speedup = MetricCard(
            title="Task Speedup & Efficiency",
            value="-- x",
            subtitle="T_sum / T_par across workers",
            status_text="Pending",
            status_theme="neutral",
        )
        grid.addWidget(self.card_speedup, 1, 2, 1, 2)

        return grid

    def _create_dag_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title_row = QHBoxLayout()
        title = QLabel("Directed Acyclic Graph (DAG) Execution Flow")
        title.setProperty("class", "heading-2")
        title_row.addWidget(title)
        title_row.addStretch(1)

        legend = QLabel("Legend: ■ Completed (Green)  ■ Running (Blue)  ■ Ready (Yellow)  ■ Blocked (Dark)  ■ Failed (Red)")
        legend.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_row.addWidget(legend)
        layout.addLayout(title_row)

        # DAG Canvas
        self.dag_canvas = DAGCanvasWidget()
        layout.addWidget(self.dag_canvas)

        return card

    def _create_worker_pool_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("Worker Process Allocation & Telemetry")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        self.worker_badges_layout = QHBoxLayout()
        self.worker_badges_layout.setSpacing(10)
        self.worker_badges: Dict[int, StatusBadge] = {}

        layout.addLayout(self.worker_badges_layout)
        return card

    def _create_task_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Individual Task Telemetry, Dependencies & Verification")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        self.table_tasks = QTableWidget()
        self.table_tasks.setColumnCount(8)
        self.table_tasks.setHorizontalHeaderLabels([
            "Task ID",
            "Name",
            "Type",
            "Priority",
            "Status",
            "Worker / PID",
            "Duration",
            "Dependencies",
        ])
        self.table_tasks.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_tasks.verticalHeader().setVisible(False)
        self.table_tasks.setFixedHeight(220)
        self.table_tasks.setAlternatingRowColors(True)
        layout.addWidget(self.table_tasks)

        return card

    def _load_preset(self, preset_name: str) -> None:
        """Instantiate preset DAG and populate UI."""
        generator = PRESET_GENERATORS.get(preset_name, create_diamond_pipeline)
        self.current_graph = generator()
        self.dag_canvas.set_graph(self.current_graph)
        self._populate_task_table()
        self._update_metrics_summary()

    def _populate_task_table(self) -> None:
        """Populate the telemetry table with tasks from current_graph."""
        if not self.current_graph:
            return

        tasks = list(self.current_graph.tasks.values())
        self.table_tasks.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            self.table_tasks.setItem(row, 0, QTableWidgetItem(task.task_id))
            self.table_tasks.setItem(row, 1, QTableWidgetItem(task.name))
            self.table_tasks.setItem(row, 2, QTableWidgetItem(task.task_type))
            self.table_tasks.setItem(row, 3, QTableWidgetItem(str(task.priority)))
            self.table_tasks.setItem(row, 4, QTableWidgetItem(task.status.value.upper()))
            self.table_tasks.setItem(row, 5, QTableWidgetItem("Pending"))
            self.table_tasks.setItem(row, 6, QTableWidgetItem("--"))
            deps_str = ", ".join(task.dependencies) if task.dependencies else "None (Root)"
            self.table_tasks.setItem(row, 7, QTableWidgetItem(deps_str))

    def _update_metrics_summary(self) -> None:
        """Refresh top-level metric cards from current graph state."""
        if not self.current_graph:
            return

        tasks = list(self.current_graph.tasks.values())
        total = len(tasks)
        running = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        failed_blocked = sum(1 for t in tasks if t.status in (TaskStatus.FAILED, TaskStatus.BLOCKED))

        self.card_total.set_value(str(total))
        self.card_running.set_value(str(running))
        self.card_running.set_status("Active" if running > 0 else "Idle", "info" if running > 0 else "neutral")

        self.card_completed.set_value(str(completed))
        self.card_completed.set_status(f"{int(completed/total*100)}%" if total > 0 else "0%", "success" if completed == total else "neutral")

        self.card_failed.set_value(str(failed_blocked))
        self.card_failed.set_status("Alert" if failed_blocked > 0 else "Clean", "danger" if failed_blocked > 0 else "neutral")

    @Slot(str)
    def _on_preset_changed(self, preset_name: str) -> None:
        self._load_preset(preset_name)

    @Slot(int)
    def _on_worker_mode_changed(self, index: int) -> None:
        # Index 0: Automatic, Index 1: Manual
        if index == 0:
            self.spin_workers.setEnabled(False)
            auto_w = TaskDispatcher.determine_automatic_workers()
            self.spin_workers.setValue(auto_w)
        else:
            self.spin_workers.setEnabled(True)

    def _on_start_execution(self) -> None:
        if not self.current_graph:
            return

        worker_count = self.spin_workers.value()
        policy = self.combo_policy.currentData() or SchedulingPolicy.FIFO

        # Reset task table
        self._populate_task_table()
        self.progress_bar.setValue(0)
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_reset.setEnabled(False)
        self.badge_status.set_status("Executing DAG", "warning")

        # Initialize worker badges
        # Clear existing badges
        while self.worker_badges_layout.count():
            item = self.worker_badges_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.worker_badges.clear()

        for w_id in range(worker_count):
            badge = StatusBadge(f"Worker {w_id}: Initializing", "neutral")
            self.worker_badges_layout.addWidget(badge)
            self.worker_badges[w_id] = badge

        self.runner_thread.configure(self.current_graph, worker_count, policy)
        self.runner_thread.start()

    def _on_cancel_clicked(self) -> None:
        self.lbl_progress_status.setText("Cancelling DAG execution and reaping workers...")
        self.runner_thread.cancel()

    def _on_reset_clicked(self) -> None:
        preset_name = self.combo_preset.currentText()
        self._load_preset(preset_name)
        self.progress_bar.setValue(0)
        self.lbl_progress_status.setText("Pipeline reset. Ready to execute.")
        self.card_makespan.set_value("-- ms")
        self.card_speedup.set_value("-- x")

    @Slot(str, str, str, str, str)
    def _on_task_status_changed(self, task_id: str, status: str, error: str, pid_str: str, duration_str: str) -> None:
        # Update Canvas
        self.dag_canvas.update_task_state(task_id)

        # Update Table row
        if self.current_graph:
            for row in range(self.table_tasks.rowCount()):
                item = self.table_tasks.item(row, 0)
                if item and item.text() == task_id:
                    self.table_tasks.setItem(row, 4, QTableWidgetItem(status.upper()))
                    self.table_tasks.setItem(row, 5, QTableWidgetItem(pid_str))
                    self.table_tasks.setItem(row, 6, QTableWidgetItem(duration_str))
                    break

        self._update_metrics_summary()

    @Slot(int, int, str)
    def _on_worker_status_changed(self, worker_id: int, pid: int, msg: str) -> None:
        badge = self.worker_badges.get(worker_id)
        if badge:
            theme = "info" if "Running" in msg else "neutral"
            badge.set_status(f"Worker {worker_id} (PID {pid}): {msg}", theme)

    @Slot(int, int, str)
    def _on_progress_updated(self, completed: int, total: int, msg: str) -> None:
        self.lbl_progress_status.setText(msg)
        if total > 0:
            pct = int((completed / total) * 100)
            self.progress_bar.setValue(pct)

    @Slot(object)
    def _on_dag_finished(self, result: TaskDAGResult) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_reset.setEnabled(True)
        self.progress_bar.setValue(100)

        theme = "success" if result.success else "warning"
        status_label = "DAG Execution Succeeded" if result.success else "DAG Finished with Failures"
        self.badge_status.set_status(status_label, theme)

        self.card_makespan.set_value(f"{result.makespan_s * 1000:.1f} ms")
        self.card_makespan.set_status(f"Makespan ({result.worker_count} Workers)", "success")

        self.card_speedup.set_value(f"{result.speedup:.2f} x")
        self.card_speedup.set_status(f"{result.worker_utilization_pct:.1f}% Utilization", "info")

        self.lbl_progress_status.setText(
            f"DAG execution completed in {result.makespan_s * 1000:.1f} ms. "
            f"Tasks: {result.completed_tasks}/{result.total_tasks} completed. "
            f"Cumulative Work: {result.cumulative_compute_s * 1000:.1f} ms."
        )

        self.dag_canvas.update()
        self._update_metrics_summary()

    @Slot(str)
    def _on_dag_failed(self, error_msg: str) -> None:
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_reset.setEnabled(True)
        self.badge_status.set_status("DAG Execution Failed", "danger")
        self.lbl_progress_status.setText(f"Failed: {error_msg}")
        self.dag_canvas.update()
        self._update_metrics_summary()

    def shutdown(self) -> None:
        """Cleanly terminate runner thread on page closure."""
        if self.runner_thread.isRunning():
            self.runner_thread.cancel()
            self.runner_thread.wait(1000)
