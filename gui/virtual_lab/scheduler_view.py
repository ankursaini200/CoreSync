"""Virtual Lab Educational Task Scheduler Workbench for CoreSync."""

from typing import Optional
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm, VirtualScheduler
from engine.virtual_lab.workload_generator import VirtualWorkloadGenerator
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class VirtualSchedulerPage(QWidget):
    """Interactive educational lab for exploring CPU scheduling policies across virtual cores."""

    simulation_stepped = Signal()

    def __init__(self, scheduler: VirtualScheduler, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scheduler = scheduler
        self._sim_timer = QTimer(self)
        self._sim_timer.setInterval(60)  # ~16.6 ticks/sec
        self._sim_timer.timeout.connect(self._on_timer_step)
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

        # 2. Control & Workload Generation Card
        controls_card = self._create_controls_card()
        layout.addWidget(controls_card)

        # 3. Scheduling Metrics Cards
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Tables: Ready Queue & Completed Tasks
        tables_card = self._create_tables_card()
        layout.addWidget(tables_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Educational Multicore Scheduling Lab")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Observe FCFS, Priority, and Round Robin scheduling algorithms dispatching synthetic "
            "workloads across your configured virtual multicore processor."
        )
        desc.setStyleSheet("color: #9AA5B4;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.header_badge = StatusBadge("Simulation Ready", "neutral")
        status_col.addWidget(self.header_badge, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_controls_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        title = QLabel("Scheduler Policy & Workload Injection")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        # Row 1: Algorithm, Time Quantum, Workload preset
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        lbl_algo = QLabel("Algorithm:")
        lbl_algo.setProperty("class", "metric-label")
        row1.addWidget(lbl_algo)

        self.combo_algo = QComboBox()
        self.combo_algo.addItems([
            "First Come First Served (FCFS)",
            "Priority Scheduling (Non-preemptive)",
            "Round Robin (Preemptive Time Quantum)",
        ])
        self.combo_algo.currentIndexChanged.connect(self._on_algorithm_changed)
        row1.addWidget(self.combo_algo, stretch=2)

        self.lbl_quantum = QLabel("Time Quantum (ticks):")
        self.lbl_quantum.setProperty("class", "metric-label")
        row1.addWidget(self.lbl_quantum)

        self.spin_quantum = QSpinBox()
        self.spin_quantum.setRange(5, 100)
        self.spin_quantum.setValue(self.scheduler.time_quantum)
        self.spin_quantum.valueChanged.connect(self._on_quantum_changed)
        row1.addWidget(self.spin_quantum, stretch=1)

        self.lbl_quantum.setEnabled(False)
        self.spin_quantum.setEnabled(False)

        row1.addStretch(1)
        layout.addLayout(row1)

        # Row 2: Workload generator presets & buttons
        row2 = QHBoxLayout()
        row2.setSpacing(14)

        lbl_workload = QLabel("Workload Batch:")
        lbl_workload.setProperty("class", "metric-label")
        row2.addWidget(lbl_workload)

        self.combo_workload = QComboBox()
        self.combo_workload.addItems([
            "Light Mix (12 Tasks, 10-30 ticks)",
            "Equal Bursts (16 Tasks, 25 ticks each)",
            "Priority Mix (20 Tasks, Varied High/Med/Low)",
            "Heavy Stress Batch (48 Tasks, 15-60 ticks)",
        ])
        row2.addWidget(self.combo_workload, stretch=2)

        self.btn_enqueue = QPushButton("Enqueue Tasks")
        self.btn_enqueue.setProperty("class", "btn-primary")
        self.btn_enqueue.clicked.connect(self._enqueue_batch)
        row2.addWidget(self.btn_enqueue)

        row2.addStretch(1)
        layout.addLayout(row2)

        # Row 3: Simulation Execution Controls
        row3 = QHBoxLayout()
        row3.setSpacing(10)

        self.btn_step1 = QPushButton("Step 1 Tick")
        self.btn_step1.setProperty("class", "btn-secondary")
        self.btn_step1.clicked.connect(lambda: self._step_simulation(1))
        row3.addWidget(self.btn_step1)

        self.btn_step10 = QPushButton("Step 10 Ticks")
        self.btn_step10.setProperty("class", "btn-secondary")
        self.btn_step10.clicked.connect(lambda: self._step_simulation(10))
        row3.addWidget(self.btn_step10)

        self.btn_run = QPushButton("Run Continuous Simulation")
        self.btn_run.setProperty("class", "btn-primary")
        self.btn_run.clicked.connect(self._toggle_simulation)
        row3.addWidget(self.btn_run)

        self.btn_reset = QPushButton("Reset Queues & Cores")
        self.btn_reset.setProperty("class", "btn-secondary")
        self.btn_reset.clicked.connect(self._reset_scheduler)
        row3.addWidget(self.btn_reset)

        row3.addStretch(1)
        layout.addLayout(row3)

        return card

    def _create_metrics_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.card_ready = MetricCard(
            title="Ready Queue",
            value="0 Tasks",
            subtitle="Tasks waiting for idle core",
            status_text="Empty",
            status_theme="neutral",
        )
        layout.addWidget(self.card_ready)

        self.card_done = MetricCard(
            title="Completed Tasks",
            value="0 Finished",
            subtitle="Successfully processed",
            status_text="None",
            status_theme="neutral",
        )
        layout.addWidget(self.card_done)

        self.card_wait = MetricCard(
            title="Avg Waiting Time",
            value="0.0 Ticks",
            subtitle="Time spent in ready queue",
            status_text="Optimal",
            status_theme="success",
        )
        layout.addWidget(self.card_wait)

        self.card_turnaround = MetricCard(
            title="Avg Turnaround Time",
            value="0.0 Ticks",
            subtitle="Arrival to completion latency",
            status_text="Standard",
            status_theme="info",
        )
        layout.addWidget(self.card_turnaround)

        return layout

    def _create_tables_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Ready Queue Table
        lbl_ready = QLabel("Active Ready Queue (Waiting for Virtual Cores)")
        lbl_ready.setProperty("class", "heading-3")
        layout.addWidget(lbl_ready)

        self.table_ready = QTableWidget()
        self.table_ready.setColumnCount(6)
        self.table_ready.setHorizontalHeaderLabels([
            "Task ID", "Name", "Priority", "Total Burst", "Remaining Ticks", "Waiting Ticks"
        ])
        self.table_ready.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_ready.verticalHeader().setVisible(False)
        self.table_ready.setFixedHeight(160)
        layout.addWidget(self.table_ready)

        # Completed Tasks Table
        lbl_done = QLabel("Completed Tasks History")
        lbl_done.setProperty("class", "heading-3")
        layout.addWidget(lbl_done)

        self.table_done = QTableWidget()
        self.table_done.setColumnCount(6)
        self.table_done.setHorizontalHeaderLabels([
            "Task ID", "Assigned Core", "Arrival Tick", "Finish Tick", "Turnaround", "Waiting Ticks"
        ])
        self.table_done.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_done.verticalHeader().setVisible(False)
        self.table_done.setFixedHeight(160)
        layout.addWidget(self.table_done)

        return card

    def _on_algorithm_changed(self, index: int) -> None:
        if index == 0:
            self.scheduler.algorithm = SchedulingAlgorithm.FCFS
            self.lbl_quantum.setEnabled(False)
            self.spin_quantum.setEnabled(False)
        elif index == 1:
            self.scheduler.algorithm = SchedulingAlgorithm.PRIORITY
            self.lbl_quantum.setEnabled(False)
            self.spin_quantum.setEnabled(False)
        elif index == 2:
            self.scheduler.algorithm = SchedulingAlgorithm.ROUND_ROBIN
            self.lbl_quantum.setEnabled(True)
            self.spin_quantum.setEnabled(True)

    def _on_quantum_changed(self, val: int) -> None:
        self.scheduler.time_quantum = val

    def _enqueue_batch(self) -> None:
        idx = self.combo_workload.currentIndex()
        if idx == 0:
            tasks = VirtualWorkloadGenerator.generate_batch(count=12, burst_range=(10, 30))
        elif idx == 1:
            tasks = VirtualWorkloadGenerator.generate_batch(count=16, burst_range=(25, 25))
        elif idx == 2:
            tasks = VirtualWorkloadGenerator.generate_batch(count=20, burst_range=(10, 40))
        else:
            tasks = VirtualWorkloadGenerator.generate_batch(count=48, burst_range=(15, 60))

        self.scheduler.submit_batch(tasks)
        self.scheduler.dispatch()
        self.refresh_display()
        self.simulation_stepped.emit()

    def _step_simulation(self, ticks: int = 1) -> None:
        self.scheduler.step(tick_delta=ticks)
        self.refresh_display()
        self.simulation_stepped.emit()

    def _on_timer_step(self) -> None:
        if not self.scheduler.ready_queue and not [c for c in self.scheduler.virtual_cpu.cores.values() if c.current_task]:
            # Everything finished, stop timer
            self._toggle_simulation()
            return

        self._step_simulation(1)

    def _toggle_simulation(self) -> None:
        if self._sim_timer.isActive():
            self._sim_timer.stop()
            self.btn_run.setText("Run Continuous Simulation")
            self.btn_run.setProperty("class", "btn-primary")
            self.header_badge.set_status("Paused", "warning")
        else:
            self._sim_timer.start()
            self.btn_run.setText("Pause Simulation")
            self.btn_run.setProperty("class", "btn-secondary")
            self.header_badge.set_status("Running Simulation", "success")

    def _reset_scheduler(self) -> None:
        if self._sim_timer.isActive():
            self._sim_timer.stop()
            self.btn_run.setText("Run Continuous Simulation")
        self.scheduler.reset()
        self.refresh_display()
        self.simulation_stepped.emit()
        self.header_badge.set_status("Queues Reset", "neutral")

    def refresh_display(self) -> None:
        """Update tables and metrics."""
        ready_count = len(self.scheduler.ready_queue)
        done_count = len(self.scheduler.completed_tasks)
        avg_wait = self.scheduler.avg_waiting_time
        avg_ta = self.scheduler.avg_turnaround_time

        self.card_ready.set_value(f"{ready_count} Tasks")
        self.card_ready.set_status("Active" if ready_count > 0 else "Empty", "info" if ready_count > 0 else "neutral")

        self.card_done.set_value(f"{done_count} Finished")
        self.card_done.set_status(f"{done_count} Completed", "success" if done_count > 0 else "neutral")

        self.card_wait.set_value(f"{avg_wait:.1f} Ticks")
        self.card_turnaround.set_value(f"{avg_ta:.1f} Ticks")

        # Update Ready Queue Table
        self.table_ready.setRowCount(ready_count)
        for row, task in enumerate(self.scheduler.ready_queue):
            self.table_ready.setItem(row, 0, QTableWidgetItem(f"#{task.task_id}"))
            self.table_ready.setItem(row, 1, QTableWidgetItem(task.name))
            self.table_ready.setItem(row, 2, QTableWidgetItem(task.priority.name))
            self.table_ready.setItem(row, 3, QTableWidgetItem(f"{task.burst_ticks:.0f}"))
            self.table_ready.setItem(row, 4, QTableWidgetItem(f"{task.remaining_ticks:.0f}"))
            self.table_ready.setItem(row, 5, QTableWidgetItem(f"{task.waiting_ticks}"))

        # Update Completed Table (recent 30)
        recent_done = self.scheduler.completed_tasks[-30:]
        self.table_done.setRowCount(len(recent_done))
        for row, task in enumerate(reversed(recent_done)):
            cid = f"Core #{task.assigned_core_id}" if task.assigned_core_id is not None else "N/A"
            fin = f"{task.completion_tick}" if task.completion_tick is not None else "N/A"
            ta = f"{task.turnaround_ticks}" if task.turnaround_ticks is not None else "N/A"

            self.table_done.setItem(row, 0, QTableWidgetItem(f"#{task.task_id}"))
            self.table_done.setItem(row, 1, QTableWidgetItem(cid))
            self.table_done.setItem(row, 2, QTableWidgetItem(f"{task.arrival_tick}"))
            self.table_done.setItem(row, 3, QTableWidgetItem(fin))
            self.table_done.setItem(row, 4, QTableWidgetItem(ta))
            self.table_done.setItem(row, 5, QTableWidgetItem(f"{task.waiting_ticks}"))

    def shutdown(self) -> None:
        """Stop simulation timer."""
        if self._sim_timer.isActive():
            self._sim_timer.stop()

