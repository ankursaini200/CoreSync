"""Reusable Action & Navigation Card component for CoreSync."""

from typing import Callable, Optional
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.config import (
    COLOR_BORDER,
    COLOR_SURFACE_ELEVATED,
    COLOR_SURFACE_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)
from gui.components.badge import StatusBadge


class ActionCardIconWidget(QWidget):
    """Rich vector icon badge rendered inside ActionCards."""

    def __init__(self, icon_type: str, accent_color: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.accent_color = QColor(accent_color)
        self.setFixedSize(36, 36)

    def sizeHint(self) -> QSize:
        return QSize(36, 36)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(1.0, 1.0, 34.0, 34.0)

        # Background with subtle ambient gradient
        grad = QLinearGradient(1.0, 1.0, 34.0, 34.0)
        grad.setColorAt(0.0, QColor(COLOR_SURFACE_ELEVATED))
        grad.setColorAt(1.0, QColor(COLOR_SURFACE_SECONDARY))
        p.setBrush(QBrush(grad))

        # Accent border
        border_col = QColor(self.accent_color)
        border_col.setAlpha(120)
        p.setPen(QPen(border_col, 1.2))
        p.drawRoundedRect(rect, 8.0, 8.0)

        # Draw icon
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(self.accent_color, 1.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        ix, iy = 9.0, 9.0  # 18x18 icon area inside 36x36
        t = self.icon_type

        if t == "core_monitor":
            p.drawRoundedRect(QRectF(ix + 2.0, iy + 2.0, 14.0, 14.0), 2.0, 2.0)
            p.drawLine(QPointF(ix + 9.0, iy + 4.0), QPointF(ix + 9.0, iy + 14.0))
            p.drawLine(QPointF(ix + 4.0, iy + 9.0), QPointF(ix + 14.0, iy + 9.0))
            for offset in (4.0, 9.0, 14.0):
                p.drawLine(QPointF(ix + offset, iy), QPointF(ix + offset, iy + 2.0))
                p.drawLine(QPointF(ix + offset, iy + 16.0), QPointF(ix + offset, iy + 18.0))
                p.drawLine(QPointF(ix, iy + offset), QPointF(ix + 2.0, iy + offset))
                p.drawLine(QPointF(ix + 16.0, iy + offset), QPointF(ix + 18.0, iy + offset))

        elif t == "process_monitor":
            for idx, y_off in enumerate((4.0, 9.0, 14.0)):
                p.drawEllipse(QRectF(ix + 1.0, iy + y_off - 1.5, 3.0, 3.0))
                bw = 12.0 if idx == 0 else (9.0 if idx == 1 else 11.0)
                p.drawLine(QPointF(ix + 6.0, iy + y_off), QPointF(ix + 6.0 + bw, iy + y_off))

        elif t == "real_stress":
            bolt = QPainterPath()
            bolt.moveTo(ix + 10.0, iy + 1.0)
            bolt.lineTo(ix + 4.0, iy + 9.5)
            bolt.lineTo(ix + 9.0, iy + 9.5)
            bolt.lineTo(ix + 7.5, iy + 17.0)
            bolt.lineTo(ix + 14.0, iy + 7.5)
            bolt.lineTo(ix + 9.5, iy + 7.5)
            bolt.closeSubpath()
            p.drawPath(bolt)

        elif t == "virtual_config":
            for x_off, handle_y in ((4.0, 6.0), (9.0, 12.0), (14.0, 8.0)):
                p.drawLine(QPointF(ix + x_off, iy + 2.0), QPointF(ix + x_off, iy + 16.0))
                p.drawEllipse(QRectF(ix + x_off - 2.0, iy + handle_y, 4.0, 4.0))

        elif t == "virtual_monitor":
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 1.5, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 10.5, iy + 1.5, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 10.5, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 10.5, iy + 10.5, 6.0, 6.0), 1.5, 1.5)

        elif t == "virtual_scheduler":
            p.drawArc(QRectF(ix + 2.0, iy + 2.0, 14.0, 14.0), 45 * 16, 270 * 16)
            p.drawLine(QPointF(ix + 13.0, iy + 2.0), QPointF(ix + 16.0, iy + 5.0))
            p.drawLine(QPointF(ix + 13.0, iy + 8.0), QPointF(ix + 16.0, iy + 5.0))
            p.drawLine(QPointF(ix + 9.0, iy + 5.0), QPointF(ix + 9.0, iy + 9.0))
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 12.0, iy + 9.0))
        else:
            p.drawRoundedRect(QRectF(ix + 2.0, iy + 2.0, 14.0, 14.0), 2.0, 2.0)


class ActionCard(QFrame):
    """Clickable workstation card for launching modules or viewing details."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        button_text: str = "Open →",
        badge_text: Optional[str] = None,
        badge_theme: str = "neutral",
        on_click: Optional[Callable[[], None]] = None,
        icon_type: Optional[str] = None,
        accent_color: str = "#19C99A",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumHeight(138)
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # Header Row: [Icon] + Title + [Badge]
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        if icon_type:
            self.icon_widget = ActionCardIconWidget(icon_type, accent_color, self)
            header_layout.addWidget(self.icon_widget)

        self.title_label = QLabel(title, self)
        self.title_label.setProperty("class", "heading-2")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        if badge_text:
            self.badge = StatusBadge(badge_text, badge_theme, self)
            header_layout.addWidget(self.badge)

        layout.addLayout(header_layout)

        # Description
        self.desc_label = QLabel(description, self)
        self.desc_label.setProperty("class", "muted")
        self.desc_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; line-height: 1.4;")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        layout.addStretch(1)

        # Footer Button
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)

        self.btn = QPushButton(button_text, self)
        self.btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_SURFACE_ELEVATED};
                border: 1px solid {self.accent_color};
                border-radius: 5px;
                padding: 6px 14px;
                color: {self.accent_color};
                font-weight: 600;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #232025;
                color: #FFFFFF;
            }}
        """)
        if on_click:
            self.btn.clicked.connect(on_click)
        self.btn.clicked.connect(self.clicked.emit)
        footer_layout.addWidget(self.btn)

        layout.addLayout(footer_layout)
