"""Premium Dark Sidebar and Gradient-Based Navigation Components for CoreSync.

Implements resolution-independent vector line icons, layered dark surfaces,
indigo-to-cyan active gradients, and CPU branding.
"""

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
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.config import (
    APP_NAME,
    APP_VERSION,
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_SURFACE_ELEVATED,
    COLOR_SURFACE_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    GRADIENT_PRIMARY_END,
    GRADIENT_PRIMARY_START,
)


class SidebarBrandWidget(QWidget):
    """Header branding featuring a CPU microchip badge and CoreSync gradient typography."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(68)
        self.setAttribute(Qt.WA_Hover, True)

    def sizeHint(self) -> QSize:
        return QSize(260, 68)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # 1. CPU Icon Badge Container
        badge_x, badge_y, badge_s = 16.0, 14.0, 38.0
        badge_rect = QRectF(badge_x, badge_y, badge_s, badge_s)

        # Gradient background
        bg_grad = QLinearGradient(badge_x, badge_y, badge_x + badge_s, badge_y + badge_s)
        bg_grad.setColorAt(0.0, QColor("#18253A"))
        bg_grad.setColorAt(1.0, QColor("#0F1726"))
        p.setBrush(QBrush(bg_grad))
        p.setPen(QPen(QColor(COLOR_BORDER), 1.2))
        p.drawRoundedRect(badge_rect, 9.0, 9.0)

        # Subtle top-left highlight border
        p.setPen(QPen(QColor(54, 201, 232, 60), 1.0))
        p.drawArc(QRectF(badge_x + 1, badge_y + 1, 16, 16), 90 * 16, 90 * 16)

        # 2. CPU Connector Pins (3 pins per side)
        pin_col = QColor(GRADIENT_PRIMARY_END)
        p.setPen(QPen(pin_col, 1.2, Qt.SolidLine, Qt.RoundCap))
        # Top & Bottom pins
        for px in (badge_x + 12.0, badge_x + 19.0, badge_x + 26.0):
            p.drawLine(QPointF(px, badge_y - 2.5), QPointF(px, badge_y + 0.5))
            p.drawLine(QPointF(px, badge_y + badge_s - 0.5), QPointF(px, badge_y + badge_s + 2.5))
        # Left & Right pins
        for py in (badge_y + 12.0, badge_y + 19.0, badge_y + 26.0):
            p.drawLine(QPointF(badge_x - 2.5, py), QPointF(badge_x + 0.5, py))
            p.drawLine(QPointF(badge_x + badge_s - 0.5, py), QPointF(badge_x + badge_s + 2.5, py))

        # 3. Inner Silicon Die with Primary Gradient
        die_margin = 8.5
        die_rect = QRectF(badge_x + die_margin, badge_y + die_margin, badge_s - (die_margin * 2), badge_s - (die_margin * 2))
        die_grad = QLinearGradient(die_rect.topLeft(), die_rect.bottomRight())
        die_grad.setColorAt(0.0, QColor(GRADIENT_PRIMARY_START))
        die_grad.setColorAt(1.0, QColor(GRADIENT_PRIMARY_END))
        p.setBrush(QBrush(die_grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(die_rect, 4.0, 4.0)

        # 4. Multicore 2x2 Grid inside die
        p.setBrush(QBrush(QColor("#0B1020")))
        p.setPen(Qt.NoPen)
        cw, ch = 3.5, 3.5
        dx, dy = die_rect.x(), die_rect.y()
        p.drawRoundedRect(QRectF(dx + 3.0, dy + 3.0, cw, ch), 1.0, 1.0)
        p.drawRoundedRect(QRectF(dx + 8.5, dy + 3.0, cw, ch), 1.0, 1.0)
        p.drawRoundedRect(QRectF(dx + 3.0, dy + 8.5, cw, ch), 1.0, 1.0)
        p.drawRoundedRect(QRectF(dx + 8.5, dy + 8.5, cw, ch), 1.0, 1.0)

        # 5. CoreSync Typography
        tx = badge_x + badge_s + 12.0
        ty = badge_y + 15.0

        p.setFont(QFont("Inter", 13, QFont.Bold))
        # "Core" in crisp white
        p.setPen(QColor(COLOR_TEXT_PRIMARY))
        p.drawText(QPointF(tx, ty), "Core")
        core_w = p.fontMetrics().horizontalAdvance("Core")

        # "Sync" in vibrant Cyan gradient color
        p.setPen(QColor(GRADIENT_PRIMARY_END))
        p.drawText(QPointF(tx + core_w, ty), "Sync")

        # 6. Subtitle Description
        p.setFont(QFont("Inter", 9, QFont.Medium))
        p.setPen(QColor(COLOR_TEXT_MUTED))
        p.drawText(QPointF(tx, ty + 15.0), "Multicore Workstation")

        # 7. Bottom Hairline Divider with Subtle Fade
        div_y = h - 1.0
        div_grad = QLinearGradient(16.0, div_y, w - 16.0, div_y)
        div_grad.setColorAt(0.0, QColor(71, 118, 230, 80))
        div_grad.setColorAt(0.4, QColor(54, 201, 232, 50))
        div_grad.setColorAt(0.8, QColor(39, 55, 80, 40))
        div_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(QBrush(div_grad), 1.0))
        p.drawLine(QPointF(16.0, div_y), QPointF(w - 16.0, div_y))


class SidebarNavButton(QPushButton):
    """High-performance vector navigation button with custom line icons and gradient states."""

    def __init__(
        self,
        page_index: int,
        title: str,
        icon_type: str,
        accent_color: str = "#36C9E8",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(title, parent)
        self.page_index = page_index
        self.title = title
        self.icon_type = icon_type
        self.accent_color = accent_color

        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(38)
        self.setAttribute(Qt.WA_Hover, True)

    def sizeHint(self) -> QSize:
        return QSize(248, 38)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        is_active = self.isChecked()
        is_hover = self.underMouse() and not is_active

        btn_rect = QRectF(4.0, 1.0, w - 8.0, h - 2.0)

        # 1. Background State
        if is_active:
            # Dark Indigo-to-Blue Gradient
            bg_grad = QLinearGradient(4.0, 0, w - 4.0, 0)
            bg_grad.setColorAt(0.0, QColor(35, 55, 88, 210))
            bg_grad.setColorAt(0.45, QColor(24, 38, 62, 160))
            bg_grad.setColorAt(1.0, QColor(14, 23, 38, 80))
            p.setBrush(QBrush(bg_grad))
            p.setPen(QPen(QColor(54, 110, 180, 120), 1.0))
            p.drawRoundedRect(btn_rect, 6.0, 6.0)

            # Left Active Accent Pill Bar
            pill_h = h - 12.0
            pill_rect = QRectF(4.0, 6.0, 3.5, pill_h)
            pill_grad = QLinearGradient(4.0, 6.0, 4.0, 6.0 + pill_h)
            pill_grad.setColorAt(0.0, QColor(GRADIENT_PRIMARY_START))
            pill_grad.setColorAt(1.0, QColor(GRADIENT_PRIMARY_END))
            p.setBrush(QBrush(pill_grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(pill_rect, 1.75, 1.75)

        elif is_hover:
            # Subtle hover brightening
            p.setBrush(QBrush(QColor("#152033")))
            p.setPen(QPen(QColor(54, 201, 232, 50), 1.0))
            p.drawRoundedRect(btn_rect, 6.0, 6.0)
        else:
            # Normal inactive state
            p.setBrush(Qt.NoBrush)
            p.setPen(Qt.NoPen)

        # 2. Draw Vector Line Icon
        ix = 18.0
        iy = (h - 18.0) / 2.0

        if is_active:
            icon_col = QColor(self.accent_color)
            pen_width = 1.75
        elif is_hover:
            icon_col = QColor(COLOR_TEXT_PRIMARY)
            pen_width = 1.6
        else:
            icon_col = QColor(COLOR_TEXT_SECONDARY)
            pen_width = 1.5

        p.setPen(QPen(icon_col, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        self._draw_vector_icon(p, ix, iy, is_active)

        # 3. Draw Navigation Label Text
        tx = 44.0
        text_w = w - tx - 24.0
        text_rect = QRectF(tx, 0.0, text_w, h)

        if is_active:
            font = QFont("Inter", 10, QFont.DemiBold)
            text_color = QColor(COLOR_TEXT_PRIMARY)
        elif is_hover:
            font = QFont("Inter", 10, QFont.Medium)
            text_color = QColor(COLOR_TEXT_PRIMARY)
        else:
            font = QFont("Inter", 10, QFont.Normal)
            text_color = QColor(COLOR_TEXT_SECONDARY)

        p.setFont(font)
        p.setPen(text_color)
        p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.title)

        # 4. Active Right Subtle Indicator
        if is_active:
            p.setPen(QPen(QColor(GRADIENT_PRIMARY_END), 1.5, Qt.SolidLine, Qt.RoundCap))
            cx = w - 16.0
            cy = h / 2.0
            p.drawLine(QPointF(cx - 2.0, cy - 3.5), QPointF(cx + 1.5, cy))
            p.drawLine(QPointF(cx + 1.5, cy), QPointF(cx - 2.0, cy + 3.5))

    def _draw_vector_icon(self, p: QPainter, ix: float, iy: float, is_active: bool) -> None:
        """Render distinct, modern 18x18 vector line icon."""
        t = self.icon_type

        if t == "dashboard":
            # 4 rounded tiles
            p.drawRoundedRect(QRectF(ix + 1.0, iy + 1.0, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 9.5, iy + 1.0, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 1.0, iy + 9.5, 6.0, 6.0), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 9.5, iy + 9.5, 6.0, 6.0), 1.5, 1.5)

        elif t == "core_monitor":
            # CPU chip with pins
            p.drawRoundedRect(QRectF(ix + 3.5, iy + 3.5, 10.5, 10.5), 2.0, 2.0)
            p.drawLine(QPointF(ix + 8.75, iy + 4.0), QPointF(ix + 8.75, iy + 13.5))
            p.drawLine(QPointF(ix + 4.0, iy + 8.75), QPointF(ix + 13.5, iy + 8.75))
            # Pins
            p.drawLine(QPointF(ix + 6.0, iy + 0.5), QPointF(ix + 6.0, iy + 2.5))
            p.drawLine(QPointF(ix + 11.5, iy + 0.5), QPointF(ix + 11.5, iy + 2.5))
            p.drawLine(QPointF(ix + 6.0, iy + 15.0), QPointF(ix + 6.0, iy + 17.0))
            p.drawLine(QPointF(ix + 11.5, iy + 15.0), QPointF(ix + 11.5, iy + 17.0))
            p.drawLine(QPointF(ix + 0.5, iy + 6.0), QPointF(ix + 2.5, iy + 6.0))
            p.drawLine(QPointF(ix + 0.5, iy + 11.5), QPointF(ix + 2.5, iy + 11.5))
            p.drawLine(QPointF(ix + 15.0, iy + 6.0), QPointF(ix + 17.0, iy + 6.0))
            p.drawLine(QPointF(ix + 15.0, iy + 11.5), QPointF(ix + 17.0, iy + 11.5))

        elif t == "process_monitor":
            # 3 task bars with bullets
            p.drawEllipse(QRectF(ix + 1.5, iy + 3.5, 2.5, 2.5))
            p.drawLine(QPointF(ix + 6.5, iy + 4.75), QPointF(ix + 16.5, iy + 4.75))
            p.drawEllipse(QRectF(ix + 1.5, iy + 8.0, 2.5, 2.5))
            p.drawLine(QPointF(ix + 6.5, iy + 9.25), QPointF(ix + 13.5, iy + 9.25))
            p.drawEllipse(QRectF(ix + 1.5, iy + 12.5, 2.5, 2.5))
            p.drawLine(QPointF(ix + 6.5, iy + 13.75), QPointF(ix + 15.5, iy + 13.75))

        elif t == "real_stress":
            # Dynamic lightning bolt
            path = QPainterPath()
            path.moveTo(ix + 10.5, iy + 1.0)
            path.lineTo(ix + 4.5, iy + 9.5)
            path.lineTo(ix + 9.5, iy + 9.5)
            path.lineTo(ix + 7.5, iy + 17.0)
            path.lineTo(ix + 14.5, iy + 8.5)
            path.lineTo(ix + 9.5, iy + 8.5)
            path.closeSubpath()
            p.drawPath(path)

        elif t == "process_scheduler":
            # Stepped Gantt timeline blocks
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 2.5, 7.0, 4.5), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 6.0, iy + 8.0, 8.0, 4.5), 1.5, 1.5)
            p.drawRoundedRect(QRectF(ix + 10.5, iy + 13.5, 6.0, 3.5), 1.5, 1.5)

        elif t == "virtual_config":
            # 3 slider controls on vertical tracks
            p.drawLine(QPointF(ix + 4.0, iy + 1.5), QPointF(ix + 4.0, iy + 16.5))
            p.drawLine(QPointF(ix + 9.0, iy + 1.5), QPointF(ix + 9.0, iy + 16.5))
            p.drawLine(QPointF(ix + 14.0, iy + 1.5), QPointF(ix + 14.0, iy + 16.5))
            p.drawEllipse(QRectF(ix + 2.0, iy + 4.5, 4.0, 4.0))
            p.drawEllipse(QRectF(ix + 7.0, iy + 10.5, 4.0, 4.0))
            p.drawEllipse(QRectF(ix + 12.0, iy + 6.0, 4.0, 4.0))

        elif t == "virtual_monitor":
            # Virtual core matrix frame with 4 circular virtual cores
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 1.5, 15.0, 15.0), 3.0, 3.0)
            p.drawEllipse(QRectF(ix + 4.5, iy + 4.5, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 10.5, iy + 4.5, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 4.5, iy + 10.5, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 10.5, iy + 10.5, 3.0, 3.0))

        elif t == "virtual_scheduler":
            # Queue dispatcher clock
            p.drawArc(QRectF(ix + 2.0, iy + 2.0, 14.0, 14.0), 45 * 16, 270 * 16)
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 9.0, iy + 5.0))
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 12.5, iy + 9.0))
            p.drawLine(QPointF(ix + 15.0, iy + 2.5), QPointF(ix + 15.0, iy + 6.5))
            p.drawLine(QPointF(ix + 15.0, iy + 2.5), QPointF(ix + 11.5, iy + 2.5))

        elif t == "data_parallel":
            # Array scatter / SIMD multi-worker fork
            p.drawRoundedRect(QRectF(ix + 1.5, iy + 4.5, 4.0, 9.0), 1.5, 1.5)
            p.drawLine(QPointF(ix + 5.5, iy + 9.0), QPointF(ix + 9.0, iy + 9.0))
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 12.5, iy + 4.0))
            p.drawLine(QPointF(ix + 12.5, iy + 4.0), QPointF(ix + 16.5, iy + 4.0))
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 16.5, iy + 9.0))
            p.drawLine(QPointF(ix + 9.0, iy + 9.0), QPointF(ix + 12.5, iy + 14.0))
            p.drawLine(QPointF(ix + 12.5, iy + 14.0), QPointF(ix + 16.5, iy + 14.0))

        elif t == "task_parallel":
            # Directed Acyclic Graph (DAG) with nodes and dependency edges
            p.drawEllipse(QRectF(ix + 7.5, iy + 1.0, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 2.0, iy + 8.0, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 13.0, iy + 8.0, 3.0, 3.0))
            p.drawEllipse(QRectF(ix + 7.5, iy + 14.0, 3.0, 3.0))
            # Edges
            p.drawLine(QPointF(ix + 8.0, iy + 4.0), QPointF(ix + 4.5, iy + 8.0))
            p.drawLine(QPointF(ix + 10.0, iy + 4.0), QPointF(ix + 13.5, iy + 8.0))
            p.drawLine(QPointF(ix + 4.5, iy + 11.0), QPointF(ix + 8.0, iy + 14.0))
            p.drawLine(QPointF(ix + 13.5, iy + 11.0), QPointF(ix + 10.0, iy + 14.0))

        elif t == "performance":
            # Performance scalability curve and axis
            p.drawLine(QPointF(ix + 1.5, iy + 1.5), QPointF(ix + 1.5, iy + 16.5))
            p.drawLine(QPointF(ix + 1.5, iy + 16.5), QPointF(ix + 16.5, iy + 16.5))
            curve = QPainterPath()
            curve.moveTo(ix + 3.0, iy + 14.5)
            curve.cubicTo(ix + 6.0, iy + 13.0, ix + 10.0, iy + 6.0, ix + 16.0, iy + 3.5)
            p.drawPath(curve)
            p.drawEllipse(QRectF(ix + 14.5, iy + 2.0, 3.0, 3.0))

        elif t == "comparison":
            # Dual comparative scales / Real vs Virtual balance
            p.drawLine(QPointF(ix + 9.0, iy + 2.0), QPointF(ix + 9.0, iy + 16.0))
            p.drawLine(QPointF(ix + 3.0, iy + 6.0), QPointF(ix + 15.0, iy + 6.0))
            # Left pan
            p.drawLine(QPointF(ix + 3.0, iy + 6.0), QPointF(ix + 1.0, iy + 11.0))
            p.drawLine(QPointF(ix + 3.0, iy + 6.0), QPointF(ix + 5.0, iy + 11.0))
            p.drawLine(QPointF(ix + 1.0, iy + 11.0), QPointF(ix + 5.0, iy + 11.0))
            # Right pan
            p.drawLine(QPointF(ix + 15.0, iy + 6.0), QPointF(ix + 13.0, iy + 11.0))
            p.drawLine(QPointF(ix + 15.0, iy + 6.0), QPointF(ix + 17.0, iy + 11.0))
            p.drawLine(QPointF(ix + 13.0, iy + 11.0), QPointF(ix + 17.0, iy + 11.0))

        elif t == "settings":
            # Engineering gear
            p.drawEllipse(QRectF(ix + 3.0, iy + 3.0, 12.0, 12.0))
            p.drawEllipse(QRectF(ix + 6.5, iy + 6.5, 5.0, 5.0))
            p.drawLine(QPointF(ix + 9.0, iy + 0.5), QPointF(ix + 9.0, iy + 3.0))
            p.drawLine(QPointF(ix + 9.0, iy + 15.0), QPointF(ix + 9.0, iy + 17.5))
            p.drawLine(QPointF(ix + 0.5, iy + 9.0), QPointF(ix + 3.0, iy + 9.0))
            p.drawLine(QPointF(ix + 15.0, iy + 9.0), QPointF(ix + 17.5, iy + 9.0))
            p.drawLine(QPointF(ix + 3.0, iy + 3.0), QPointF(ix + 4.75, iy + 4.75))
            p.drawLine(QPointF(ix + 13.25, iy + 13.25), QPointF(ix + 15.0, iy + 15.0))
            p.drawLine(QPointF(ix + 15.0, iy + 3.0), QPointF(ix + 13.25, iy + 4.75))
            p.drawLine(QPointF(ix + 4.75, iy + 13.25), QPointF(ix + 3.0, iy + 15.0))


class WorkstationStatusWidget(QFrame):
    """Bottom status card displaying live system load, engine state, and version."""

    def __init__(self, physical_cores: int = 8, logical_cores: int = 16, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.physical_cores = physical_cores
        self.logical_cores = logical_cores
        self.current_load: float = 0.0

        self.setObjectName("sidebarStatusCard")
        self.setFixedHeight(94)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        # 1. Top Row: Status Dot + Engine Status + Version
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.status_dot = QLabel("●", self)
        self.status_dot.setStyleSheet("color: #42D6B0; font-size: 11px;")
        top_row.addWidget(self.status_dot)

        self.lbl_status = QLabel("Engine Ready", self)
        self.lbl_status.setStyleSheet("color: #96A8C2; font-size: 11px; font-weight: 600;")
        top_row.addWidget(self.lbl_status)
        top_row.addStretch(1)

        self.lbl_version = QLabel(f"v{APP_VERSION}", self)
        self.lbl_version.setStyleSheet("color: #71839D; font-size: 10px; font-weight: 500;")
        top_row.addWidget(self.lbl_version)
        layout.addLayout(top_row)

        # 2. Middle Row: Load Text
        mid_row = QHBoxLayout()
        mid_row.setContentsMargins(0, 0, 0, 0)

        lbl_load_title = QLabel("System Load", self)
        lbl_load_title.setStyleSheet("color: #71839D; font-size: 10.5px;")
        mid_row.addWidget(lbl_load_title)
        mid_row.addStretch(1)

        self.sidebar_load_label = QLabel("0.0%", self)
        self.sidebar_load_label.setStyleSheet("color: #E8EEF8; font-size: 11px; font-weight: 700;")
        mid_row.addWidget(self.sidebar_load_label)
        layout.addLayout(mid_row)

        # 3. Mini Gradient Progress Bar
        self.progress_bar = QFrame(self)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet("background-color: #19263A; border-radius: 2px;")
        layout.addWidget(self.progress_bar)

        # 4. Topology Tag
        self.lbl_topology = QLabel(f"{self.physical_cores}P / {self.logical_cores}L Cores Online", self)
        self.lbl_topology.setStyleSheet("color: #71839D; font-size: 9.5px;")
        layout.addWidget(self.lbl_topology)

    def update_load(self, percent: float) -> None:
        """Update system load value and progress bar width."""
        self.current_load = max(0.0, min(100.0, percent))
        self.sidebar_load_label.setText(f"{self.current_load:.1f}%")
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        # Custom gradient overlay on the mini progress bar
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        # Progress bar geometry
        pb_geo = self.progress_bar.geometry()
        bw = float(pb_geo.width())
        fill_w = max(4.0, bw * (self.current_load / 100.0))

        fill_rect = QRectF(float(pb_geo.x()), float(pb_geo.y()), fill_w, float(pb_geo.height()))
        grad = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
        grad.setColorAt(0.0, QColor(GRADIENT_PRIMARY_START))
        grad.setColorAt(1.0, QColor(GRADIENT_PRIMARY_END))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(fill_rect, 2.0, 2.0)

