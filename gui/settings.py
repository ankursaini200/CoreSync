"""Settings Page for CoreSync Workstation."""

import platform
import sys
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from utils.config import (
    APP_NAME,
    APP_VERSION,
    COOPERATIVE_TIMEOUT,
    SIGTERM_TIMEOUT,
    SIGKILL_TIMEOUT,
    DEFAULT_WORKER_TIMEOUT,
    LOGS_DIR,
)
from gui.components.badge import StatusBadge


class SettingsPage(QWidget):
    """Workstation settings for hardware detection, timeouts, worker configuration, and logging."""

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

        # 2. Process Lifecycle & Timeout Settings Card
        timeout_card = self._create_timeouts_card()
        layout.addWidget(timeout_card)

        # 3. Hardware Probing & Multiprocessing Config Card
        hardware_card = self._create_hardware_card()
        layout.addWidget(hardware_card)

        # 4. Virtual Lab & Simulation Parameters Card
        vlab_card = self._create_vlab_settings_card()
        layout.addWidget(vlab_card)

        # 5. Environment & Logging Info Card
        env_card = self._create_env_card()
        layout.addWidget(env_card)

        layout.addStretch(1)

    def _create_vlab_settings_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Virtual Lab Simulation & Stress Safety Parameters")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Default Tick Delta
        grid.addWidget(QLabel("Default Simulation Step Delta:"), 0, 0)
        self.spin_tick_delta = QSpinBox()
        self.spin_tick_delta.setRange(1, 50)
        self.spin_tick_delta.setValue(1)
        grid.addWidget(self.spin_tick_delta, 0, 1)

        # Simulation Clock Interval
        grid.addWidget(QLabel("Continuous Run Timer (ms):"), 0, 2)
        self.spin_sim_timer = QSpinBox()
        self.spin_sim_timer.setRange(20, 500)
        self.spin_sim_timer.setValue(60)
        grid.addWidget(self.spin_sim_timer, 0, 3)

        # Real Stress Safety Hard Cap
        grid.addWidget(QLabel("Real CPU Stress Hard Cap (s):"), 1, 0)
        self.spin_stress_cap = QSpinBox()
        self.spin_stress_cap.setRange(5, 30)
        self.spin_stress_cap.setValue(30)
        self.spin_stress_cap.setEnabled(False)
        grid.addWidget(self.spin_stress_cap, 1, 1)

        # Duty Cycle Slice
        grid.addWidget(QLabel("Stress Duty-Cycle Window (ms):"), 1, 2)
        self.spin_duty_ms = QSpinBox()
        self.spin_duty_ms.setRange(10, 200)
        self.spin_duty_ms.setValue(50)
        grid.addWidget(self.spin_duty_ms, 1, 3)

        layout.addLayout(grid)
        return card

    def _create_header_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)

        title = QLabel("Workstation Settings & System Configuration")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Configure process lifecycle timeouts, hardware inspection mechanisms, "
            "logging thresholds, and workstation UI preferences."
        )
        desc.setStyleSheet("color: #AAA4AE;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_status = QLabel("Active Settings")
        lbl_status.setStyleSheet("color: #AAA4AE; font-size: 11px;")
        status_col.addWidget(lbl_status, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_timeouts_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Process Lifecycle Escalation & Timeouts")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Stage 1: Cooperative Timeout
        grid.addWidget(QLabel("Stage 1: Cooperative Cancel Wait (s):"), 0, 0)
        self.spin_coop = QDoubleSpinBox()
        self.spin_coop.setRange(0.5, 10.0)
        self.spin_coop.setValue(COOPERATIVE_TIMEOUT)
        self.spin_coop.setSingleStep(0.5)
        grid.addWidget(self.spin_coop, 0, 1)

        # Stage 2: SIGTERM Timeout
        grid.addWidget(QLabel("Stage 2: Process.terminate() Wait (s):"), 0, 2)
        self.spin_term = QDoubleSpinBox()
        self.spin_term.setRange(0.5, 10.0)
        self.spin_term.setValue(SIGTERM_TIMEOUT)
        self.spin_term.setSingleStep(0.5)
        grid.addWidget(self.spin_term, 0, 3)

        # Stage 3: SIGKILL Timeout
        grid.addWidget(QLabel("Stage 3: Process.kill() Grace (s):"), 1, 0)
        self.spin_kill = QDoubleSpinBox()
        self.spin_kill.setRange(0.1, 5.0)
        self.spin_kill.setValue(SIGKILL_TIMEOUT)
        self.spin_kill.setSingleStep(0.1)
        grid.addWidget(self.spin_kill, 1, 1)

        # Global Worker Max Execution Timeout
        grid.addWidget(QLabel("Max Worker Execution Timeout (s):"), 1, 2)
        self.spin_worker_timeout = QDoubleSpinBox()
        self.spin_worker_timeout.setRange(1.0, 120.0)
        self.spin_worker_timeout.setValue(DEFAULT_WORKER_TIMEOUT)
        grid.addWidget(self.spin_worker_timeout, 1, 3)

        layout.addLayout(grid)
        return card

    def _create_hardware_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        title = QLabel("Hardware Probing & Worker Architecture")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Topology Source
        grid.addWidget(QLabel("Topology Detection Method:"), 0, 0)
        self.combo_topo = QComboBox()
        if sys.platform.startswith("win32"):
            topo_items = [
                "Windows Registry / Win32 API - Recommended",
                "psutil Generic Fallback",
            ]
        elif sys.platform.startswith("darwin"):
            topo_items = [
                "macOS sysctl / CoreServices - Recommended",
                "psutil Generic Fallback",
            ]
        else:
            topo_items = [
                "Linux sysfs (/sys/devices/system/cpu) - Recommended",
                "psutil Standard Fallback",
            ]
        self.combo_topo.addItems(topo_items)
        grid.addWidget(self.combo_topo, 0, 1)

        # Start Method
        grid.addWidget(QLabel("Multiprocessing Context:"), 0, 2)
        self.combo_start = QComboBox()
        self.combo_start.addItems(["spawn (Safe, isolated, Qt-compatible)"])
        self.combo_start.setEnabled(False)
        grid.addWidget(self.combo_start, 0, 3)

        # Worker Pool Strategy
        grid.addWidget(QLabel("Worker Pool Strategy:"), 1, 0)
        self.combo_pool = QComboBox()
        self.combo_pool.addItems(["On-Demand Process Spawning (Cold)", "Pre-warmed Worker Pool (Hot)"])
        grid.addWidget(self.combo_pool, 1, 1)

        # Logging Verbosity
        grid.addWidget(QLabel("Logging Level:"), 1, 2)
        self.combo_log = QComboBox()
        self.combo_log.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])
        grid.addWidget(self.combo_log, 1, 3)

        layout.addLayout(grid)
        return card

    def _create_env_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("Runtime Environment & System Diagnostics")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        info_text = (
            f"• Application: {APP_NAME} v{APP_VERSION}\n"
            f"• OS & Kernel: {platform.system()} {platform.release()} ({platform.machine()})\n"
            f"• Python Interpreter: {platform.python_implementation()} {platform.python_version()}\n"
            f"• Logs Directory: {LOGS_DIR}\n"
            f"• Multiprocessing Start Method: spawn (Mandatory for Qt GUI isolation)"
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #AAA4AE; line-height: 1.6; font-family: monospace; font-size: 12px;")
        layout.addWidget(info_label)

        return card

