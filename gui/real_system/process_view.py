"""Real System Process Monitor View for CoreSync."""

from typing import List, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from utils.hardware.base import ProcessInfo
from monitoring.cpu_monitor import CPUMetricsSnapshot
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class RealProcessPage(QWidget):
    """Monitors running operating system processes and tracks active CoreSync worker processes."""

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

        # 2. Metric Cards (Worker count, total tracked)
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 3. Process Table Card
        table_card = self._create_table_card()
        layout.addWidget(table_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Real System Process & Worker Monitor")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Inspect live running operating system processes, real-time CPU consumption, memory footprint, "
            "and active CoreSync child worker processes."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Real OS Processes (psutil)", "success"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_metrics_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.card_workers = MetricCard(
            title="CoreSync Worker Processes",
            value="0 Workers",
            subtitle="Active child processes spawned by CoreSync",
            status_text="Idle",
            status_theme="neutral",
        )
        layout.addWidget(self.card_workers)

        self.card_top_proc = MetricCard(
            title="Top CPU Consumer",
            value="--",
            subtitle="Process consuming the highest CPU slice",
            status_text="Sampling",
            status_theme="info",
        )
        layout.addWidget(self.card_top_proc)

        return layout

    def _create_table_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Live Top Operating System Processes")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

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
        self.table.setMinimumHeight(320)
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

    @Slot(CPUMetricsSnapshot)
    def update_metrics(self, snapshot: CPUMetricsSnapshot) -> None:
        """Update process table and worker counts from snapshot."""
        worker_count = snapshot.coresync_workers_count
        self.card_workers.set_value(f"{worker_count} Workers")
        self.card_workers.set_status("Active" if worker_count > 0 else "Idle", "success" if worker_count > 0 else "neutral")

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

