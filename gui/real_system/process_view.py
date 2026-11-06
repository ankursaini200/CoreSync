"""Real System Process Monitor and Worker Lifecycle Management View for CoreSync."""

import time
from typing import List, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from engine.affinity import AffinityPolicy, get_available_system_cpus
from engine.process_manager import ProcessManager, WorkerLifecycleStatus, WorkerMetadata
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard
from monitoring.cpu_monitor import CPUMetricsSnapshot
from utils.hardware.base import ProcessInfo


class RealProcessPage(QWidget):
    """Monitors running operating system processes and manages CoreSync worker lifecycles and affinity."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_policy = AffinityPolicy.AUTOMATIC
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

        # 2. Metric Cards Grid
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 3. CoreSync Worker Processes Section (Dedicated Control Card)
        cs_workers_card = self._create_coresync_workers_card()
        layout.addWidget(cs_workers_card)

        # 4. OS Processes Table Card
        table_card = self._create_os_table_card()
        layout.addWidget(table_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Real System Process & Worker Lifecycle Manager")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Track active child workers across Data Parallelism, Task Parallelism, and Real CPU Stress. "
            "Inspect assigned CPU affinity masks, monitor resource usage, and reap orphaned processes."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Unified Process Manager", "success"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_metrics_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.card_workers = MetricCard(
            title="CoreSync Active Workers",
            value="0 Workers",
            subtitle="Spawned processes across engines",
            status_text="Idle",
            status_theme="neutral",
        )
        layout.addWidget(self.card_workers)

        self.card_affinity = MetricCard(
            title="CPU Affinity Policy",
            value="Automatic",
            subtitle=f"{len(get_available_system_cpus())} Logical Cores Available",
            status_text="Hardware Ready",
            status_theme="info",
        )
        layout.addWidget(self.card_affinity)

        self.card_top_proc = MetricCard(
            title="Top OS CPU Consumer",
            value="--",
            subtitle="Process with highest CPU consumption",
            status_text="Sampling",
            status_theme="neutral",
        )
        layout.addWidget(self.card_top_proc)

        self.card_orphans = MetricCard(
            title="Orphan Detection",
            value="0 Detected",
            subtitle="Dangling worker processes",
            status_text="Clean",
            status_theme="success",
        )
        layout.addWidget(self.card_orphans)

        return layout

    def _create_coresync_workers_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # Header row with title and action buttons
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Active CoreSync Worker Processes")
        title.setProperty("class", "heading-2")
        title_box.addWidget(title)

        subtitle = QLabel("Dedicated tracking of child processes spawned by CoreSync execution engines")
        subtitle.setStyleSheet("color: #8b949e; font-size: 11px;")
        title_box.addWidget(subtitle)
        header_row.addLayout(title_box)
        header_row.addStretch(1)

        # Policy selector
        lbl_pol = QLabel("Default Affinity:")
        lbl_pol.setStyleSheet("color: #8b949e; font-size: 11px;")
        header_row.addWidget(lbl_pol)

        self.combo_policy = QComboBox()
        self.combo_policy.addItems([
            "Automatic (All Cores)",
            "Round Robin",
            "One-to-One Pinning",
            "P-Core Only (Performance)",
            "E-Core Only (Efficiency)",
        ])
        self.combo_policy.currentIndexChanged.connect(self._on_policy_changed)
        header_row.addWidget(self.combo_policy)

        # Reaping and kill buttons
        self.btn_reap = QPushButton("Reap Orphans")
        self.btn_reap.setToolTip("Scan operating system and cleanly terminate any dangling CoreSync workers")
        self.btn_reap.clicked.connect(self._on_reap_orphans_clicked)
        header_row.addWidget(self.btn_reap)

        self.btn_kill_all = QPushButton("Cancel All Workers")
        self.btn_kill_all.setProperty("class", "danger")
        self.btn_kill_all.setStyleSheet("background-color: #f85149; color: white; font-weight: 600; padding: 4px 10px; border-radius: 4px;")
        self.btn_kill_all.clicked.connect(self._on_cancel_all_clicked)
        header_row.addWidget(self.btn_kill_all)

        layout.addLayout(header_row)

        # CoreSync Worker Table
        self.table_workers = QTableWidget(self)
        self.table_workers.setColumnCount(10)
        self.table_workers.setHorizontalHeaderLabels([
            "Worker ID",
            "PID",
            "Parent PID",
            "Engine",
            "Task / Chunk",
            "Assigned CPUs",
            "Status",
            "CPU %",
            "Memory (MB)",
            "Action",
        ])
        self.table_workers.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_workers.setMinimumHeight(180)
        self.table_workers.setAlternatingRowColors(True)
        self.table_workers.verticalHeader().setVisible(False)
        self.table_workers.setStyleSheet("""
            QTableWidget {
                background-color: #161b24;
                border: 1px solid #283344;
                border-radius: 6px;
                gridline-color: #283344;
            }
            QHeaderView::section {
                background-color: #1c2330;
                color: #58a6ff;
                font-weight: 600;
                padding: 6px;
                border: 1px solid #283344;
            }
        """)
        layout.addWidget(self.table_workers)

        return card

    def _create_os_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Host Operating System Processes (psutil)")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        subtitle = QLabel("Live operating system process telemetry (strictly isolated from CoreSync control)")
        subtitle.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(subtitle)

        self.table = QTableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "PID",
            "Process Name",
            "CPU %",
            "Memory (MB)",
            "Memory %",
            "CoreSync Worker?",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(260)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
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
        layout.addWidget(self.table)
        return card

    def _on_policy_changed(self, index: int) -> None:
        policy_map = {
            0: AffinityPolicy.AUTOMATIC,
            1: AffinityPolicy.ROUND_ROBIN,
            2: AffinityPolicy.ONE_TO_ONE,
            3: AffinityPolicy.P_CORE_ONLY,
            4: AffinityPolicy.E_CORE_ONLY,
        }
        self._current_policy = policy_map.get(index, AffinityPolicy.AUTOMATIC)
        self.card_affinity.set_value(self._current_policy.value.replace("_", " ").title())

    def _on_cancel_all_clicked(self) -> None:
        """Cancel all registered active CoreSync workers."""
        workers = ProcessManager.get_global_active_workers()
        if not workers:
            return

        for w in workers:
            if w.pid:
                try:
                    import psutil
                    proc = psutil.Process(w.pid)
                    proc.terminate()
                except Exception:
                    pass

    def _on_reap_orphans_clicked(self) -> None:
        """Scan and terminate orphaned CoreSync workers."""
        reaped = ProcessManager.reap_orphans(timeout_s=1.0)
        self.card_orphans.set_value(f"{reaped} Reaped" if reaped > 0 else "0 Detected")
        self.card_orphans.set_status("Cleaned" if reaped > 0 else "Clean", "success")

    def _terminate_single_worker(self, pid: int) -> None:
        """Gracefully terminate an individual CoreSync worker process."""
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.terminate()
            try:
                proc.wait(timeout=0.4)
            except psutil.TimeoutExpired:
                proc.kill()
        except Exception:
            pass

    @Slot(CPUMetricsSnapshot)
    def update_metrics(self, snapshot: CPUMetricsSnapshot) -> None:
        """Update both CoreSync workers table and OS processes table from snapshot."""
        # 1. Update CoreSync Active Workers
        cs_workers = snapshot.coresync_workers or ProcessManager.get_global_active_workers()
        active_count = len(cs_workers)

        self.card_workers.set_value(f"{active_count} Workers")
        self.card_workers.set_status("Active" if active_count > 0 else "Idle", "success" if active_count > 0 else "neutral")

        # Check orphans
        orphans = ProcessManager.detect_orphans()
        orphan_count = len(orphans)
        self.card_orphans.set_value(f"{orphan_count} Detected" if orphan_count > 0 else "0 Detected")
        self.card_orphans.set_status("Warning" if orphan_count > 0 else "Clean", "warning" if orphan_count > 0 else "success")

        # Populate CoreSync workers table
        self.table_workers.setRowCount(len(cs_workers))
        for row, w in enumerate(cs_workers):
            self.table_workers.setItem(row, 0, QTableWidgetItem(str(w.worker_id)))
            self.table_workers.setItem(row, 1, QTableWidgetItem(str(w.pid or "--")))
            self.table_workers.setItem(row, 2, QTableWidgetItem(str(w.parent_pid)))
            self.table_workers.setItem(row, 3, QTableWidgetItem(w.engine_name))
            self.table_workers.setItem(row, 4, QTableWidgetItem(str(w.task_or_chunk_id or "--")))

            # Affinity string representation
            aff_str = str(w.assigned_cpu_affinity) if w.assigned_cpu_affinity else "All Cores"
            self.table_workers.setItem(row, 5, QTableWidgetItem(aff_str))

            status_item = QTableWidgetItem(w.status.value.upper())
            if w.status == WorkerLifecycleStatus.RUNNING:
                status_item.setForeground(Qt.green)
            elif w.status == WorkerLifecycleStatus.IDLE:
                status_item.setForeground(Qt.cyan)
            self.table_workers.setItem(row, 6, status_item)

            self.table_workers.setItem(row, 7, QTableWidgetItem(f"{w.cpu_utilization:.1f}%"))
            self.table_workers.setItem(row, 8, QTableWidgetItem(f"{w.memory_rss_mb:.1f} MB"))

            # Cancel / Terminate Action button
            if w.pid:
                btn_cancel = QPushButton("Terminate")
                btn_cancel.setStyleSheet("background-color: #3b2024; color: #f85149; border: 1px solid #f85149; border-radius: 3px; font-size: 10px; font-weight: 600;")
                btn_cancel.clicked.connect(lambda _, target_pid=w.pid: self._terminate_single_worker(target_pid))
                self.table_workers.setCellWidget(row, 9, btn_cancel)

        # 2. Update Top OS Processes
        top_procs = snapshot.top_processes
        if top_procs:
            self.card_top_proc.set_value(f"{top_procs[0].name} ({top_procs[0].cpu_percent:.1f}%)")

        self.table.setRowCount(len(top_procs))
        for row, p in enumerate(top_procs):
            item_pid = QTableWidgetItem(str(p.pid))
            item_name = QTableWidgetItem(p.name)
            item_cpu = QTableWidgetItem(f"{p.cpu_percent:.1f}%")
            item_mem = QTableWidgetItem(f"{p.memory_rss_mb:.1f} MB")
            item_memp = QTableWidgetItem(f"{p.memory_percent:.1f}%")

            is_cs = "YES (CoreSync)" if p.is_coresync_worker else "No"
            item_cs = QTableWidgetItem(is_cs)
            if p.is_coresync_worker:
                item_cs.setForeground(Qt.green)

            self.table.setItem(row, 0, item_pid)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_cpu)
            self.table.setItem(row, 3, item_mem)
            self.table.setItem(row, 4, item_memp)
            self.table.setItem(row, 5, item_cs)
