"""Analytics Canvas Widgets for Performance Visualization in CoreSync.

Provides high-contrast QPainter canvas implementations for:
- Amdahl's Law Speedup Curve with interactive operating point, asymptote, and gradient area fills.
- Empirical Scalability Chart with multi-worker measurements and linear scaling reference.
- Stacked Execution Lifecycle Timing Breakdown (Startup, Dispatch, Compute, Collection, Overhead).
"""

import math
from typing import Dict, List, Optional, Tuple
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
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from engine.analytics.amdahl import AmdahlCalculator


# Black Gradient Data Visualization Palette (No Blue)
PALETTE = {
    "bg": QColor("#08090B"),
    "card_bg": QColor("#151416"),
    "card_alt": QColor("#1C191D"),
    "border": QColor("#302B32"),
    "grid": QColor("#221F24"),
    "text": QColor("#F2F0F3"),
    "text_muted": QColor("#77717C"),
    "teal": QColor("#19C99A"),
    "emerald": QColor("#42D6A0"),
    "violet": QColor("#A879F5"),
    "purple": QColor("#7956C8"),
    "magenta": QColor("#D17BE8"),
    "amber": QColor("#E4AD69"),
    "red": QColor("#EF737D"),
    "pink": QColor("#D17BE8"),
    "blue": QColor("#19C99A"),   # Backward compat alias mapped to Teal
    "green": QColor("#42D6A0"),  # Backward compat alias mapped to Emerald
    "cyan": QColor("#19C99A"),   # Backward compat alias mapped to Teal
}


class AmdahlCurveWidget(QWidget):
    """Visualizes Amdahl's Law theoretical speedup curve and operating point with gradient fill."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self._parallel_fraction: float = 0.85
        self._operating_processors: int = 8
        self._max_processors: int = 32

    def set_parameters(
        self,
        p: Optional[float] = None,
        n_op: Optional[int] = None,
        n_max: Optional[int] = None,
        *,
        parallel_fraction: Optional[float] = None,
        operating_processors: Optional[int] = None,
        max_processors: Optional[int] = None,
    ) -> None:
        val_p = parallel_fraction if parallel_fraction is not None else (p if p is not None else 0.85)
        val_nop = operating_processors if operating_processors is not None else (n_op if n_op is not None else 8)
        val_nmax = max_processors if max_processors is not None else (n_max if n_max is not None else 32)

        self._parallel_fraction = max(0.0, min(1.0, float(val_p)))
        self._operating_processors = max(1, int(val_nop))
        self._max_processors = max(2, int(val_nmax))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        w = self.width()
        h = self.height()
        painter.fillRect(0, 0, w, h, PALETTE["card_bg"])

        p = self._parallel_fraction
        max_n = self._max_processors
        cur_pred = AmdahlCalculator.evaluate(p, self._operating_processors)
        s_max = cur_pred.theoretical_max_speedup

        ml, mr, mt, mb = 55, 30, 30, 40
        plot_w = max(50, w - ml - mr)
        plot_h = max(50, h - mt - mb)

        # Upper bound on Y axis
        finite_smax = s_max if not math.isinf(s_max) else float(max_n)
        y_max = max(2.0, math.ceil(max(finite_smax * 1.15, 4.0)))

        # Draw Grid & Y ticks
        painter.setFont(QFont("Inter", 8))
        y_steps = 4
        for i in range(y_steps + 1):
            val = (y_max / y_steps) * i
            y_pos = mt + plot_h - (i / y_steps) * plot_h

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(ml, int(y_pos), ml + plot_w, int(y_pos))

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(0, y_pos - 8, ml - 8, 16), Qt.AlignRight | Qt.AlignVCenter, f"{val:.1f}x")

        # X Ticks
        for n_val in [1, 2, 4, 8, 16, 32, 64, 128]:
            if n_val > max_n:
                break
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w

            painter.setPen(QPen(PALETTE["grid"], 1, Qt.DashLine))
            painter.drawLine(int(x_pos), mt, int(x_pos), mt + plot_h)

            painter.setPen(PALETTE["text_muted"])
            painter.drawText(QRectF(x_pos - 15, mt + plot_h + 6, 30, 16), Qt.AlignCenter, str(n_val))

        # Border
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
                x_c = ml + ((y_max - 1) / (max_n - 1)) * plot_w
                lin_path.lineTo(x_c, mt)
                break
            x_pos = ml + ((n - 1) / (max_n - 1)) * plot_w
            y_pos = mt + plot_h - (n / y_max) * plot_h
            lin_path.lineTo(x_pos, y_pos)

        painter.setPen(QPen(QColor("#302B32"), 1.5, Qt.DotLine))
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

        # Gradient area fill under curve
        area_path = QPainterPath(curve_path)
        area_path.lineTo(ml + plot_w, mt + plot_h)
        area_path.lineTo(ml, mt + plot_h)
        area_path.closeSubpath()

        grad = QLinearGradient(0, mt, 0, mt + plot_h)
        c_top = QColor(PALETTE["teal"])
        c_top.setAlpha(45)
        c_bot = QColor(PALETTE["teal"])
        c_bot.setAlpha(2)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(area_path)

        # Stroke line
        painter.setPen(QPen(PALETTE["teal"], 2.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(curve_path)

        # 4. Active Operating Point
        op_n = self._operating_processors
        op_s = cur_pred.theoretical_speedup
        pt_x = ml + ((op_n - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
        pt_y = mt + plot_h - (op_s / y_max) * plot_h

        # Drop lines
        painter.setPen(QPen(PALETTE["teal"], 1, Qt.DashLine))
        painter.drawLine(int(pt_x), int(pt_y), int(pt_x), mt + plot_h)
        painter.drawLine(ml, int(pt_y), int(pt_x), int(pt_y))

        # Point circle
        painter.setBrush(QBrush(PALETTE["teal"]))
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

        # Titles and legend
        painter.setFont(QFont("Inter", 8))
        painter.setPen(PALETTE["text_muted"])
        painter.drawText(QRectF(ml, h - 22, plot_w, 20), Qt.AlignCenter, "Processor Count (N)")

        painter.setPen(PALETTE["teal"])
        painter.drawText(ml + 10, mt + 16, f"― S(N) for P={p:.2f}")
        painter.setPen(QColor("#77717C"))
        painter.drawText(ml + 160, mt + 16, "··· Linear Scaling (S = N)")


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
        painter.setPen(QPen(QColor("#302B32"), 1.5, Qt.DotLine))
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

        # Subtle gradient area fill under empirical curve
        area_path = QPainterPath(path)
        last_x = ml + ((max_n - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
        area_path.lineTo(last_x, mt + plot_h)
        area_path.lineTo(ml, mt + plot_h)
        area_path.closeSubpath()

        grad = QLinearGradient(0, mt, 0, mt + plot_h)
        c_top = QColor(PALETTE["teal"])
        c_top.setAlpha(40)
        c_bot = QColor(PALETTE["teal"])
        c_bot.setAlpha(2)
        grad.setColorAt(0.0, c_top)
        grad.setColorAt(1.0, c_bot)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawPath(area_path)

        painter.setPen(QPen(PALETTE["teal"], 2.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Points
        for n_val, s_val, eff in self._data_points:
            x_pos = ml + ((n_val - 1) / (max_n - 1)) * plot_w if max_n > 1 else ml
            y_pos = mt + plot_h - (s_val / y_max) * plot_h

            painter.setBrush(QBrush(PALETTE["teal"]))
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

        painter.setPen(PALETTE["teal"])
        painter.drawText(ml + 10, mt + 16, f"― {self._series_title}")
        painter.setPen(QColor("#77717C"))
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
            ("Task Dispatch", self._timings.get("dispatch_s", 0.0), PALETTE["violet"]),
            ("Parallel Compute", self._timings.get("compute_s", 0.0), PALETTE["teal"]),
            ("Result Collection", self._timings.get("collection_s", 0.0), PALETTE["amber"]),
            ("Result Merge", self._timings.get("merge_s", 0.0), PALETTE["magenta"]),
            ("No-Worker-Compute Time", self._timings.get("no_worker_compute_time_s", self._timings.get("residual_s", self._timings.get("idle_gap_time_s", self._timings.get("estimated_distribution_overhead_s", 0.0)))), PALETTE["red"]),
        ]
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
