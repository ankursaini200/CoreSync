"""Core Monitor Page for CoreSync Workstation.

Displays verified hardware topology, P-Core / E-Core classifications,
live per-core utilization meters, and affinity mask previews.
"""

from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
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

from utils.config import (
    COLOR_P_CORE,
    COLOR_E_CORE,
    COLOR_TEXT_MUTED,
    COLOR_BORDER,
    COLOR_ACCENT,
)
from utils.system_info import SystemSummary, get_system_summary
from utils.cpu_topology import CoreType
from monitoring.cpu_monitor import CPUMetricsSnapshot
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class CoreWidget(QFrame):
    """Widget displaying a single logical CPU's utilization bar, type, and live metrics."""

    def __init__(
        self,
        cpu_id: int,
        core_type: CoreType = CoreType.UNKNOWN,
        physical_core_id: Optional[int] = None,
        max_freq_mhz: Optional[float] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.cpu_id = cpu_id
        self.core_type = core_type
        self.physical_core_id = physical_core_id
        self.max_freq_mhz = max_freq_mhz
        self._is_highlighted = True

        self.setProperty("class", "card")
        self.setObjectName(f"coreBox_{cpu_id}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: CPU ID & Core Type Tag
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel(f"CPU {cpu_id}", self)
        self.title_lbl.setStyleSheet("font-weight: 700; font-size: 12px;")
        top_row.addWidget(self.title_lbl)

        # Tag label according to reliable core-type detection
        tag_text = "Core"
        tag_color = COLOR_TEXT_MUTED
        if core_type == CoreType.PERFORMANCE:
            tag_text = "P-Core"
            tag_color = COLOR_P_CORE
        elif core_type == CoreType.EFFICIENCY:
            tag_text = "E-Core"
            tag_color = COLOR_E_CORE

        self.tag_lbl = QLabel(tag_text, self)
        self.tag_lbl.setStyleSheet(f"color: {tag_color}; font-size: 10px; font-weight: 700;")
        top_row.addWidget(self.tag_lbl, alignment=Qt.AlignRight)
        layout.addLayout(top_row)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Metrics row: Percent & Frequency
        metrics_row = QHBoxLayout()
        metrics_row.setContentsMargins(0, 0, 0, 0)

        self.percent_lbl = QLabel("0.0%", self)
        self.percent_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        metrics_row.addWidget(self.percent_lbl)

        freq_str = f"{int(max_freq_mhz)} MHz" if max_freq_mhz else "-- MHz"
        self.freq_lbl = QLabel(freq_str, self)
        self.freq_lbl.setProperty("class", "muted")
        self.freq_lbl.setStyleSheet("font-size: 10px;")
        metrics_row.addWidget(self.freq_lbl, alignment=Qt.AlignRight)

        layout.addLayout(metrics_row)

    def update_metrics(self, percent: float, freq_mhz: Optional[float] = None) -> None:
        """Update live utilization percentage and current frequency."""
        val = max(0, min(int(round(percent)), 100))
        self.progress_bar.setValue(val)
        self.percent_lbl.setText(f"{percent:.1f}%")
        if freq_mhz is not None and freq_mhz > 0:
            self.freq_lbl.setText(f"{int(round(freq_mhz))} MHz")

    def set_affinity_highlight(self, enabled: bool) -> None:
        """Dim or highlight card based on affinity preview selection."""
        self._is_highlighted = enabled
        if enabled:
            self.setStyleSheet("")
        else:
            self.setStyleSheet(f"QFrame#coreBox_{self.cpu_id} {{ opacity: 0.35; border: 1px dashed {COLOR_BORDER}; }}")


class CoreMonitorPage(QWidget):
    """Workstation page for inspecting CPU topology, live per-core load, and affinity masks."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.summary: SystemSummary = get_system_summary()
        self.core_widgets: Dict[int, CoreWidget] = {}
        self.selected_preview_affinity: List[int] = list(range(self.summary.logical_cores))
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

        # 3. CPU Affinity Controls & Preview Bar
        affinity_card = self._create_affinity_card()
        layout.addWidget(affinity_card)

        # 4. Live Logical CPU Utilization Grid
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

        title = QLabel(f"CPU Core Monitor: {self.summary.cpu_model}")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        hybrid_info = "Hybrid Architecture (P/E Cores)" if self.summary.topology.is_hybrid else "Symmetric Multiprocessing (SMP)"
        desc = QLabel(
            f"Inspecting {self.summary.physical_cores} physical cores across {self.summary.logical_cores} logical threads. "
            f"Topology classification: {hybrid_info} | {self.summary.os_kernel}."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        status_theme = "success" if "Verified" in self.summary.detection_status else "info"
        self.badge_status = StatusBadge(self.summary.detection_status, status_theme)
        status_col.addWidget(self.badge_status, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_topology_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_phys = MetricCard(
            title="Physical Cores",
            value=f"{self.summary.physical_cores} Cores",
            subtitle=f"{self.summary.cpu_vendor} hardware units on silicon",
            status_text="Verified",
            status_theme="success",
        )
        grid.addWidget(self.card_phys, 0, 0)

        self.card_log = MetricCard(
            title="Logical CPUs",
            value=f"{self.summary.logical_cores} Threads",
            subtitle=f"{self.summary.available_cpus} available to current process",
            status_text="Optimal",
            status_theme="success",
        )
        grid.addWidget(self.card_log, 0, 1)

        hybrid_desc = "Intel Hybrid (P-Cores + E-Cores)" if self.summary.topology.is_hybrid else "Standard SMP Architecture"
        self.card_hybrid = MetricCard(
            title="Core Architecture",
            value="Hybrid P/E" if self.summary.topology.is_hybrid else "Standard",
            subtitle=hybrid_desc,
            status_text="Verified PMU" if self.summary.topology.is_hybrid else "Standard",
            status_theme="info" if self.summary.topology.is_hybrid else "neutral",
        )
        grid.addWidget(self.card_hybrid, 0, 2)

        max_f_str = f"{int(self.summary.max_freq_mhz)} MHz" if self.summary.max_freq_mhz else "Dynamic"
        self.card_freq = MetricCard(
            title="Clock Ceiling",
            value=max_f_str,
            subtitle="Scaling governor max limit",
            status_text="cpufreq",
            status_theme="neutral",
        )
        grid.addWidget(self.card_freq, 0, 3)

        return grid

    def _create_affinity_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("CPU Affinity Mask Preview")
        title.setProperty("class", "heading-2")
        header_layout.addWidget(title)
        header_layout.addStretch(1)

        # Preset selection buttons (Preview Only)
        self.btn_all = QPushButton("Select All Cores")
        self.btn_all.setProperty("class", "btn-secondary")
        self.btn_all.clicked.connect(self._preset_all_cores)
        header_layout.addWidget(self.btn_all)

        self.btn_pcores = QPushButton("P-Cores Only")
        self.btn_pcores.setProperty("class", "btn-secondary")
        if self.summary.topology.is_hybrid:
            self.btn_pcores.setText(f"P-Cores Only ({len(self.summary.topology.p_cores)})")
            self.btn_pcores.clicked.connect(self._preset_p_cores)
        else:
            self.btn_pcores.setEnabled(False)
            self.btn_pcores.setToolTip("P-Cores only available on reliably detected hybrid CPUs")
        header_layout.addWidget(self.btn_pcores)

        self.btn_ecores = QPushButton("E-Cores Only")
        self.btn_ecores.setProperty("class", "btn-secondary")
        if self.summary.topology.is_hybrid:
            self.btn_ecores.setText(f"E-Cores Only ({len(self.summary.topology.e_cores)})")
            self.btn_ecores.clicked.connect(self._preset_e_cores)
        else:
            self.btn_ecores.setEnabled(False)
            self.btn_ecores.setToolTip("E-Cores only available on reliably detected hybrid CPUs")
        header_layout.addWidget(self.btn_ecores)

        self.btn_reset = QPushButton("Reset Mask")
        self.btn_reset.setProperty("class", "btn-secondary")
        self.btn_reset.clicked.connect(self._preset_all_cores)
        header_layout.addWidget(self.btn_reset)

        layout.addLayout(header_layout)

        # Status text of preview
        self.affinity_preview_lbl = QLabel(f"Active Preview Mask: {self._format_affinity_list(self.selected_preview_affinity)}")
        self.affinity_preview_lbl.setStyleSheet("color: #58a6ff; font-weight: 600; font-size: 12px;")
        layout.addWidget(self.affinity_preview_lbl)

        notice = QLabel(
            "Note: CPU affinity restricts which logical CPUs a worker process is allowed to run on via sched_setaffinity(). "
            "In Phase 4 this provides visualization and topology inspection only; worker affinity assignment is handled in Phase 7."
        )
        notice.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(notice)

        return card

    def _create_cores_panel(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("class", "card-alt")
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        title = QLabel("Real-Time Logical CPU Core Utilization")
        title.setProperty("class", "heading-2")
        header_row.addWidget(title)
        header_row.addStretch(1)

        self.live_badge = StatusBadge("Live Monitoring (QThread)", "success")
        header_row.addWidget(self.live_badge)
        layout.addLayout(header_row)

        grid = QGridLayout()
        grid.setSpacing(10)

        logical_count = self.summary.logical_cores
        cols = 5

        for i in range(logical_count):
            logical_cpu = self.summary.topology.logical_cpus.get(i)
            core_type = logical_cpu.core_type if logical_cpu else CoreType.UNKNOWN
            phys_id = logical_cpu.core_id if logical_cpu else None
            max_f = logical_cpu.max_freq_mhz if logical_cpu else None

            widget = CoreWidget(
                cpu_id=i,
                core_type=core_type,
                physical_core_id=phys_id,
                max_freq_mhz=max_f,
                parent=self,
            )
            self.core_widgets[i] = widget
            grid.addWidget(widget, i // cols, i % cols)

        layout.addLayout(grid)
        return panel

    def _format_affinity_list(self, cpus: List[int]) -> str:
        if len(cpus) == self.summary.logical_cores:
            return f"All Cores (0 - {self.summary.logical_cores - 1}) [{len(cpus)} CPUs]"
        if not cpus:
            return "None (Empty)"
        return f"{cpus} [{len(cpus)} CPUs]"

    def _preset_all_cores(self) -> None:
        self.selected_preview_affinity = list(range(self.summary.logical_cores))
        self.affinity_preview_lbl.setText(f"Active Preview Mask: {self._format_affinity_list(self.selected_preview_affinity)}")
        for w in self.core_widgets.values():
            w.set_affinity_highlight(True)

    def _preset_p_cores(self) -> None:
        if not self.summary.topology.p_cores:
            return
        self.selected_preview_affinity = list(self.summary.topology.p_cores)
        self.affinity_preview_lbl.setText(f"Active Preview Mask: {self._format_affinity_list(self.selected_preview_affinity)} (P-Cores Only)")
        p_set = set(self.selected_preview_affinity)
        for cid, w in self.core_widgets.items():
            w.set_affinity_highlight(cid in p_set)

    def _preset_e_cores(self) -> None:
        if not self.summary.topology.e_cores:
            return
        self.selected_preview_affinity = list(self.summary.topology.e_cores)
        self.affinity_preview_lbl.setText(f"Active Preview Mask: {self._format_affinity_list(self.selected_preview_affinity)} (E-Cores Only)")
        e_set = set(self.selected_preview_affinity)
        for cid, w in self.core_widgets.items():
            w.set_affinity_highlight(cid in e_set)

    @Slot(CPUMetricsSnapshot)
    def update_metrics(self, snapshot: CPUMetricsSnapshot) -> None:
        """Receive live metrics update from CPUMonitorService."""
        per_cpu = snapshot.per_cpu_percent
        freqs = snapshot.per_cpu_freq_mhz

        for i, val in enumerate(per_cpu):
            if i in self.core_widgets:
                f_val = freqs[i] if freqs and i < len(freqs) else None
                self.core_widgets[i].update_metrics(val, f_val)
