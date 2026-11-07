"""Circular Arc Gauge Widget for Rich Hardware Telemetry Visualization.

Provides a smooth, antialiased circular radial meter drawn with QPainter,
featuring customizable gradient sweeps, glowing indicator points, and central readouts.
"""

import math
from typing import Optional
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
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


class ArcGaugeWidget(QWidget):
    """Circular arc gauge with gradient fill, glowing tip, and central value readout."""

    def __init__(
        self,
        title: str = "UTILIZATION",
        value: float = 0.0,
        max_value: float = 100.0,
        unit: str = "%",
        subtitle: str = "",
        color_start: str = COLOR_ACCENT,
        color_end: str = COLOR_ACCENT_SECONDARY,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title = title
        self._value = max(0.0, min(max_value, float(value)))
        self._max_value = max(1.0, float(max_value))
        self.unit = unit
        self.subtitle = subtitle
        self.color_start = QColor(color_start)
        self.color_end = QColor(color_end)
        self.track_color = QColor("#1C283E")
        self.border_color = QColor(COLOR_BORDER)

        self.setMinimumSize(140, 140)
        self.setMouseTracking(True)

    def set_value(self, value: float, subtitle: Optional[str] = None) -> None:
        """Update gauge value and trigger smooth repaint."""
        self._value = max(0.0, min(self._max_value, float(value)))
        if subtitle is not None:
            self.subtitle = subtitle
        self.update()

    def set_colors(self, start_color: str, end_color: str) -> None:
        """Dynamically update gauge accent gradient colors."""
        self.color_start = QColor(start_color)
        self.color_end = QColor(end_color)
        self.update()

    @property
    def value(self) -> float:
        return self._value

    def sizeHint(self) -> QSize:
        return QSize(160, 160)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        size = min(w, h)
        center = QPointF(w / 2.0, h / 2.0)

        # Margins and radius
        margin = 12.0
        radius = (size / 2.0) - margin
        thickness = max(8.0, size * 0.085)

        # Arc geometry: 240 degrees sweep from 150 to 390 (or 210 to -30)
        # In Qt drawArc: 0 is 3 o'clock, counterclockwise in 1/16th degrees
        # Start at 210° (bottom-left) and sweep -240° (clockwise to bottom-right)
        start_angle_deg = 210.0
        span_total_deg = -240.0

        ratio = self._value / self._max_value
        span_value_deg = span_total_deg * ratio

        arc_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)

        # 1. Background Track Arc
        track_pen = QPen(self.track_color, thickness, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(track_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(arc_rect, int(start_angle_deg * 16), int(span_total_deg * 16))

        # 2. Outer Subtle Guide Circle
        guide_pen = QPen(self.border_color, 1.0, Qt.DotLine)
        painter.setPen(guide_pen)
        outer_radius = radius + thickness / 2.0 + 3.0
        painter.drawEllipse(center, outer_radius, outer_radius)

        # 3. Active Value Arc with Gradient
        if ratio > 0.001:
            grad = QLinearGradient(arc_rect.topLeft(), arc_rect.bottomRight())
            grad.setColorAt(0.0, self.color_start)
            grad.setColorAt(1.0, self.color_end)

            active_pen = QPen(QBrush(grad), thickness, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(active_pen)
            painter.drawArc(arc_rect, int(start_angle_deg * 16), int(span_value_deg * 16))

            # 4. Glowing Tip Indicator Dot
            # Calculate tip coordinate in radians
            tip_angle_deg = start_angle_deg + span_value_deg
            tip_rad = math.radians(tip_angle_deg)
            # In standard cartesian (Qt y is down, so y = center.y - radius * sin(tip_rad))
            tip_x = center.x() + radius * math.cos(tip_rad)
            tip_y = center.y() - radius * math.sin(tip_rad)

            # Outer glow
            glow_color = QColor(self.color_end)
            glow_color.setAlpha(90)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawEllipse(QPointF(tip_x, tip_y), thickness * 0.9, thickness * 0.9)

            # Core white dot
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(QPointF(tip_x, tip_y), thickness * 0.35, thickness * 0.35)

        # 5. Center Typography
        # Title (Above)
        painter.setFont(QFont("Inter", max(8, int(size * 0.055)), QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        title_rect = QRectF(w * 0.15, center.y() - radius * 0.55, w * 0.7, size * 0.18)
        painter.drawText(title_rect, Qt.AlignCenter, self.title.upper())

        # Main Value (Center)
        painter.setFont(QFont("Inter", max(16, int(size * 0.16)), QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        val_str = f"{self._value:.1f}{self.unit}" if self.unit == "%" else f"{self._value:.0f} {self.unit}"
        val_rect = QRectF(w * 0.1, center.y() - size * 0.12, w * 0.8, size * 0.28)
        painter.drawText(val_rect, Qt.AlignCenter, val_str)

        # Subtitle (Below)
        if self.subtitle:
            painter.setFont(QFont("Inter", max(8, int(size * 0.055)), QFont.Normal))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            sub_rect = QRectF(w * 0.1, center.y() + size * 0.16, w * 0.8, size * 0.2)
            painter.drawText(sub_rect, Qt.AlignCenter, self.subtitle)

    def mouseMoveEvent(self, event) -> None:
        val_str = f"{self._value:.1f}{self.unit}"
        pct = (self._value / self._max_value) * 100.0
        tip_text = f"<b>{self.title}</b><br/>Value: <b>{val_str}</b> ({pct:.1f}%)"
        if self.subtitle:
            tip_text += f"<br/><span style='color:#8FA0B8;'>{self.subtitle}</span>"
        QToolTip.showText(event.globalPosition().toPoint(), tip_text, self)
        super().mouseMoveEvent(event)

