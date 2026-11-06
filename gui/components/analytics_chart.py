"""Custom QPainter Canvas Widgets for Performance Analytics Visualizations.

Provides dark-themed, high-DPI rendering for:
- Amdahl's Law Speedup & Efficiency curves with theoretical asymptote and operating point.
- Multi-run Empirical Scalability (Speedup vs Worker Count) compared to Linear Ideal.
- Execution Timing Breakdown stacked bar chart (Startup, Dispatch, Compute, Collection, Merge, Overhead).
"""

import math
from typing import Dict, List, Optional, Tuple
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from engine.analytics.amdahl import AmdahlCalculator


# Professional workstation theme palette
PALETTE = {
    "bg": QColor("#0d1117"),
    "card_bg": QColor("#161b22"),
    "border": QColor("#30363d"),
    "grid": QColor("#21262d"),
    "text": QColor("#c9d1d9"),
    "text_muted": QColor("#8b949e"),
    "blue": QColor("#58a6ff"),
    "green": QColor("#3fb950"),
    "amber": QColor("#d29922"),
    "purple": QColor("#bc8cff"),
    "pink": QColor("#db61a2"),
    "red": QColor("#f85149"),
    "cyan": QColor("#39c5cf"),
}


class AmdahlCurveWidget(QWidget):
    """Visualizes Amdahl's Law theoretical speedup curve and operating point."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self._parallel_fraction: float = 0.85
        self._operating_processors: int = 8
        self._max_sweep_processors: int = 32

    def set_parameters(self, parallel_fraction: float, operating_processors: int, max_processors: int = 32) -> None:
        self._parallel_fraction = max(0.0, min(1.0, parallel_fraction))
        self._operating_processors = max(1, operating_processors)
        self._max_sweep_processors = max(operating_processors, max_processors)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, PALETTE["card_bg"])

        # Margins
        ml, mr, mt, mb = 55, 30, 30, 40
        plot_w = max(50, w - ml - mr)
        plot_h = max(50, h - mt - mb)

        # Theoretical S_max
        p = self._parallel_fraction
        s_max = AmdahlCalculator.calculate_max_speedup(p)
        cur_pred = AmdahlCalculator.predict(p, self._operating_processors)

        # Determine y-axis scale
        # If P=1, linear S=N. For general P, cap axis appropriately
        max_n = self._max_sweep_processors
        max_s_on_curve = AmdahlCalculator.calculate_speedup(p, max_n)
        y_max = max(4.0, math.ceil(min(max_n, max(max_s_on_curve * 1.25, cur_pred.theoretical_speedup * 1.3))))
        if not math.isinf(s_max) and s_max < max_n:
            y_max = max(y_max, math.ceil(s_max * 1.15))

        # Grid lines and Y ticks
        painter.setFont(QFont("Inter", 8))
        y_steps = 4
        for i in range(y_steps + 1):
            val = (y_max / y_steps) * i
            y_pos = mt + plot_h - (i / y_steps) * plot_h

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(ml, int(y_pos), ml + plot_w, int(y_pos))

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(0, y_pos - 8, ml - 8, 16), Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}x")

        # X ticks
        x_steps = min(8, max_n)
        for i in range(x_steps + 1):
            if i == 0:
                continue
            n_val = int(round((max_n / x_steps) * i))
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(int(x_pos), mt, int(x_pos), mt + plot_h)

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(x_pos - 15, mt + plot_h + 6, 30, 16), Qt.AlignCenter, str(n_val))

        # Axes borders
        painter.setPen(QPen(PALETTE["border"], 1))
        painter.drawRect(ml, mt, plot_w, plot_h)

        # 1. Asymptote Line (S_max) if finite and within bounds
        if not math.isinf(s_max) and s_max <= y_max:
            asymp_y = mt + plot_h - (s_max / y_max) * plot_h
            painter.setPen(QPen(PALETTE["amber"], 1.5, Qt.DashDotLine))
            painter.drawLine(ml, int(asymp_y), ml + plot_w, int(asymp_y))
            painter.setPen(PALETTE["amber"])
            painter.setFont(QFont("Inter", 8, QFont.Bold))
            painter.drawText(ml + plot_w - 120, int(asymp_y) - 6, f"S_max = {s_max:.2f}x")

        # 2. Linear Scaling Reference Line (y = x)
        lin_path = QPainterPath()
        lin_path.moveTo(ml, mt + plot_h - (1.0 / y_max) * plot_h)
        for n in range(2, max_n + 1):
            if n > y_max:
                # clamp to border
                x_c = ml + ((y_max - 1) / (max_n - 1)) * plot_w
                lin_path.lineTo(x_c, mt)
                break
            x_pos = ml + ((n - 1) / (max_n - 1)) * plot_w
            y_pos = mt + plot_h - (n / y_max) * plot_h
            lin_path.lineTo(x_pos, y_pos)

        painter.setPen(QPen(QColor("#30363d"), 1.5, Qt.DotLine))
        painter.drawPath(lin_path)

        # 3. Amdahl Theoretical Speedup Curve
        curve_path = QPainterPath()
        first = True
        for n in range(1, max_n + 1):
            s = AmdahlCalculator.calculate_speedup(p, n)
            x_pos = ml + ((n - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
            y_pos = mt + plot_h - (s / y_max) * plot_h
            if first:
                curve_path.moveTo(x_pos, y_pos)
                first = False
            else:
                curve_path.lineTo(x_pos, y_pos)

        painter.setPen(QPen(PALETTE["blue"], 2.5))
        painter.drawPath(curve_path)

        # 4. Active Operating Point
        op_n = self._operating_processors
        op_s = cur_pred.theoretical_speedup
        pt_x = ml + ((op_n - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
        pt_y = mt + plot_h - (op_s / y_max) * plot_h

        # Drop lines
        painter.setPen(QPen(PALETTE["blue"], 1, Qt.DashLine))
        painter.drawLine(int(pt_x), int(pt_y), int(pt_x), mt + plot_h)
        painter.drawLine(ml, int(pt_y), int(pt_x), int(pt_y))

        # Point circle
        painter.setBrush(QBrush(PALETTE["blue"]))
        painter.setPen(QPen(PALETTE["bg"], 2))
        painter.drawEllipse(QPointF(pt_x, pt_y), 6, 6)

        # Operating Point Tag
        tag_text = f"N={op_n}: {op_s:.2f}x ({cur_pred.theoretical_efficiency_pct:.1f}% Eff)"
        painter.setFont(QFont("Inter", 8, QFont.Bold))
        tag_rect = QRectF(pt_x + 8, pt_y - 20, 160, 20)
        if pt_x + 168 > ml + plot_w:
            tag_rect = QRectF(pt_x - 168, pt_y - 20, 160, 20)
        painter.setPen(PALETTE["text"])
        painter.drawText(tag_rect, Qt.AlignVCenter, tag_text)

        # Axis Titles & Legend
        painter.setFont(QFont("Inter", 8))
        painter.setPen(PALETTE["text_muted"])
        painter.drawText(QRectF(ml, h - 22, plot_w, 20), Qt.AlignCenter, "Processors / Worker Threads (N)")

        # Legend top right
        painter.setPen(PALETTE["blue"])
        painter.drawText(ml + 10, mt + 16, f"― Amdahl's Law (P = {p*100:.1f}%)")
        painter.setPen(QColor("#6e7681"))
        painter.drawText(ml + 180, mt + 16, "··· Linear Ideal (S = N)")


class ScalabilityChartWidget(QWidget):
    """Plots empirical multi-worker speedup measurements against linear ideal reference."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(420, 240)
        self._data_points: List[Tuple[int, float, float]] = []  # (workers, speedup, efficiency_pct)
        self._series_title: str = "Empirical Speedup"

    def set_data(self, data_points: List[Tuple[int, float, float]], title: str = "Empirical Speedup") -> None:
        self._data_points = sorted(data_points, key=lambda x: x[0])
        self._series_title = title
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, PALETTE["card_bg"])

        ml, mr, mt, mb = 55, 30, 30, 40
        plot_w = max(50, w - ml - mr)
        plot_h = max(50, h - mt - mb)

        if not self._data_points:
            painter.setFont(QFont("Inter", 10))
            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "No benchmark sweep data recorded yet.")
            return

        max_n = max(d[0] for d in self._data_points)
        max_s = max(d[1] for d in self._data_points)
        y_max = max(2.0, math.ceil(max(max_s * 1.25, float(max_n) * 1.1)))

        # Grid and Y ticks
        painter.setFont(QFont("Inter", 8))
        y_steps = 4
        for i in range(y_steps + 1):
            val = (y_max / y_steps) * i
            y_pos = mt + plot_h - (i / y_steps) * plot_h

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(ml, int(y_pos), ml + plot_w, int(y_pos))

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(0, y_pos - 8, ml - 8, 16), Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}x")

        # X ticks
        for d in self._data_points:
            n_val = d[0]
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(int(x_pos), mt, int(x_pos), mt + plot_h)

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(x_pos - 15, mt + plot_h + 6, 30, 16), Qt.AlignCenter, str(n_val))

        # Border
        painter.setPen(QPen(PALETTE["border"], 1))
        painter.drawRect(ml, mt, plot_w, plot_h)

        # Linear Ideal Line
        lin_path = QPainterPath()
        lin_path.moveTo(ml, mt + plot_h - (1.0 / y_max) * plot_h)
        x_end = ml + ((max_n - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
        y_end = mt + plot_h - (float(max_n) / y_max) * plot_h
        lin_path.lineTo(x_end, y_end)
        painter.setPen(QPen(QColor("#30363d"), 1.5, Qt.DotLine))
        painter.drawPath(lin_path)

        # Empirical Speedup Series
        path = QPainterPath()
        for idx, (n_val, s_val, _) in enumerate(self._data_points):
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
            y_pos = mt + plot_h - (s_val / y_max) * plot_h
            if idx == 0:
                path.moveTo(x_pos, y_pos)
            else:
                path.lineTo(x_pos, y_pos)

        painter.setPen(QPen(PALETTE["green"], 2.5))
        painter.drawPath(path)

        # Points
        for n_val, s_val, eff in self._data_points:
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
            y_pos = mt + plot_h - (s_val / y_max) * plot_h

            painter.setBrush(QBrush(PALETTE["green"]))
            painter.setPen(QPen(PALETTE["bg"], 2))
            painter.drawEllipse(QPointF(x_pos, y_pos), 5, 5)

            # Label point
            painter.setFont(QFont("Inter", 7, QFont.Bold))
            painter.setPen(PALETTE["text"])
            painter.drawText(QRectF(x_pos - 25, y_pos - 18, 50, 14), Qt.AlignCenter, f"{s_val:.2f}x")

        # Titles and legend
        painter.setFont(QFont("Inter", 8))
        painter.setPen(PALETTE["text_muted"])
        painter.drawText(QRectF(ml, h - 22, plot_w, 20), Qt.AlignCenter, "Active Multiprocessing Workers (W)")

        painter.setPen(PALETTE["green"])
        painter.drawText(ml + 10, mt + 16, f"― {self._series_title}")
        painter.setPen(QColor("#6e7681"))
        painter.drawText(ml + 180, mt + 16, "··· Linear Scaling (S = W)")


class TimingBreakdownWidget(QWidget):
    """Stacked horizontal bar chart depicting execution lifecycle timing overheads."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(420, 160)
        self._timings: Dict[str, float] = {}

    def set_timings(self, timings: Dict[str, float]) -> None:
        """Set execution segments: startup_s, dispatch_s, compute_s, collection_s, merge_s, etc."""
        self._timings = {k: max(0.0, float(v)) for k, v in timings.items()}
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, PALETTE["card_bg"])

        total_time = sum(self._timings.values())
        if total_time <= 0:
            painter.setFont(QFont("Inter", 9))
            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, "No lifecycle timing breakdown available.")
            return

        segments = [
            ("Process Startup", self._timings.get("startup_s", 0.0), PALETTE["purple"]),
            ("Task Dispatch", self._timings.get("dispatch_s", 0.0), PALETTE["blue"]),
            ("Parallel Compute", self._timings.get("compute_s", 0.0), PALETTE["green"]),
            ("Result Collection", self._timings.get("collection_s", 0.0), PALETTE["amber"]),
            ("Result Merge", self._timings.get("merge_s", 0.0), PALETTE["cyan"]),
            ("No-Worker-Compute Time", self._timings.get("no_worker_compute_time_s", self._timings.get("residual_s", self._timings.get("idle_gap_time_s", self._timings.get("estimated_distribution_overhead_s", 0.0)))), PALETTE["pink"]),
        ]
        # Filter non-zero
        active_segments = [s for s in segments if s[1] > 0]

        # Draw Title
        painter.setFont(QFont("Inter", 9, QFont.Bold))
        painter.setPen(PALETTE["text"])
        painter.drawText(20, 24, f"Parallel Makespan Breakdown (Total: {total_time * 1000.0:.2f} ms)")

        # Bar coordinates
        bar_x = 20
        bar_y = 40
        bar_w = w - 40
        bar_h = 32

        # Draw outer bar background
        painter.fillRect(bar_x, bar_y, bar_w, bar_h, PALETTE["grid"])

        # Stack segments
        cur_x = float(bar_x)
        for label, val, color in active_segments:
            seg_w = (val / total_time) * bar_w
            if seg_w < 1.0:
                continue
            painter.fillRect(QRectF(cur_x, bar_y, seg_w, bar_h), color)
            # Text inside segment if wide enough
            if seg_w > 45:
                pct = (val / total_time) * 100.0
                painter.setFont(QFont("Inter", 7, QFont.Bold))
                painter.setPen(PALETTE["bg"])
                painter.drawText(QRectF(cur_x, bar_y, seg_w, bar_h), Qt.AlignCenter, f"{pct:.1f}%")
            cur_x += seg_w

        # Draw border
        painter.setPen(QPen(PALETTE["border"], 1))
        painter.drawRect(bar_x, bar_y, bar_w, bar_h)

        # Legend below bar
        leg_x = 20
        leg_y = bar_y + bar_h + 18
        painter.setFont(QFont("Inter", 8))
        for label, val, color in active_segments:
            painter.fillRect(leg_x, leg_y + 2, 10, 10, color)
            painter.setPen(PALETTE["text_muted"])
            ms_val = val * 1000.0
            pct_val = (val / total_time) * 100.0
            text = f"{label}: {ms_val:.2f} ms ({pct_val:.1f}%)"
            painter.drawText(leg_x + 14, leg_y + 11, text)
            leg_x += len(text) * 7 + 22
            if leg_x > w - 120:
                leg_x = 20
                leg_y += 18

