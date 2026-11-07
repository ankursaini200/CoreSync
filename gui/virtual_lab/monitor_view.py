"""Virtual Core Monitor and Multi-Core Grid View for CoreSync Virtual Lab."""

from typing import Dict, Optional
from PySide6.QtCore import Qt
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

from engine.virtual_lab.virtual_core import VirtualCore, VirtualCoreState, VirtualCoreType
from engine.virtual_lab.virtual_cpu import VirtualCPU
from gui.components.arc_gauge import ArcGaugeWidget
from gui.components.badge import StatusBadge
from gui.components.core_heatmap import get_heatmap_colors
from gui.components.metric_card import MetricCard
from utils.config import COLOR_ACCENT, COLOR_BORDER, COLOR_TASK, COLOR_TEXT_MUTED, COLOR_TEXT_PRIMARY


class VirtualCoreCard(QFrame):
    """Visual card displaying the real-time simulation state of a single virtual core."""

    def __init__(self, core: VirtualCore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.core = core
        self.setProperty("class", "card-alt")
        self.setMinimumWidth(180)
        self.setMinimumHeight(115)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header: Core ID and Type Pill
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.label_id = QLabel(f"Virtual Core #{self.core.core_id}")
        self.label_id.setStyleSheet("font-weight: 700; font-size: 12px; color: #e6edf3;")
        header_layout.addWidget(self.label_id)
        header_layout.addStretch(1)

        type_text = "STD"
        theme = "neutral"
        if self.core.core_type == VirtualCoreType.PERFORMANCE:
            type_text = f"P-Core ({self.core.speed_multiplier}x)"
            theme = "warning"
        elif self.core.core_type == VirtualCoreType.EFFICIENCY:
            type_text = f"E-Core ({self.core.speed_multiplier}x)"
            theme = "info"
        else:
            type_text = f"Std ({self.core.speed_multiplier}x)"
            theme = "neutral"

        self.type_badge = StatusBadge(type_text, theme)
        header_layout.addWidget(self.type_badge)
        layout.addLayout(header_layout)

        # State & Task
        self.label_task = QLabel("Task: None (IDLE)")
        self.label_task.setStyleSheet("font-size: 11px; color: #8b949e;")
        layout.addWidget(self.label_task)

        # Simulated Utilization Bar
        bar_layout = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        bar_layout.addWidget(self.bar)

        self.label_pct = QLabel("0.0%")
        self.label_pct.setStyleSheet("font-size: 11px; font-weight: 600; color: #58a6ff;")
        self.label_pct.setFixedWidth(45)
        self.label_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bar_layout.addWidget(self.label_pct)
        layout.addLayout(bar_layout)

    def update_state(self) -> None:
        """Refresh card visuals from internal VirtualCore state with dynamic heatmap styling."""
        util = self.core.simulated_utilization
        self.bar.setValue(int(util))
        self.label_pct.setText(f"{util:.1f}%")

        bg_col, border_col, accent_col = get_heatmap_colors(util)
        self.label_pct.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {accent_col.name()};")
        self.setStyleSheet(
            f"QFrame {{"
            f"  background-color: {bg_col.name()};"
            f"  border: 1px solid {border_col.name()};"
            f"  border-radius: 8px;"
            f"}}"
        )

        if self.core.state == VirtualCoreState.BUSY and self.core.current_task:
            task = self.core.current_task
            self.label_task.setText(f"Task: {task.name} ({task.remaining_ticks:.0f} ticks left)")
            self.label_task.setStyleSheet(f"font-size: 11px; color: {accent_col.name()}; font-weight: 600;")
        else:
            self.label_task.setText("Task: None (IDLE)")
            self.label_task.setStyleSheet("font-size: 11px; color: #8FA0B8;")


class VirtualMonitorPage(QWidget):
    """Real-time matrix visualization of simulated virtual multicore execution."""

    def __init__(self, virtual_cpu: VirtualCPU, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.virtual_cpu = virtual_cpu
        self.core_cards: Dict[int, VirtualCoreCard] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll)

        container = QWidget()
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(28, 24, 28, 28)
        self.layout.setSpacing(20)
        scroll.setWidget(container)

        # 1. Header Card
        header_card = self._create_header_card()
        self.layout.addWidget(header_card)

        # 2. Metric Cards Grid
        metrics_grid = self._create_metrics_grid()
        self.layout.addLayout(metrics_grid)

        # 3. Virtual Core Matrix Card
        self.matrix_card = self._create_matrix_card()
        self.layout.addWidget(self.matrix_card)

        self.layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Virtual Multicore Core Matrix Monitor")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Visual observation grid for individual virtual cores, simulated cycle throughput, "
            "and dynamic task assignments."
        )
        desc.setStyleSheet("color: #9AA5B4;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.badge_status = QLabel("Virtual Core Matrix")
        self.badge_status.setStyleSheet("color: #9AA5B4; font-size: 11px;")
        status_col.addWidget(self.badge_status, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_metrics_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        # Arc Gauge for Simulated Virtual Load
        card_gauge = QFrame()
        card_gauge.setProperty("class", "card")
        l_g = QHBoxLayout(card_gauge)
        l_g.setContentsMargins(14, 10, 14, 10)
        self.gauge_sim_load = ArcGaugeWidget(
            title="SIMULATED LOAD",
            value=0.0,
            max_value=100.0,
            unit="%",
            subtitle="DISCRETE TICKS",
            color_start=COLOR_TASK,
            color_end="#FDE68A",
            parent=card_gauge,
        )
        l_g.addWidget(self.gauge_sim_load)
        layout.addWidget(card_gauge)

        self.card_util = MetricCard(
            title="Simulated Aggregate Load",
            value="0.0%",
            subtitle="Windowed simulated duty cycle",
            status_text="Simulated",
            status_theme="info",
            show_progress=True,
            progress_val=0,
        )
        layout.addWidget(self.card_util)

        self.card_clock = MetricCard(
            title="Simulation Clock",
            value=f"{self.virtual_cpu.current_tick} Ticks",
            subtitle="Virtual time delta steps",
            status_text="Clock Active",
            status_theme="neutral",
        )
        layout.addWidget(self.card_clock)

        self.card_busy = MetricCard(
            title="Core Occupancy",
            value=f"0 / {len(self.virtual_cpu.cores)} Active",
            subtitle="Cores executing virtual tasks",
            status_text="Idle",
            status_theme="neutral",
        )
        layout.addWidget(self.card_busy)

        return layout

    def _create_matrix_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        self.matrix_layout = QVBoxLayout(card)
        self.matrix_layout.setContentsMargins(20, 18, 20, 18)
        self.matrix_layout.setSpacing(14)

        # Header with controls
        header_row = QHBoxLayout()
        title = QLabel(f"Virtual Execution Units ({len(self.virtual_cpu.cores)} Cores)")
        title.setProperty("class", "heading-2")
        self.matrix_title = title
        header_row.addWidget(title)
        header_row.addStretch(1)

        btn_step1 = QPushButton("Step +1 Tick")
        btn_step1.setProperty("class", "btn-secondary")
        btn_step1.clicked.connect(lambda: self._on_step(1))
        header_row.addWidget(btn_step1)

        btn_step10 = QPushButton("Step +10 Ticks")
        btn_step10.setProperty("class", "btn-secondary")
        btn_step10.clicked.connect(lambda: self._on_step(10))
        header_row.addWidget(btn_step10)

        self.matrix_layout.addLayout(header_row)

        # Grid of core cards
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self._rebuild_core_grid()

        self.matrix_layout.addWidget(self.grid_container)
        return card

    def _rebuild_core_grid(self) -> None:
        """Clear and rebuild the grid cards when virtual core topology changes."""
        # Remove existing widgets
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.core_cards.clear()

        # Place cores in 4 columns
        cols = 4 if len(self.virtual_cpu.cores) <= 16 else 6
        for idx, (core_id, core) in enumerate(self.virtual_cpu.cores.items()):
            row = idx // cols
            col = idx % cols
            card = VirtualCoreCard(core, self.grid_container)
            self.core_cards[core_id] = card
            self.grid_layout.addWidget(card, row, col)

        if hasattr(self, "matrix_title"):
            self.matrix_title.setText(f"Virtual Execution Units ({len(self.virtual_cpu.cores)} Cores)")

    def rebuild_for_new_config(self) -> None:
        """Public slot called after virtual CPU reconfiguration."""
        self._rebuild_core_grid()
        self.refresh_display()

    def _on_step(self, delta: int) -> None:
        self.virtual_cpu.step(delta)
        self.refresh_display()

    def refresh_display(self) -> None:
        """Update metrics and individual virtual core cards."""
        busy_count = len([c for c in self.virtual_cpu.cores.values() if c.state == VirtualCoreState.BUSY])
        total_cores = len(self.virtual_cpu.cores)
        overall_util = self.virtual_cpu.overall_simulated_utilization

        self.card_util.set_value(f"{overall_util:.1f}%")
        if self.card_util.progress_bar:
            self.card_util.progress_bar.setValue(int(overall_util))

        self.card_clock.set_value(f"{self.virtual_cpu.current_tick} Ticks")
        self.card_busy.set_value(f"{busy_count} / {total_cores} Active")
        self.card_busy.set_status("Executing" if busy_count > 0 else "Idle", "danger" if busy_count > 0 else "neutral")

        if hasattr(self, "gauge_sim_load"):
            self.gauge_sim_load.set_value(overall_util, subtitle=f"{busy_count}/{total_cores} CORES BUSY")

        for card in self.core_cards.values():
            card.update_state()

