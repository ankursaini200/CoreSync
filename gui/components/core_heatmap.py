"""Structured Per-Core Heatmap Grid Component for CoreSync.

Renders an interactive, responsive grid of logical/virtual CPU cores
with utilization-driven heat coloring, P/E classifications, and worker pinning tags.
"""

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
    COLOR_E_CORE,
    COLOR_P_CORE,
    COLOR_SUCCESS,
    COLOR_TASK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)
from utils.cpu_topology import CoreType


def get_heatmap_colors(percent: float) -> tuple[QColor, QColor, QColor]:
    """Returns (background_color, border_color, accent_color) for a given utilization percentage."""
    p = max(0.0, min(100.0, percent))
    if p < 25.0:
        # Deep Black with subtle Teal
        return QColor("#101512"), QColor("#1B2A22"), QColor("#19C99A")
    elif p < 50.0:
        # Deep Black with Emerald
        return QColor("#111A15"), QColor("#1E3A2C"), QColor("#42D6A0")
    elif p < 75.0:
        # Deep Black with Amber
        return QColor("#1F1911"), QColor("#3D2E1A"), QColor("#E4AD69")
    else:
        # Deep Black with Coral Red
        return QColor("#241113"), QColor("#481D22"), QColor("#EF737D")


class CoreHeatmapGridWidget(QWidget):
    """Visual matrix of individual cores displaying live utilization heatmaps and metadata."""

    def __init__(
        self,
        core_count: int = 8,
        core_types: Optional[Dict[int, CoreType]] = None,
        max_freqs: Optional[Dict[int, float]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.core_count = max(1, core_count)
        self.core_types: Dict[int, CoreType] = core_types or {}
        self.max_freqs: Dict[int, float] = max_freqs or {}

        self.per_cpu_percent: List[float] = [0.0] * self.core_count
        self.per_cpu_freq: List[float] = [0.0] * self.core_count
        self.worker_pinning: Dict[int, List[str]] = {}

        self._hover_index: Optional[int] = None
        self.setMouseTracking(True)
        self.setMinimumHeight(140)

    def update_telemetry(
        self,
        per_cpu_percent: List[float],
        per_cpu_freq_mhz: Optional[List[float]] = None,
        worker_pinning: Optional[Dict[int, List[str]]] = None,
    ) -> None:
        """Update live core utilization and frequency values."""
        self.per_cpu_percent = list(per_cpu_percent)
        if len(self.per_cpu_percent) < self.core_count:
            self.per_cpu_percent.extend([0.0] * (self.core_count - len(self.per_cpu_percent)))

        if per_cpu_freq_mhz:
            self.per_cpu_freq = list(per_cpu_freq_mhz)
            if len(self.per_cpu_freq) < self.core_count:
                self.per_cpu_freq.extend([0.0] * (self.core_count - len(self.per_cpu_freq)))

        if worker_pinning is not None:
            self.worker_pinning = worker_pinning

        self.update()

    def sizeHint(self) -> QSize:
        rows = (self.core_count + 5) // 6
        return QSize(600, rows * 85 + 20)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Determine optimal column layout
        if w >= 1100:
            cols = min(8, self.core_count)
        elif w >= 750:
            cols = min(6, self.core_count)
        elif w >= 500:
            cols = min(4, self.core_count)
        else:
            cols = min(2, self.core_count)

        cols = max(1, cols)
        rows = (self.core_count + cols - 1) // cols

        spacing = 10.0
        margin = 4.0
        avail_w = w - (margin * 2.0) - (spacing * (cols - 1))
        avail_h = h - (margin * 2.0) - (spacing * (rows - 1))

        tile_w = max(70.0, avail_w / cols)
        tile_h = max(75.0, min(100.0, avail_h / rows if rows > 0 else 85.0))

        for idx in range(self.core_count):
            r = idx // cols
            c = idx % cols
            x = margin + c * (tile_w + spacing)
            y = margin + r * (tile_h + spacing)
            tile_rect = QRectF(x, y, tile_w, tile_h)

            pct = self.per_cpu_percent[idx] if idx < len(self.per_cpu_percent) else 0.0
            freq = self.per_cpu_freq[idx] if idx < len(self.per_cpu_freq) else 0.0
            ctype = self.core_types.get(idx, CoreType.UNKNOWN)
            workers = self.worker_pinning.get(idx, [])
            is_hover = (idx == self._hover_index)

            self._draw_core_tile(painter, tile_rect, idx, pct, freq, ctype, workers, is_hover)

    def _draw_core_tile(
        self,
        painter: QPainter,
        rect: QRectF,
        cpu_id: int,
        pct: float,
        freq_mhz: float,
        ctype: CoreType,
        workers: List[str],
        is_hover: bool,
    ) -> None:
        bg_col, border_col, accent_col = get_heatmap_colors(pct)

        if is_hover:
            border_col = QColor("#19C99A")

        # 1. Tile Base Background
        painter.setPen(QPen(border_col, 1.5 if is_hover else 1.0))
        painter.setBrush(QBrush(bg_col))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        # 2. Header: CPU ID & Core Type Chip
        top_y = rect.y() + 6.0
        painter.setFont(QFont("Inter", 8, QFont.Bold))
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        painter.drawText(QRectF(rect.x() + 8, top_y, 45, 14), Qt.AlignLeft | Qt.AlignVCenter, f"CPU {cpu_id}")

        # Core Type Tag
        if ctype == CoreType.PERFORMANCE:
            painter.setFont(QFont("Inter", 7, QFont.Bold))
            painter.setPen(QColor(COLOR_P_CORE))
            painter.drawText(QRectF(rect.right() - 48, top_y, 40, 14), Qt.AlignRight | Qt.AlignVCenter, "P-CORE")
        elif ctype == CoreType.EFFICIENCY:
            painter.setFont(QFont("Inter", 7, QFont.Bold))
            painter.setPen(QColor(COLOR_E_CORE))
            painter.drawText(QRectF(rect.right() - 48, top_y, 40, 14), Qt.AlignRight | Qt.AlignVCenter, "E-CORE")

        # 3. Utilization Value (Center)
        painter.setFont(QFont("Inter", 13, QFont.Bold))
        painter.setPen(accent_col)
        val_rect = QRectF(rect.x() + 8, rect.y() + 22, rect.width() - 16, 22)
        painter.drawText(val_rect, Qt.AlignLeft | Qt.AlignVCenter, f"{pct:.1f}%")

        # 4. Secondary Row: Frequency or Worker Tag
        sec_y = rect.y() + 46
        painter.setFont(QFont("Inter", 8))
        if workers:
            w_str = f"• {workers[0]}"
            painter.setPen(QColor(COLOR_SUCCESS))
            painter.drawText(QRectF(rect.x() + 8, sec_y, rect.width() - 16, 14), Qt.AlignLeft | Qt.AlignVCenter, w_str)
        elif freq_mhz > 0:
            f_str = f"{int(round(freq_mhz))} MHz"
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(rect.x() + 8, sec_y, rect.width() - 16, 14), Qt.AlignLeft | Qt.AlignVCenter, f_str)
        else:
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(rect.x() + 8, sec_y, rect.width() - 16, 14), Qt.AlignLeft | Qt.AlignVCenter, "Active")

        # 5. Activity Bottom Bar (Indicator)
        bar_h = 3.0
        bar_y = rect.bottom() - 5.0
        bar_w = rect.width() - 16.0
        bar_x = rect.x() + 8.0

        # Track
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#1C191D"))
        painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 1.5, 1.5)

        # Active Fill
        fill_w = max(2.0, (pct / 100.0) * bar_w)
        painter.setBrush(accent_col)
        painter.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 1.5, 1.5)

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        w = self.width()
        if w >= 1100:
            cols = min(8, self.core_count)
        elif w >= 750:
            cols = min(6, self.core_count)
        elif w >= 500:
            cols = min(4, self.core_count)
        else:
            cols = min(2, self.core_count)

        cols = max(1, cols)
        rows = (self.core_count + cols - 1) // cols

        spacing = 10.0
        margin = 4.0
        avail_w = w - (margin * 2.0) - (spacing * (cols - 1))
        avail_h = self.height() - (margin * 2.0) - (spacing * (rows - 1))
        tile_w = max(70.0, avail_w / cols)
        tile_h = max(75.0, min(100.0, avail_h / rows if rows > 0 else 85.0))

        found_idx = None
        for idx in range(self.core_count):
            r = idx // cols
            c = idx % cols
            x = margin + c * (tile_w + spacing)
            y = margin + r * (tile_h + spacing)
            if QRectF(x, y, tile_w, tile_h).contains(pos):
                found_idx = idx
                break

        if found_idx != self._hover_index:
            self._hover_index = found_idx
            self.update()

        if self._hover_index is not None and self._hover_index < self.core_count:
            idx = self._hover_index
            pct = self.per_cpu_percent[idx] if idx < len(self.per_cpu_percent) else 0.0
            freq = self.per_cpu_freq[idx] if idx < len(self.per_cpu_freq) else 0.0
            ctype = self.core_types.get(idx, CoreType.UNKNOWN).name
            workers = self.worker_pinning.get(idx, [])
            w_info = f"<br/>Assigned Worker: <b>{', '.join(workers)}</b>" if workers else ""
            freq_info = f"<br/>Frequency: <b>{int(round(freq))} MHz</b>" if freq > 0 else ""

            tip = (
                f"<b>Logical Core {idx}</b><br/>"
                f"Utilization: <b>{pct:.1f}%</b><br/>"
                f"Classification: <b>{ctype}</b>"
                f"{freq_info}"
                f"{w_info}"
            )
            QToolTip.showText(event.globalPosition().toPoint(), tip, self)
        else:
            QToolTip.hideText()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_index = None
        self.update()
        super().leaveEvent(event)

