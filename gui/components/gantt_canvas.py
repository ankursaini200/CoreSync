"""Interactive CPU Scheduling Execution Timeline & Gantt Chart Canvas.

Provides QPainter-based visualization of process bursts, CPU idle gaps, context switches,
preemption markers, and timestamp rulers with horizontal scrolling and zoom controls.
"""

from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QPoint, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from engine.process_scheduler.timeline import BlockType, SchedulingTimeline, TimelineBlock


# High-contrast workstation process colors matching black gradient palette (No Blue)
PROCESS_PALETTE = [
    QColor("#19C99A"),  # Teal
    QColor("#A879F5"),  # Violet
    QColor("#42D6A0"),  # Emerald
    QColor("#E4AD69"),  # Amber
    QColor("#D17BE8"),  # Magenta
    QColor("#7956C8"),  # Purple
    QColor("#EF737D"),  # Coral Red
    QColor("#F1BC70"),  # Warm Gold
    QColor("#2DD4BF"),  # Light Teal
    QColor("#C084FC"),  # Soft Violet
]

IDLE_BG = QColor("#111113")
IDLE_BORDER = QColor("#302B32")
IDLE_TEXT = QColor("#77717C")

CS_BG = QColor("#1F1911")
CS_BORDER = QColor("#E4AD69")
CS_TEXT = QColor("#E4AD69")


class GanttPaintWidget(QWidget):
    """Internal canvas widget handling direct QPainter rendering."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._timeline: Optional[SchedulingTimeline] = None
        self._zoom: float = 1.0
        self._base_px_per_unit: float = 60.0
        self._pid_color_map: Dict[str, QColor] = {}
        self._rendered_blocks: List[Tuple[QRectF, TimelineBlock]] = []

        self.setMouseTracking(True)
        self.setMinimumHeight(140)

    @property
    def px_per_unit(self) -> float:
        return max(15.0, self._base_px_per_unit * self._zoom)

    def set_timeline(self, timeline: Optional[SchedulingTimeline]) -> None:
        """Bind a new execution timeline and recalculate dimensions."""
        self._timeline = timeline
        self._assign_colors()
        self._update_geometry()
        self.update()

    def set_zoom(self, zoom: float) -> None:
        """Update horizontal zoom multiplier."""
        self._zoom = max(0.4, min(4.0, zoom))
        self._update_geometry()
        self.update()

    def _assign_colors(self) -> None:
        """Assign deterministic colors to distinct process IDs."""
        self._pid_color_map.clear()
        if not self._timeline:
            return
        idx = 0
        for b in self._timeline.blocks:
            if b.block_type == BlockType.PROCESS and b.process_id and b.process_id not in self._pid_color_map:
                self._pid_color_map[b.process_id] = PROCESS_PALETTE[idx % len(PROCESS_PALETTE)]
                idx += 1

    def _update_geometry(self) -> None:
        """Update required width based on timeline duration and zoom."""
        if not self._timeline or not self._timeline.blocks:
            self.setMinimumWidth(600)
            return

        total_time = self._timeline.total_simulation_time
        needed_width = int(total_time * self.px_per_unit) + 120  # margins
        self.setMinimumWidth(max(600, needed_width))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        painter.fillRect(self.rect(), QColor("#08090B"))

        if not self._timeline or not self._timeline.blocks:
            painter.setPen(QColor("#77717C"))
            font = QFont("Inter", 11)
            painter.setFont(font)
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "No simulation timeline available. Configure processes and click 'Run Simulation'.",
            )
            return

        self._rendered_blocks.clear()

        margin_left = 30.0
        track_y = 25.0
        track_h = 55.0
        ruler_y = track_y + track_h + 10.0

        font_bold = QFont("Inter", 10, QFont.Bold)
        font_small = QFont("Inter", 8)
        font_ruler = QFont("Inter", 8)

        # 1. Draw Gantt Blocks
        for b in self._timeline.blocks:
            bx = margin_left + (b.start_time * self.px_per_unit)
            bw = max(4.0, b.duration * self.px_per_unit)
            rect = QRectF(bx, track_y, bw, track_h)
            self._rendered_blocks.append((rect, b))

            if b.block_type == BlockType.PROCESS:
                color = self._pid_color_map.get(b.process_id, QColor("#19C99A"))
                # Fill
                painter.setBrush(QBrush(color.darker(160)))
                pen_color = QColor("#E4AD69") if b.preempted else color
                pen_style = Qt.DashLine if b.preempted else Qt.SolidLine
                painter.setPen(QPen(pen_color, 2, pen_style))
                painter.drawRoundedRect(rect, 4, 4)

                # Process ID Label
                painter.setFont(font_bold)
                painter.setPen(Qt.white)
                text_rect = QRectF(rect.x(), rect.y() + 6, rect.width(), 20)
                painter.drawText(text_rect, Qt.AlignCenter, str(b.process_id))

                # Duration label if block wide enough
                if bw >= 36:
                    painter.setFont(font_small)
                    painter.setPen(QColor("#AAA4AE"))
                    sub_rect = QRectF(rect.x(), rect.y() + 28, rect.width(), 16)
                    painter.drawText(sub_rect, Qt.AlignCenter, f"{b.duration:g}")

                # Preemption marker badge
                if b.preempted and bw >= 24:
                    painter.setFont(font_small)
                    painter.setPen(QColor("#E4AD69"))
                    p_badge = QRectF(rect.right() - 18, rect.top() + 3, 14, 12)
                    painter.drawText(p_badge, Qt.AlignCenter, "⚡")

            elif b.block_type == BlockType.IDLE:
                painter.setBrush(QBrush(IDLE_BG, Qt.DiagCrossPattern))
                painter.setPen(QPen(IDLE_BORDER, 1))
                painter.drawRoundedRect(rect, 4, 4)

                painter.setFont(font_bold)
                painter.setPen(IDLE_TEXT)
                painter.drawText(rect, Qt.AlignCenter, "IDLE" if bw >= 36 else "—")

            elif b.block_type == BlockType.CONTEXT_SWITCH:
                painter.setBrush(QBrush(CS_BG, Qt.Dense4Pattern))
                painter.setPen(QPen(CS_BORDER, 1, Qt.DashLine))
                painter.drawRoundedRect(rect, 3, 3)

                if bw >= 24:
                    painter.setFont(font_small)
                    painter.setPen(CS_TEXT)
                    painter.drawText(rect, Qt.AlignCenter, "CS")

        # 2. Draw Bottom Time Ruler
        total_time = self._timeline.total_simulation_time
        max_x = margin_left + (total_time * self.px_per_unit)

        # Baseline
        painter.setPen(QPen(QColor("#302B32"), 1))
        painter.drawLine(int(margin_left), int(ruler_y), int(max_x), int(ruler_y))

        # Determine tick step (1, 2, 5, 10, etc.)
        tick_step = 1.0
        if self.px_per_unit < 25:
            tick_step = 5.0
        elif self.px_per_unit < 40:
            tick_step = 2.0

        painter.setFont(font_ruler)
        t = 0.0
        while t <= total_time + 1e-9:
            tx = margin_left + (t * self.px_per_unit)
            painter.setPen(QPen(QColor("#302B32"), 1))
            painter.drawLine(int(tx), int(ruler_y), int(tx), int(ruler_y + 5))

            painter.setPen(QColor("#77717C"))
            lbl_rect = QRectF(tx - 25, ruler_y + 8, 50, 16)
            painter.drawText(lbl_rect, Qt.AlignCenter, f"{t:g}")
            t += tick_step

        # Final timestamp mark if not on tick
        if abs((t - tick_step) - total_time) > 1e-4:
            tx_final = margin_left + (total_time * self.px_per_unit)
            painter.setPen(QPen(QColor("#19C99A"), 1))
            painter.drawLine(int(tx_final), int(ruler_y), int(tx_final), int(ruler_y + 7))
            lbl_rect = QRectF(tx_final - 25, ruler_y + 8, 50, 16)
            painter.setPen(QColor("#19C99A"))
            painter.drawText(lbl_rect, Qt.AlignCenter, f"{total_time:g}")

    def mouseMoveEvent(self, event) -> None:
        """Show rich tooltip on hovering over execution blocks."""
        pos = event.position()
        for rect, block in self._rendered_blocks:
            if rect.contains(pos):
                if block.block_type == BlockType.PROCESS:
                    preempt_str = "Yes (Context Saved)" if block.preempted else "No (Burst Completed)"
                    tip = (
                        f"<b>Process: {block.process_id}</b><br>"
                        f"Execution Slice: [{block.start_time:g} → {block.end_time:g}]<br>"
                        f"Duration: {block.duration:g} ms<br>"
                        f"Preempted: {preempt_str}"
                    )
                    if block.priority_at_execution is not None:
                        tip += f"<br>Priority: {block.priority_at_execution}"
                elif block.block_type == BlockType.IDLE:
                    tip = (
                        f"<b>CPU IDLE Interval</b><br>"
                        f"Time: [{block.start_time:g} → {block.end_time:g}]<br>"
                        f"Duration: {block.duration:g} ms<br>"
                        f"Status: No processes in ready queue"
                    )
                else:
                    tip = (
                        f"<b>Context Switch Overhead</b><br>"
                        f"Time: [{block.start_time:g} → {block.end_time:g}]<br>"
                        f"Duration: {block.duration:g} ms<br>"
                        f"Transition: {block.context_from_pid or '—'} → {block.context_to_pid or '—'}"
                    )
                QToolTip.showText(event.globalPosition().toPoint(), tip, self)
                return
        QToolTip.hideText()


class GanttCanvasWidget(QWidget):
    """Container widget providing the scrollable Gantt canvas with zoom controls."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_zoom: float = 1.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Top Controls Bar
        ctrl_bar = QHBoxLayout()
        ctrl_bar.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Execution Timeline & Gantt Chart")
        title.setProperty("class", "heading-2")
        ctrl_bar.addWidget(title)

        ctrl_bar.addStretch(1)

        # Legend badges
        lbl_legend_proc = QLabel("■ Process")
        lbl_legend_proc.setStyleSheet("color: #19C99A; font-size: 11px; margin-right: 8px;")
        ctrl_bar.addWidget(lbl_legend_proc)

        lbl_legend_idle = QLabel("■ Idle")
        lbl_legend_idle.setStyleSheet("color: #77717C; font-size: 11px; margin-right: 8px;")
        ctrl_bar.addWidget(lbl_legend_idle)

        lbl_legend_cs = QLabel("■ Context Switch")
        lbl_legend_cs.setStyleSheet("color: #E4AD69; font-size: 11px; margin-right: 14px;")
        ctrl_bar.addWidget(lbl_legend_cs)

        # Zoom buttons
        self.btn_zoom_out = QPushButton("− Zoom")
        self.btn_zoom_out.setFixedSize(65, 26)
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        ctrl_bar.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("color: #8b949e; font-size: 11px; min-width: 36px; text-align: center;")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        ctrl_bar.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("+ Zoom")
        self.btn_zoom_in.setFixedSize(65, 26)
        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        ctrl_bar.addWidget(self.btn_zoom_in)

        layout.addLayout(ctrl_bar)

        # 2. Scrollable Canvas
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(145)
        self.scroll.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 6px;")

        self.canvas = GanttPaintWidget(self.scroll)
        self.scroll.setWidget(self.canvas)
        layout.addWidget(self.scroll)

    def set_timeline(self, timeline: Optional[SchedulingTimeline]) -> None:
        """Bind timeline to canvas."""
        self.canvas.set_timeline(timeline)

    def _on_zoom_in(self) -> None:
        self._current_zoom = min(4.0, self._current_zoom * 1.25)
        self._apply_zoom()

    def _on_zoom_out(self) -> None:
        self._current_zoom = max(0.4, self._current_zoom / 1.25)
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        self.canvas.set_zoom(self._current_zoom)
        self.lbl_zoom.setText(f"{int(self._current_zoom * 100)}%")

