"""Core Monitor Page for CoreSync Workstation."""

import psutil
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class CoreMonitorPage(QWidget):
    """Workstation page for inspecting CPU topology, per-core load, and setting CPU affinity masks."""

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

        # 2. Hardware Topology Overview
        topology_grid = self._create_topology_grid()
        layout.addLayout(topology_grid)

        # 3. CPU Affinity Controls & Core Grid Preview
        affinity_card = self._create_affinity_card()
        layout.addWidget(affinity_card)

        # 4. Core Cards Grid Preview (Real detected core count)
        cores_panel = self._create_cores_panel()
        layout.addWidget(cores_panel)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Hardware CPU Core Monitor & Affinity Controller")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Inspect physical and logical CPU cores, Intel hybrid Performance (P) vs Efficient (E) topology, "
            "and configure worker process CPU affinity masks via POSIX sched_setaffinity."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_col.addWidget(StatusBadge("Live Sampler: Phase 4 Pending", "info"), alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_topology_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        physical = psutil.cpu_count(logical=False) or 14
        logical = psutil.cpu_count(logical=True) or 20

        self.card_phys = MetricCard(
            title="Physical Cores",
            value=f"{physical} Cores",
            subtitle="Silicon processing cores on socket",
            status_text="Verified",
            status_theme="success",
        )
        grid.addWidget(self.card_phys, 0, 0)

        self.card_log = MetricCard(
            title="Logical CPUs",
            value=f"{logical} Threads",
            subtitle="Total addressable execution contexts",
            status_text="Optimal",
            status_theme="success",
        )
        grid.addWidget(self.card_log, 0, 1)

        self.card_hybrid = MetricCard(
            title="Architecture",
            value="Hybrid P/E",
            subtitle="P-Cores (SMT) + E-Cores (Single-thread)",
            status_text="Intel 13th Gen",
            status_theme="info",
        )
        grid.addWidget(self.card_hybrid, 0, 2)

        self.card_affinity = MetricCard(
            title="Active Affinity Mask",
            value=f"0 - {logical - 1}",
            subtitle="Allowable CPU cores for spawned workers",
            status_text="Unrestricted",
            status_theme="neutral",
        )
        grid.addWidget(self.card_affinity, 0, 3)

        return grid

    def _create_affinity_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("CPU Affinity Mask Presets")
        title.setProperty("class", "heading-2")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        # Quick selection buttons
        btn_all = QPushButton("Select All Cores")
        btn_all.setProperty("class", "btn-secondary")
        header_layout.addWidget(btn_all)

        btn_pcores = QPushButton("P-Cores Only (0-11)")
        btn_pcores.setProperty("class", "btn-secondary")
        header_layout.addWidget(btn_pcores)

        btn_ecores = QPushButton("E-Cores Only (12-19)")
        btn_ecores.setProperty("class", "btn-secondary")
        header_layout.addWidget(btn_ecores)

        btn_clear = QPushButton("Reset Mask")
        btn_clear.setProperty("class", "btn-secondary")
        header_layout.addWidget(btn_clear)

        layout.addLayout(header_layout)

        notice = QLabel(
            "Note: CPU affinity restricts which logical CPUs a worker process is permitted to execute on via sched_setaffinity(). "
            "It does not guarantee exclusive core execution, as the Linux CFS kernel scheduler manages preemption and interrupts."
        )
        notice.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(notice)

        return card

    def _create_cores_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "card-alt")
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        title = QLabel("Logical CPU Core Utilization Grid (Preview)")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(10)

        logical_count = psutil.cpu_count(logical=True) or 20
        cols = 5

        for i in range(logical_count):
            core_box = QFrame()
            core_box.setProperty("class", "card")
            core_layout = QVBoxLayout(core_box)
            core_layout.setContentsMargins(10, 8, 10, 8)
            core_layout.setSpacing(4)

            top_row = QHBoxLayout()
            core_lbl = QLabel(f"CPU {i}")
            core_lbl.setStyleSheet("font-weight: 600; font-size: 11px;")
            top_row.addWidget(core_lbl)

            type_tag = "P-Core" if i < 12 else "E-Core"
            tag_color = "#388bfd" if i < 12 else "#a371f7"
            tag_lbl = QLabel(type_tag)
            tag_lbl.setStyleSheet(f"color: {tag_color}; font-size: 9px; font-weight: 600;")
            top_row.addWidget(tag_lbl, alignment=Qt.AlignRight)
            core_layout.addLayout(top_row)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            core_layout.addWidget(bar)

            load_lbl = QLabel("Awaiting Sampler")
            load_lbl.setProperty("class", "muted")
            load_lbl.setStyleSheet("font-size: 10px;")
            core_layout.addWidget(load_lbl)

            grid.addWidget(core_box, i // cols, i % cols)

        layout.addLayout(grid)
        return panel

