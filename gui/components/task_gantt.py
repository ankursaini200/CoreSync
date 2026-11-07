"""Gantt Execution Timeline Component for Task Parallelism and Schedulers.

Visualizes task execution duration, worker assignments, and scheduling timelines.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QToolTip, QWidget

from utils.config import (
    COLOR_ACCENT,
    COLOR_ACCENT_SECONDARY,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
    COLOR_DANGER,
    COLOR_SUCCESS,
    COLOR_TASK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


@dataclass
class GanttTaskItem:
    task_id: str
    name: str
    worker_id: int
    start_ms: float
    duration_ms: float
    status: str = "completed"  # "completed", "running", "failed"
    color_hex: Optional[str] = None


class TaskExecutionGanttWidget(QWidget):
    """High-DPI vector Gantt chart rendering parallel worker execution tracks."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.items: List[GanttTaskItem] = []
        self.worker_count: int = 4
        self.total_time_ms: float = 100.0
        self._hover_item: Optional[GanttTaskItem] = None

        self.setMinimumHeight(180)
        self.setMouseTracking(True)

    def set_tasks(self, items: List[GanttTaskItem], worker_count: int = 4, total_time_ms: Optional[float] = None) -> None:
        """Load task items and recompute visual bounds."""
        self.items = list(items)
        self.worker_count = max(1, worker_count)
        if total_time_ms is not None and total_time_ms > 0:
            self.total_time_ms = total_time_ms
        elif self.items:
            self.total_time_ms = max(10.0, max(t.start_ms + t.duration_ms for t in self.items) * 1.05)
        else:
            self.total_time_ms = 100.0
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(650, max(180, 50 + self.worker_count * 36))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        ml, mr, mt, mb = 80.0, 24.0, 30.0, 30.0
        plot_w = max(50.0, w - ml - mr)
        plot_h = max(50.0, h - mt - mb)

        # Title
        painter.setFont(QFont("Inter", 9, QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        painter.drawText(QRectF(ml, 6, plot_w, 20), Qt.AlignLeft | Qt.AlignVCenter, "WORKER EXECUTION TIMELINE (GANTT)")

        track_h = max(24.0, plot_h / self.worker_count)

        # 1. Background Worker Tracks
        for wid in range(self.worker_count):
            ty = mt + wid * track_h
            t_rect = QRectF(ml, ty, plot_w, track_h - 4.0)

            painter.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor("#101726") if wid % 2 == 0 else QColor(COLOR_BG_CARD_ALT)))
            painter.drawRoundedRect(t_rect, 4.0, 4.0)

            # Worker Track Label
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(0, ty, ml - 8, track_h - 4.0), Qt.AlignRight | Qt.AlignVCenter, f"Worker {wid}")

        # 2. Time Grid Lines on X-Axis
        steps = 5
        for s in range(steps + 1):
            t_val = (self.total_time_ms / steps) * s
            gx = ml + (s / steps) * plot_w

            painter.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.DotLine))
            painter.drawLine(int(gx), int(mt), int(gx), int(mt + plot_h))

            # Label
            painter.setFont(QFont("Inter", 8))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(gx - 30, mt + plot_h + 4, 60, 18), Qt.AlignCenter, f"{t_val:.1f}ms")

        # 3. Task Bars
        if not self.items:
            painter.setFont(QFont("Inter", 8))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(ml + 20, mt + plot_h / 2.0 - 10, plot_w - 40, 20), Qt.AlignCenter, "Awaiting DAG benchmark execution...")
            return

        for item in self.items:
            wid = min(self.worker_count - 1, max(0, item.worker_id))
            ty = mt + wid * track_h + 3.0
            bh = track_h - 10.0

            bx = ml + (item.start_ms / self.total_time_ms) * plot_w
            bw = max(12.0, (item.duration_ms / self.total_time_ms) * plot_w)

            bar_rect = QRectF(bx, ty, bw, bh)

            # Color assignment
            if item.color_hex:
                c_fill = QColor(item.color_hex)
            elif item.status == "completed":
                c_fill = QColor(COLOR_SUCCESS)
            elif item.status == "running":
                c_fill = QColor(COLOR_ACCENT)
            else:
                c_fill = QColor(COLOR_DANGER)

            # Highlight if hovered
            is_hover = (item == self._hover_item)
            painter.setPen(QPen(QColor("#FFFFFF") if is_hover else c_fill.darker(120), 1.5 if is_hover else 1.0))
            painter.setBrush(QBrush(c_fill))
            painter.drawRoundedRect(bar_rect, 4.0, 4.0)

            # Task Label Inside Bar
            if bw >= 30.0:
                painter.setFont(QFont("Inter", 7, QFont.Bold))
                painter.setPen(QColor("#0B1020"))
                label_text = f"{item.name[:8]} ({item.duration_ms:.1f}ms)"
                painter.drawText(QRectF(bx + 4, ty, bw - 8, bh), Qt.AlignCenter, label_text)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        w = self.width()
        ml, mr, mt, mb = 80.0, 24.0, 30.0, 30.0
        plot_w = max(50.0, w - ml - mr)
        plot_h = max(50.0, self.height() - mt - mb)
        track_h = max(24.0, plot_h / self.worker_count)

        found_item = None
        for item in self.items:
            wid = min(self.worker_count - 1, max(0, item.worker_id))
            ty = mt + wid * track_h + 3.0
            bh = track_h - 10.0
            bx = ml + (item.start_ms / self.total_time_ms) * plot_w
            bw = max(12.0, (item.duration_ms / self.total_time_ms) * plot_w)
            if QRectF(bx, ty, bw, bh).contains(pos):
                found_item = item
                break

        if found_item != self._hover_item:
            self._hover_item = found_item
            self.update()

        if self._hover_item:
            it = self._hover_item
            tip = (
                f"<b>Task: {it.name}</b> (ID: {it.task_id})<br/>"
                f"Worker: <b>Worker {it.worker_id}</b><br/>"
                f"Start: <b>{it.start_ms:.1f} ms</b><br/>"
                f"Duration: <b>{it.duration_ms:.1f} ms</b><br/>"
                f"Status: <b>{it.status.upper()}</b>"
            )
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_item = None
        self.update()
        super().leaveEvent(event)

