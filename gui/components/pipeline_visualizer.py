"""Visual Execution Pipeline Component for Data Parallelism.

Renders an interactive 4-stage pipeline:
Dataset ➔ Partitioning ➔ Multi-Worker Compute ➔ Result Aggregation & Verification.
"""

from typing import List, Optional
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
    COLOR_SUCCESS,
    COLOR_TASK,
    COLOR_TEXT_MUTED,
    COLOR_TEXT_PRIMARY,
)


class DataPipelineVisualizerWidget(QWidget):
    """Renders the 4-stage data parallel execution pipeline with animated/active state highlights."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.stage: int = 0  # 0: Ready, 1: Partitioning, 2: Workers Computing, 3: Completed & Verified
        self.dataset_size: int = 100_000
        self.worker_count: int = 4
        self.chunks_count: int = 4
        self.verified: bool = True
        self.makespan_ms: float = 0.0

        self.setMinimumHeight(95)
        self.setMouseTracking(True)

    def set_pipeline_state(
        self,
        stage: int,
        dataset_size: int = 100_000,
        worker_count: int = 4,
        chunks_count: int = 4,
        verified: bool = True,
        makespan_ms: float = 0.0,
    ) -> None:
        """Update current pipeline progress."""
        self.stage = stage
        self.dataset_size = dataset_size
        self.worker_count = worker_count
        self.chunks_count = chunks_count
        self.verified = verified
        self.makespan_ms = makespan_ms
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(600, 110)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        stages = [
            ("1. Input Dataset", f"{self.dataset_size:,} Items", "#19C99A"),
            ("2. Partitioning", f"{self.chunks_count} Chunks", "#A879F5"),
            ("3. Worker Pool", f"{self.worker_count} Workers", "#42D6A0"),
            ("4. Verification", "100% Match" if self.verified and self.stage == 3 else "Pending", "#42D6A0"),
        ]

        n_stages = len(stages)
        margin = 12.0
        avail_w = w - (margin * 2.0)
        gap = 24.0
        stage_w = (avail_w - (gap * (n_stages - 1))) / n_stages
        stage_h = h - (margin * 2.0)

        for i, (title, sub, col_hex) in enumerate(stages):
            sx = margin + i * (stage_w + gap)
            sy = margin
            s_rect = QRectF(sx, sy, stage_w, stage_h)

            is_active = (i <= self.stage)
            accent_col = QColor(col_hex) if is_active else QColor(COLOR_BORDER)
            bg_col = QColor(COLOR_BG_CARD_ALT) if is_active else QColor("#111113")

            # Stage Box
            painter.setPen(QPen(accent_col, 1.5 if is_active else 1.0))
            painter.setBrush(QBrush(bg_col))
            painter.drawRoundedRect(s_rect, 8.0, 8.0)

            # Stage Number & Title
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.setPen(QColor(COLOR_TEXT_PRIMARY if is_active else COLOR_TEXT_MUTED))
            painter.drawText(QRectF(sx + 8, sy + 10, stage_w - 16, 18), Qt.AlignCenter, title)

            # Subtitle / Metric
            painter.setFont(QFont("Inter", 11, QFont.Bold))
            painter.setPen(accent_col if is_active else QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(sx + 8, sy + 32, stage_w - 16, 22), Qt.AlignCenter, sub)

            # Subtle status pill
            status_text = "ACTIVE" if (i == self.stage and self.stage < 3) else ("COMPLETED" if i < self.stage or self.stage == 3 else "WAITING")
            painter.setFont(QFont("Inter", 7, QFont.Bold))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(QRectF(sx + 8, sy + 56, stage_w - 16, 14), Qt.AlignCenter, status_text)

            # Connector Arrow to next stage
            if i < n_stages - 1:
                arrow_x = sx + stage_w + (gap / 2.0)
                arrow_y = sy + (stage_h / 2.0)
                painter.setFont(QFont("Inter", 11, QFont.Bold))
                painter.setPen(QColor(COLOR_ACCENT if i < self.stage else COLOR_BORDER))
                painter.drawText(QRectF(arrow_x - 10, arrow_y - 10, 20, 20), Qt.AlignCenter, "➔")

