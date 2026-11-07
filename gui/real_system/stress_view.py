"""Real System CPU Stress Generator View for CoreSync."""

from typing import Optional
from PySide6.QtCore import QTimer, Qt, Slot
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import psutil
from engine.real_system.cpu_stress import (
    DEFAULT_STRESS_DURATION_S,
    MAX_STRESS_DURATION_S,
    RealCPUStressGenerator,
)
from gui.components.badge import StatusBadge
from gui.components.metric_card import MetricCard


class RealStressPage(QWidget):
    """Workstation control interface for running genuine, safety-bounded CPU stress workloads."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stress_gen = RealCPUStressGenerator()
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(250)
        self._update_timer.timeout.connect(self._poll_stress_status)
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

        # 2. Controls Card
        controls_card = self._create_controls_card()
        layout.addWidget(controls_card)

        # 3. Live Stress Status Metrics
        metrics_grid = self._create_metrics_grid()
        layout.addLayout(metrics_grid)

        # 4. Safety & Architecture Notes
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

        title = QLabel("Real CPU Stress & Multicore Workload Generator")
        title.setProperty("class", "heading-1")
        left_col.addWidget(title)

        desc = QLabel(
            "Spawn actual CPU-bound worker processes to observe true multicore load and thermal scaling. "
            "Includes conservative safety caps, duty-cycle throttling, and instantaneous process termination."
        )
        desc.setStyleSheet("color: #AAA4AE;")
        left_col.addWidget(desc)
        layout.addLayout(left_col)
        layout.addStretch(1)

        status_col = QVBoxLayout()
        status_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.status_badge = StatusBadge("Generator Idle", "neutral")
        status_col.addWidget(self.status_badge, alignment=Qt.AlignRight)
        layout.addLayout(status_col)

        return card

    def _create_controls_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setSpacing(16)

        title = QLabel("Stress Parameters & Execution Control")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(14)

        # Worker count
        logical_count = psutil.cpu_count(logical=True) or 4
        grid.addWidget(QLabel("Stress Worker Count:"), 0, 0)
        self.spin_workers = QSpinBox()
        self.spin_workers.setRange(1, logical_count)
        self.spin_workers.setValue(min(4, logical_count))
        grid.addWidget(self.spin_workers, 0, 1)

        # Duration
        grid.addWidget(QLabel(f"Duration (Max {int(MAX_STRESS_DURATION_S)}s):"), 0, 2)
        self.spin_duration = QDoubleSpinBox()
        self.spin_duration.setRange(1.0, MAX_STRESS_DURATION_S)
        self.spin_duration.setValue(DEFAULT_STRESS_DURATION_S)
        self.spin_duration.setSuffix(" s")
        grid.addWidget(self.spin_duration, 0, 3)

        # Intensity Slider (10% to 100%)
        grid.addWidget(QLabel("Workload Intensity:"), 1, 0)
        self.slider_intensity = QSlider(Qt.Horizontal)
        self.slider_intensity.setRange(10, 100)
        self.slider_intensity.setValue(100)
        self.slider_intensity.valueChanged.connect(lambda v: self.lbl_intensity.setText(f"{v}%"))
        grid.addWidget(self.slider_intensity, 1, 1)

        self.lbl_intensity = QLabel("100%")
        self.lbl_intensity.setStyleSheet("font-weight: 600; color: #19C99A;")
        grid.addWidget(self.lbl_intensity, 1, 2)

        layout.addLayout(grid)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.btn_start = QPushButton("Start Real CPU Stress")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.clicked.connect(self._on_start_clicked)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Stress Immediately")
        self.btn_stop.setProperty("class", "btn-danger")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)
        btn_layout.addWidget(self.btn_stop)

        layout.addLayout(btn_layout)
        return card

    def _create_metrics_grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_active = MetricCard(
            title="Active Stress Workers",
            value="0 Running",
            subtitle="Genuine child processes computing math",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_active, 0, 0)

        self.card_elapsed = MetricCard(
            title="Elapsed Time",
            value="0.0 s",
            subtitle="Time since stress initiation",
            status_text="Ready",
            status_theme="neutral",
            show_progress=True,
            progress_val=0,
        )
        grid.addWidget(self.card_elapsed, 0, 1)

        self.card_pids = MetricCard(
            title="Child Process IDs",
            value="None",
            subtitle="OS-assigned process identifiers",
            status_text="Idle",
            status_theme="neutral",
        )
        grid.addWidget(self.card_pids, 0, 2)

        return grid

    def _create_notes_card(self) -> QFrame:
        card = QFrame()
        card.setProperty("class", "card-alt")
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        title = QLabel("Safety Protocols & Workload Transparency")
        title.setProperty("class", "heading-2")
        layout.addWidget(title)

        notes = QLabel(
            "• Explicit Initiation Only: Real CPU stress is never triggered automatically. It strictly runs when you click Start.\n"
            f"• Safety Duration Cap: Hard-limited to a maximum of {int(MAX_STRESS_DURATION_S)} seconds to prevent system instability.\n"
            "• Duty-Cycle Throttling: Lower intensities insert sleep windows into the worker loops, allowing proportional load generation.\n"
            "• Immediate Termination: Clicking 'Stop Stress Immediately' or closing CoreSync executes SIGTERM and SIGKILL escalations, "
            "guaranteeing zero orphan processes remain."
        )
        notes.setStyleSheet("color: #8b949e; line-height: 1.5; font-size: 12px;")
        layout.addWidget(notes)

        return card

    def _on_start_clicked(self) -> None:
        workers = self.spin_workers.value()
        duration = self.spin_duration.value()
        intensity = float(self.slider_intensity.value())

        started = self.stress_gen.start_stress(
            worker_count=workers,
            duration_s=duration,
            intensity_pct=intensity,
        )
        if started:
            self.btn_start.setEnabled(False)
            self.btn_stop.setEnabled(True)
            self.status_badge.set_status("STRESS ACTIVE", "danger")
            self._update_timer.start()

    def _on_stop_clicked(self) -> None:
        self.stress_gen.stop_stress()
        self._update_timer.stop()
        self._update_ui_stopped()

    def _poll_stress_status(self) -> None:
        status = self.stress_gen.get_status()
        if not status.is_running:
            self._update_timer.stop()
            self._update_ui_stopped()
            return

        self.card_active.set_value(f"{status.workers_active} Workers")
        self.card_active.set_status("Active", "danger")
        self.card_elapsed.set_value(f"{status.elapsed_s:.1f} / {status.target_duration_s:.1f} s")

        progress = int((status.elapsed_s / status.target_duration_s) * 100) if status.target_duration_s > 0 else 0
        if self.card_elapsed.progress_bar:
            self.card_elapsed.progress_bar.setValue(progress)

        pid_str = ", ".join(str(p) for p in status.worker_pids[:4])
        if len(status.worker_pids) > 4:
            pid_str += f" +{len(status.worker_pids) - 4} more"
        self.card_pids.set_value(pid_str or "None")

    def _update_ui_stopped(self) -> None:
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_badge.set_status("Generator Idle", "neutral")
        self.card_active.set_value("0 Running")
        self.card_active.set_status("Idle", "neutral")
        self.card_elapsed.set_value("0.0 s")
        if self.card_elapsed.progress_bar:
            self.card_elapsed.progress_bar.setValue(0)
        self.card_pids.set_value("None")

    def shutdown(self) -> None:
        """Clean up workers upon window close."""
        self._update_timer.stop()
        self.stress_gen.stop_stress()

