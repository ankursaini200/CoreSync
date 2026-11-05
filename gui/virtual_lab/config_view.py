"""Virtual CPU Topology and Architecture Configuration View for CoreSync Virtual Lab."""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from engine.virtual_lab.virtual_cpu import VirtualCPU, VirtualCPUConfig
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class VirtualConfigPage(QWidget):
    """Configuration interface for customizing simulated virtual multicore processors."""

    configuration_applied = Signal(VirtualCPUConfig)

    def __init__(self, virtual_cpu: VirtualCPU, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.virtual_cpu = virtual_cpu
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

        # 2. Active Virtual CPU Summary Cards
        summary_grid = self._create_summary_grid()
        layout.addLayout(summary_grid)

        # 3. Main Configuration Card
        config_card = self._create_config_card()
        layout.addWidget(config_card)

        # 4. Educational Architecture Notes Card
        notes_card = self._create_notes_card()
        layout.addWidget(notes_card)

        layout.addStretch(1)

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Virtual Multicore Processor Architect")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Configure software-simulated multicore CPUs with arbitrary core topologies, "
            "asymmetric P-core/E-core performance ratios, and custom clock multipliers."
        )
        desc.setStyleSheet("color: #8b949e;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.header_badge = StatusBadge("Virtual Lab (Configurable)", "info")
        status_col.addWidget(self.header_badge, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_summary_grid(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(14)

        self.card_name = MetricCard(
            title="Virtual Model",
            value=self.virtual_cpu.config.name,
            subtitle="Custom simulated architecture",
            status_text="Virtual",
            status_theme="info",
        )
        layout.addWidget(self.card_name)

        self.card_cores = MetricCard(
            title="Virtual Cores",
            value=f"{len(self.virtual_cpu.cores)} Cores",
            subtitle=f"{self.virtual_cpu.config.physical_cores} Physical / {self.virtual_cpu.config.logical_threads} Threads",
            status_text="Active",
            status_theme="success",
        )
        layout.addWidget(self.card_cores)

        self.card_arch = MetricCard(
            title="Core Hierarchy",
            value="Homogeneous SMP" if not self.virtual_cpu.config.enable_hybrid else "Heterogeneous Hybrid",
            subtitle="Uniform execution units" if not self.virtual_cpu.config.enable_hybrid else f"{self.virtual_cpu.config.p_core_count}P + {self.virtual_cpu.config.e_core_count}E",
            status_text="Simulated",
            status_theme="neutral",
        )
        layout.addWidget(self.card_arch)

        return layout

    def _create_config_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        title = QLabel("Virtual Processor Parameters")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(3, 2)

        # Preset selector
        lbl_preset = QLabel("Hardware Preset:")
        lbl_preset.setProperty("class", "metric-label")
        self.combo_presets = QComboBox()
        self.combo_presets.addItems([
            "Custom Configuration",
            "Workstation 8-Core (8 Cores, 16 Threads)",
            "High-End Desktop 16-Core (16 Cores, 32 Threads)",
            "Server High-Density 64-Core (32 Cores, 64 Threads)",
            "Hybrid Desktop (4 P-Cores @ 1.5x, 8 E-Cores @ 0.8x)",
            "Flagship Hybrid (8 P-Cores @ 1.6x, 16 E-Cores @ 0.8x)",
        ])
        self.combo_presets.currentIndexChanged.connect(self._on_preset_changed)
        grid.addWidget(lbl_preset, 0, 0)
        grid.addWidget(self.combo_presets, 0, 1, 1, 3)

        # Name
        lbl_name = QLabel("Processor Name:")
        lbl_name.setProperty("class", "metric-label")
        self.input_name = QLineEdit(self.virtual_cpu.config.name)
        grid.addWidget(lbl_name, 1, 0)
        grid.addWidget(self.input_name, 1, 1)

        # Physical Cores
        lbl_phys = QLabel("Physical Cores:")
        lbl_phys.setProperty("class", "metric-label")
        self.spin_phys = QSpinBox()
        self.spin_phys.setRange(1, 64)
        self.spin_phys.setValue(self.virtual_cpu.config.physical_cores)
        grid.addWidget(lbl_phys, 1, 2)
        grid.addWidget(self.spin_phys, 1, 3)

        # Logical Threads (Total Virtual Execution Units)
        lbl_threads = QLabel("Logical Threads (1-128):")
        lbl_threads.setProperty("class", "metric-label")
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 128)
        self.spin_threads.setValue(self.virtual_cpu.config.logical_threads)
        grid.addWidget(lbl_threads, 2, 0)
        grid.addWidget(self.spin_threads, 2, 1)

        # Standard speed
        lbl_std_speed = QLabel("Standard Speed Multiplier:")
        lbl_std_speed.setProperty("class", "metric-label")
        self.spin_std_speed = QDoubleSpinBox()
        self.spin_std_speed.setRange(0.2, 3.0)
        self.spin_std_speed.setSingleStep(0.1)
        self.spin_std_speed.setValue(self.virtual_cpu.config.standard_speed)
        grid.addWidget(lbl_std_speed, 2, 2)
        grid.addWidget(self.spin_std_speed, 2, 3)

        # Hybrid Checkbox
        self.check_hybrid = QCheckBox("Enable Hybrid Heterogeneous Core Architecture (P-cores / E-cores)")
        self.check_hybrid.setChecked(self.virtual_cpu.config.enable_hybrid)
        self.check_hybrid.toggled.connect(self._toggle_hybrid_controls)
        grid.addWidget(self.check_hybrid, 3, 0, 1, 4)

        # Hybrid controls row
        lbl_p_count = QLabel("P-Core Count:")
        lbl_p_count.setProperty("class", "metric-label")
        self.spin_p_count = QSpinBox()
        self.spin_p_count.setRange(1, 64)
        self.spin_p_count.setValue(self.virtual_cpu.config.p_core_count)
        grid.addWidget(lbl_p_count, 4, 0)
        grid.addWidget(self.spin_p_count, 4, 1)

        lbl_p_speed = QLabel("P-Core Speed:")
        lbl_p_speed.setProperty("class", "metric-label")
        self.spin_p_speed = QDoubleSpinBox()
        self.spin_p_speed.setRange(1.0, 3.0)
        self.spin_p_speed.setSingleStep(0.1)
        self.spin_p_speed.setValue(self.virtual_cpu.config.p_core_speed)
        grid.addWidget(lbl_p_speed, 4, 2)
        grid.addWidget(self.spin_p_speed, 4, 3)

        lbl_e_count = QLabel("E-Core Count:")
        lbl_e_count.setProperty("class", "metric-label")
        self.spin_e_count = QSpinBox()
        self.spin_e_count.setRange(1, 64)
        self.spin_e_count.setValue(self.virtual_cpu.config.e_core_count)
        grid.addWidget(lbl_e_count, 5, 0)
        grid.addWidget(self.spin_e_count, 5, 1)

        lbl_e_speed = QLabel("E-Core Speed:")
        lbl_e_speed.setProperty("class", "metric-label")
        self.spin_e_speed = QDoubleSpinBox()
        self.spin_e_speed.setRange(0.2, 1.5)
        self.spin_e_speed.setSingleStep(0.1)
        self.spin_e_speed.setValue(self.virtual_cpu.config.e_core_speed)
        grid.addWidget(lbl_e_speed, 5, 2)
        grid.addWidget(self.spin_e_speed, 5, 3)

        layout.addLayout(grid)

        # Action Button Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_apply = QPushButton("Apply Configuration to Virtual Lab")
        self.btn_apply.setProperty("class", "btn-primary")
        self.btn_apply.clicked.connect(self._apply_configuration)
        btn_layout.addWidget(self.btn_apply)

        btn_layout.addStretch(1)
        layout.addLayout(btn_layout)

        self._toggle_hybrid_controls(self.check_hybrid.isChecked())
        return card

    def _create_notes_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("Architectural Principles of the Virtual Lab")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        notes = QLabel(
            "• Pure Software Simulation: Virtual CPUs run entirely within an in-memory simulation clock. "
            "They do not invoke OS thread pools or modify your actual hardware affinity.\n"
            "• Heterogeneous Modeling: Performance cores (P-cores) progress tasks with a speed multiplier >1.0x, "
            "while Efficiency cores (E-cores) conserve simulated cycles with multipliers <1.0x.\n"
            "• Educational Topology Exploration: Test theoretical 32, 64, or 128-core architectures regardless "
            "of the physical limitations of your host machine."
        )
        notes.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        layout.addWidget(notes)

        return card

    def _toggle_hybrid_controls(self, enabled: bool) -> None:
        self.spin_p_count.setEnabled(enabled)
        self.spin_p_speed.setEnabled(enabled)
        self.spin_e_count.setEnabled(enabled)
        self.spin_e_speed.setEnabled(enabled)

    def _on_preset_changed(self, index: int) -> None:
        if index == 1:  # Workstation 8-Core
            self.input_name.setText("Virtual Workstation-8")
            self.spin_phys.setValue(8)
            self.spin_threads.setValue(16)
            self.check_hybrid.setChecked(False)
            self.spin_std_speed.setValue(1.0)
        elif index == 2:  # High-End Desktop 16-Core
            self.input_name.setText("Virtual ThreadRipper-16")
            self.spin_phys.setValue(16)
            self.spin_threads.setValue(32)
            self.check_hybrid.setChecked(False)
            self.spin_std_speed.setValue(1.0)
        elif index == 3:  # Server 64-Core
            self.input_name.setText("Virtual EpycCluster-64")
            self.spin_phys.setValue(32)
            self.spin_threads.setValue(64)
            self.check_hybrid.setChecked(False)
            self.spin_std_speed.setValue(1.0)
        elif index == 4:  # Hybrid Desktop (4P+8E)
            self.input_name.setText("Virtual AlderLake-12")
            self.spin_phys.setValue(8)
            self.spin_threads.setValue(12)
            self.check_hybrid.setChecked(True)
            self.spin_p_count.setValue(4)
            self.spin_p_speed.setValue(1.5)
            self.spin_e_count.setValue(8)
            self.spin_e_speed.setValue(0.8)
        elif index == 5:  # Flagship Hybrid (8P+16E)
            self.input_name.setText("Virtual RaptorLake-24")
            self.spin_phys.setValue(16)
            self.spin_threads.setValue(24)
            self.check_hybrid.setChecked(True)
            self.spin_p_count.setValue(8)
            self.spin_p_speed.setValue(1.6)
            self.spin_e_count.setValue(16)
            self.spin_e_speed.setValue(0.8)

    def _apply_configuration(self) -> None:
        config = VirtualCPUConfig(
            name=self.input_name.text().strip() or "Custom Virtual CPU",
            physical_cores=self.spin_phys.value(),
            logical_threads=self.spin_threads.value(),
            enable_hybrid=self.check_hybrid.isChecked(),
            p_core_count=self.spin_p_count.value(),
            p_core_speed=self.spin_p_speed.value(),
            e_core_count=self.spin_e_count.value(),
            e_core_speed=self.spin_e_speed.value(),
            standard_speed=self.spin_std_speed.value(),
        )

        self.virtual_cpu.reconfigure(config)
        self.configuration_applied.emit(config)

        # Update summary metrics
        self.card_name.set_value(config.name)
        self.card_cores.set_value(f"{len(self.virtual_cpu.cores)} Cores")
        self.card_cores.set_subtitle(f"{config.physical_cores} Physical / {config.logical_threads} Threads")
        self.card_arch.set_value("Homogeneous SMP" if not config.enable_hybrid else "Heterogeneous Hybrid")
        self.card_arch.set_subtitle(
            "Uniform execution units" if not config.enable_hybrid else f"{config.p_core_count}P + {config.e_core_count}E"
        )
        self.header_badge.set_status("Config Applied", "success")

