"""Real-Time Area and Line Chart Component with Gradient Fill and Smooth Splines.

Inspired by modern telemetry dashboards, providing anti-aliased Bézier curves,
multi-series plotting, interactive crosshairs, and live data buffering.
"""

from collections import deque
from typing import Deque, List, Optional, Tuple
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
    COLOR_MEMORY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


class RealtimeAreaChartWidget(QWidget):
    """High-performance real-time area chart with smooth gradients and interactive crosshairs."""

    def __init__(
        self,
        max_points: int = 60,
        title: str = "REAL-TIME CPU & MEMORY TELEMETRY",
        series1_name: str = "CPU Load",
        series1_color: str = COLOR_ACCENT,
        series2_name: Optional[str] = "RAM Usage",
        series2_color: Optional[str] = COLOR_MEMORY,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.max_points = max_points
        self.title = title
        self.series1_name = series1_name
        self.series1_color = QColor(series1_color)
        self.series2_name = series2_name
        self.series2_color = QColor(series2_color) if series2_color else None

        self.s1_data: Deque[float] = deque(maxlen=max_points)
        self.s2_data: Deque[float] = deque(maxlen=max_points)

        # Pre-fill with zeroes for smooth initial window
        for _ in range(max_points):
            self.s1_data.append(0.0)
            if self.series2_name:
                self.s2_data.append(0.0)

        self._hover_x: Optional[float] = None
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self.setStyleSheet(f"background-color: #0D0D10; border: 1px solid {COLOR_BORDER}; border-radius: 8px;")

    def add_sample(self, val1: float, val2: Optional[float] = None) -> None:
        """Push new sample to ring buffer and trigger repaint."""
        self.s1_data.append(max(0.0, min(100.0, float(val1))))
        if self.series2_name:
            v2 = max(0.0, min(100.0, float(val2))) if val2 is not None else 0.0
            self.s2_data.append(v2)
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(400, 200)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Margins for axes and title
        ml, mr, mt, mb = 45.0, 16.0, 32.0, 24.0
        plot_w = max(50.0, w - ml - mr)
        plot_h = max(50.0, h - mt - mb)

        # 1. Header Row (Title & Legend)
        painter.setFont(QFont("Inter", 9, QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        painter.drawText(QRectF(ml, 8, plot_w * 0.6, 20), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # Legend
        leg_x = w - mr
        if self.series2_name and self.series2_color:
            leg_x -= 100
            painter.setFont(QFont("Inter", 8))
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.series2_color)
            painter.drawEllipse(QPointF(leg_x, 18), 4, 4)
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(leg_x + 8, 8, 90, 20), Qt.AlignLeft | Qt.AlignVCenter, self.series2_name)

        leg_x -= 100
        painter.setFont(QFont("Inter", 8))
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.series1_color)
        painter.drawEllipse(QPointF(leg_x, 18), 4, 4)
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.drawText(QRectF(leg_x + 8, 8, 90, 20), Qt.AlignLeft | Qt.AlignVCenter, self.series1_name)

        # 2. Grid Lines & Y-Ticks (0%, 25%, 50%, 75%, 100%)
        painter.setFont(QFont("Inter", 8))
        for step in [0, 25, 50, 75, 100]:
            y_pos = mt + plot_h - (step / 100.0) * plot_h
            painter.setPen(QPen(QColor(COLOR_BORDER), 1, Qt.DashLine if step > 0 else Qt.SolidLine))
            painter.drawLine(int(ml), int(y_pos), int(ml + plot_w), int(y_pos))

            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(0, y_pos - 7, ml - 8, 14), Qt.AlignRight | Qt.AlignVCenter, f"{step}%")

        # 3. Draw Series 2 (RAM) if active
        if self.series2_name and self.series2_color and len(self.s2_data) >= 2:
            self._draw_series(painter, list(self.s2_data), self.series2_color, ml, mt, plot_w, plot_h, fill_alpha=40)

        # 4. Draw Series 1 (CPU)
        if len(self.s1_data) >= 2:
            self._draw_series(painter, list(self.s1_data), self.series1_color, ml, mt, plot_w, plot_h, fill_alpha=65)

        # 5. Interactive Crosshair on Hover
        if self._hover_x is not None and ml <= self._hover_x <= ml + plot_w:
            # Draw vertical guide line
            painter.setPen(QPen(self.series1_color, 1, Qt.DashDotLine))
            painter.drawLine(int(self._hover_x), int(mt), int(self._hover_x), int(mt + plot_h))

            # Find closest sample index
            rel_x = (self._hover_x - ml) / plot_w
            idx = int(round(rel_x * (len(self.s1_data) - 1)))
            idx = max(0, min(len(self.s1_data) - 1, idx))

            # Dot on series 1
            v1 = self.s1_data[idx]
            y1 = mt + plot_h - (v1 / 100.0) * plot_h
            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.setBrush(self.series1_color)
            painter.drawEllipse(QPointF(self._hover_x, y1), 5, 5)

        # 6. X-Axis Time Markers
        painter.setFont(QFont("Inter", 8))
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        painter.drawText(QRectF(ml, mt + plot_h + 4, 60, 16), Qt.AlignLeft, f"-{self.max_points}s")
        painter.drawText(QRectF(ml + plot_w / 2.0 - 30, mt + plot_h + 4, 60, 16), Qt.AlignCenter, f"-{self.max_points // 2}s")
        painter.drawText(QRectF(ml + plot_w - 60, mt + plot_h + 4, 60, 16), Qt.AlignRight, "Live")

    def _draw_series(
        self,
        painter: QPainter,
        data: List[float],
        color: QColor,
        ml: float,
        mt: float,
        plot_w: float,
        plot_h: float,
        fill_alpha: int = 50,
    ) -> None:
        n = len(data)
        if n < 2:
            return

        points: List[QPointF] = []
        for i, val in enumerate(data):
            x = ml + (i / (n - 1)) * plot_w
            y = mt + plot_h - (val / 100.0) * plot_h
            points.append(QPointF(x, y))

        # Build smooth cubic Bezier path
        line_path = QPainterPath()
        line_path.moveTo(points[0])

        for i in range(len(points) - 1):
            p0 = points[max(0, i - 1)]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[min(len(points) - 1, i + 2)]

            # Catmull-Rom to Cubic Bezier conversion
            c1 = QPointF(p1.x() + (p2.x() - p0.x()) / 6.0, p1.y() + (p2.y() - p0.y()) / 6.0)
            c2 = QPointF(p2.x() - (p3.x() - p1.x()) / 6.0, p2.y() - (p3.y() - p1.y()) / 6.0)
            line_path.cubicTo(c1, c2, p2)

        # Create gradient filled area
        area_path = QPainterPath(line_path)
        area_path.lineTo(ml + plot_w, mt + plot_h)
        area_path.lineTo(ml, mt + plot_h)
        area_path.closeSubpath()

        grad = QLinearGradient(0, mt, 0, mt + plot_h)
        c_top = QColor(color)
        c_top.setAlpha(fill_alpha)
        c_bot = QColor(color)
        c_bot.setAlpha(2)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(area_path)

        # Draw anti-aliased smooth curve line
        pen = QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(line_path)

        # Highlight newest point
        last_pt = points[-1]
        painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
        painter.setBrush(color)
        painter.drawEllipse(last_pt, 4.0, 4.0)

    def mouseMoveEvent(self, event) -> None:
        self._hover_x = event.position().x()
        w = self.width()
        ml, mr = 45.0, 16.0
        plot_w = max(50.0, w - ml - mr)

        if ml <= self._hover_x <= ml + plot_w and len(self.s1_data) > 0:
            rel_x = (self._hover_x - ml) / plot_w
            idx = int(round(rel_x * (len(self.s1_data) - 1)))
            idx = max(0, min(len(self.s1_data) - 1, idx))
            time_offset = (len(self.s1_data) - 1 - idx)

            v1 = self.s1_data[idx]
            tip = f"<b>{self.series1_name}</b>: {v1:.1f}%<br/>Time: -{time_offset}s ago"
            if self.series2_name and idx < len(self.s2_data):
                v2 = self.s2_data[idx]
                tip = f"<b>{self.series1_name}</b>: {v1:.1f}%<br/><b>{self.series2_name}</b>: {v2:.1f}%<br/>Time: -{time_offset}s ago"
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            self._hover_x = None

        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_x = None
        self.update()
        super().leaveEvent(event)

