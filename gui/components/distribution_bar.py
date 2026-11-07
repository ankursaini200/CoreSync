"""Horizontal Distribution Bar Chart for Process and Memory Rankings.

Renders ranked horizontal bars for operating system processes, highlighting CoreSync workers.
"""

from typing import List, Optional
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QToolTip, QWidget

from utils.config import (
    COLOR_ACCENT,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
    COLOR_MEMORY,
    COLOR_SUCCESS,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)
from utils.hardware.base import ProcessInfo


class ProcessDistributionWidget(QWidget):
    """Visualizes top CPU or Memory processes as horizontal ranked bars."""

    def __init__(
        self,
        title: str = "TOP PROCESSES BY CPU LOAD",
        mode: str = "cpu",  # "cpu" or "memory"
        bar_color: str = COLOR_ACCENT,
        max_rows: int = 5,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self.mode = mode
        self.bar_color = QColor(bar_color)
        self.max_rows = max_rows
        self.processes: List[ProcessInfo] = []
        self.coresync_pids: set[int] = set()

        self.setMinimumHeight(150)
        self.setMouseTracking(True)

    def set_data(self, processes: List[ProcessInfo], coresync_pids: Optional[List[int]] = None) -> None:
        """Update ranked process list."""
        self.coresync_pids = set(coresync_pids or [])
        if self.mode == "cpu":
            sorted_procs = sorted(processes, key=lambda p: p.cpu_percent, reverse=True)
        else:
            sorted_procs = sorted(processes, key=lambda p: p.memory_rss_mb, reverse=True)
        self.processes = sorted_procs[:self.max_rows]
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(350, 40 + self.max_rows * 26)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Title
        painter.setFont(QFont("Inter", 9, QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        painter.drawText(QRectF(10, 8, w - 20, 18), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        if not self.processes:
            painter.setFont(QFont("Inter", 8))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(10, 35, w - 20, 30), Qt.AlignLeft, "Sampling active system processes...")
            return

        max_val = max((p.cpu_percent if self.mode == "cpu" else p.memory_rss_mb) for p in self.processes)
        max_val = max(1.0, max_val)

        row_h = 24.0
        start_y = 32.0

        for idx, proc in enumerate(self.processes):
            y = start_y + idx * row_h
            is_coresync = proc.pid in self.coresync_pids

            # Process Name & PID
            name_str = f"{proc.name[:14]} ({proc.pid})"
            painter.setFont(QFont("Inter", 8, QFont.Bold if is_coresync else QFont.Normal))
            painter.setPen(QColor(COLOR_SUCCESS if is_coresync else COLOR_TEXT_PRIMARY))
            painter.drawText(QRectF(10, y, 120, 18), Qt.AlignLeft | Qt.AlignVCenter, name_str)

            # Bar Area
            bar_start_x = 135.0
            val_text_w = 60.0
            avail_bar_w = max(40.0, w - bar_start_x - val_text_w - 10.0)

            cur_val = proc.cpu_percent if self.mode == "cpu" else proc.memory_rss_mb
            bar_fill_w = max(4.0, (cur_val / max_val) * avail_bar_w)

            # Track
            bar_y = y + 5.0
            bar_rect_track = QRectF(bar_start_x, bar_y, avail_bar_w, 8.0)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(COLOR_BG_CARD_ALT))
            painter.drawRoundedRect(bar_rect_track, 4.0, 4.0)

            # Fill
            c_fill = QColor(COLOR_SUCCESS if is_coresync else self.bar_color)
            bar_rect_fill = QRectF(bar_start_x, bar_y, bar_fill_w, 8.0)
            painter.setBrush(c_fill)
            painter.drawRoundedRect(bar_rect_fill, 4.0, 4.0)

            # Value text
            val_str = f"{cur_val:.1f}%" if self.mode == "cpu" else f"{cur_val:.0f} MB"
            painter.setFont(QFont("Inter", 8))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(w - val_text_w - 8, y, val_text_w, 18), Qt.AlignRight | Qt.AlignVCenter, val_str)

