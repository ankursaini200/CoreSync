"""Interactive DAG Dependency Graph Visualization Canvas with Controlled Zoom and Responsive Layout."""

from typing import Dict, List, Optional
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from engine.task_parallel.task import Task, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from utils.config import (
    COLOR_BG_DARK,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_ACCENT,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
)

STATUS_COLORS = {
    TaskStatus.PENDING: (QColor("#18202C"), QColor(COLOR_BORDER), QColor(COLOR_TEXT_MUTED)),
    TaskStatus.BLOCKED: (QColor("#18202C"), QColor(COLOR_BORDER), QColor("#6E7A8A")),
    TaskStatus.READY: (QColor("#241F16"), QColor(COLOR_WARNING), QColor("#E0BC75")),
    TaskStatus.QUEUED: (QColor("#2B2016"), QColor("#B88636"), QColor("#E5A84F")),
    TaskStatus.RUNNING: (QColor("#162333"), QColor(COLOR_ACCENT), QColor("#89BAE8")),
    TaskStatus.COMPLETED: (QColor("#14291F"), QColor(COLOR_SUCCESS), QColor("#66C097")),
    TaskStatus.FAILED: (QColor("#2E181B"), QColor(COLOR_DANGER), QColor("#E58A8A")),
    TaskStatus.CANCELLED: (QColor("#18202C"), QColor(COLOR_BORDER), QColor(COLOR_TEXT_MUTED)),
}


class DAGCanvasWidget(QWidget):
    """Custom QPainter widget rendering DAG nodes and dependency edges with internal zoom."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._graph: Optional[TaskGraph] = None
        self._node_positions: Dict[str, QRectF] = {}
        self._zoom: float = 1.0
        self.setMinimumHeight(240)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; border-radius: 6px;")

    def set_graph(self, graph: Optional[TaskGraph]) -> None:
        """Bind graph and recompute layout."""
        self._graph = graph
        self._compute_layout()
        self.update()

    def update_task_state(self, task_id: str) -> None:
        """Trigger canvas repaint on task status changes."""
        self.update()

    def set_zoom(self, zoom: float) -> None:
        """Apply zoom factor and recompute node positions."""
        self._zoom = max(0.5, min(2.5, zoom))
        self._compute_layout()
        self.update()

    def zoom_in(self) -> float:
        self.set_zoom(self._zoom * 1.15)
        return self._zoom

    def zoom_out(self) -> float:
        self.set_zoom(self._zoom / 1.15)
        return self._zoom

    def reset_zoom(self) -> None:
        self.set_zoom(1.0)

    def _compute_layout(self) -> None:
        """Calculate layered left-to-right topological layout coordinates."""
        self._node_positions.clear()
        if not self._graph or not self._graph.tasks:
            return

        # 1. Compute layer (depth) for each node using topological sort
        layers: Dict[str, int] = {}
        for t_id in self._graph.tasks:
            layers[t_id] = 0

        # Propagate depths
        changed = True
        iterations = 0
        while changed and iterations < len(self._graph.tasks) + 1:
            changed = False
            iterations += 1
            for child_id, parents in self._graph.dependencies.items():
                if parents:
                    max_p_layer = max(layers.get(p, 0) for p in parents)
                    if layers[child_id] != max_p_layer + 1:
                        layers[child_id] = max_p_layer + 1
                        changed = True

        # Group nodes by layer
        nodes_by_layer: Dict[int, List[str]] = {}
        for t_id, lyr in layers.items():
            nodes_by_layer.setdefault(lyr, []).append(t_id)

        # 2. Position nodes in canvas
        z = self._zoom
        node_w = 160.0 * z
        node_h = 52.0 * z
        col_gap = 52.0 * z
        row_gap = 16.0 * z
        left_margin = 24.0 * z
        top_margin = 20.0 * z

        max_layer = max(nodes_by_layer.keys()) if nodes_by_layer else 0
        max_rows = max(len(col) for col in nodes_by_layer.values()) if nodes_by_layer else 1

        total_width = left_margin * 2 + (max_layer + 1) * (node_w + col_gap)
        total_height = top_margin * 2 + max_rows * (node_h + row_gap)
        self.resize(int(total_width), max(240, int(total_height)))
        self.setMinimumSize(int(total_width), max(240, int(total_height)))

        for lyr, node_ids in nodes_by_layer.items():
            x = left_margin + lyr * (node_w + col_gap)
            col_height = len(node_ids) * node_h + (len(node_ids) - 1) * row_gap
            y_start = top_margin + max(0.0, (total_height - col_height) / 2.0 - top_margin)

            for row_idx, t_id in enumerate(node_ids):
                y = y_start + row_idx * (node_h + row_gap)
                self._node_positions[t_id] = QRectF(x, y, node_w, node_h)

    def paintEvent(self, event) -> None:
        """Render edges and task cards."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), QColor(COLOR_BG_DARK))

        if not self._graph or not self._node_positions:
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignCenter, "No DAG Workload Loaded. Select a Preset above.")
            return

        # 1. Draw directed dependency edges
        for child_id, parents in self._graph.dependencies.items():
            child_rect = self._node_positions.get(child_id)
            if not child_rect:
                continue

            for parent_id in parents:
                parent_rect = self._node_positions.get(parent_id)
                if not parent_rect:
                    continue
                self._draw_edge(painter, parent_rect, child_rect, parent_id, child_id)

        # 2. Draw task nodes
        for t_id, task in self._graph.tasks.items():
            rect = self._node_positions.get(t_id)
            if rect:
                self._draw_node(painter, rect, task)

    def _draw_edge(self, painter: QPainter, r1: QRectF, r2: QRectF, p_id: str, c_id: str) -> None:
        """Draw smooth cubic Bezier arrow from right edge of r1 to left edge of r2."""
        start = QPointF(r1.right(), r1.center().y())
        end = QPointF(r2.left(), r2.center().y())

        # Determine edge color based on status
        p_task = self._graph.tasks.get(p_id)
        if p_task and p_task.status == TaskStatus.COMPLETED:
            edge_color = QColor(COLOR_SUCCESS)
        elif p_task and p_task.status == TaskStatus.RUNNING:
            edge_color = QColor(COLOR_ACCENT)
        elif p_task and p_task.status == TaskStatus.FAILED:
            edge_color = QColor(COLOR_DANGER)
        else:
            edge_color = QColor(COLOR_BORDER)

        pen = QPen(edge_color, 1.8, Qt.SolidLine)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(start)
        dx = (end.x() - start.x()) * 0.5
        c1 = QPointF(start.x() + dx, start.y())
        c2 = QPointF(end.x() - dx, end.y())
        path.cubicTo(c1, c2, end)
        painter.drawPath(path)

        # Draw arrowhead
        arrow_size = 6.0 * max(0.8, self._zoom)
        arrow = QPolygonF([
            end,
            QPointF(end.x() - arrow_size * 1.5, end.y() - arrow_size),
            QPointF(end.x() - arrow_size * 1.5, end.y() + arrow_size),
        ])
        painter.setBrush(QBrush(edge_color))
        painter.drawPolygon(arrow)

    def _draw_node(self, painter: QPainter, rect: QRectF, task: Task) -> None:
        """Draw rounded task card with status and metadata."""
        bg_color, border_color, text_color = STATUS_COLORS.get(
            task.status,
            (QColor("#18202C"), QColor(COLOR_BORDER), QColor(COLOR_TEXT_MUTED)),
        )

        # Card body
        painter.setPen(QPen(border_color, 1.2))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 6.0, 6.0)

        # Title text
        painter.setPen(QColor(COLOR_TEXT_PRIMARY))
        font_size = max(7, int(8 * max(0.85, self._zoom)))
        title_font = QFont("-apple-system, Segoe UI, sans-serif", font_size, QFont.DemiBold)
        painter.setFont(title_font)
        title_rect = QRectF(rect.left() + 8, rect.top() + 5, rect.width() - 16, 16)
        title_text = task.name if len(task.name) <= 20 else (task.name[:18] + "…")
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, title_text)

        # Type label
        type_font = QFont("-apple-system, Segoe UI, sans-serif", max(6, int(7 * max(0.85, self._zoom))))
        painter.setFont(type_font)
        painter.setPen(QColor(COLOR_TEXT_MUTED))
        type_rect = QRectF(rect.left() + 8, rect.top() + 21, rect.width() - 16, 13)
        painter.drawText(type_rect, Qt.AlignLeft | Qt.AlignVCenter, f"[{task.task_type}]")

        # Status text & duration
        status_font = QFont("-apple-system, Segoe UI, sans-serif", max(6, int(7 * max(0.85, self._zoom))), QFont.DemiBold)
        painter.setFont(status_font)
        painter.setPen(text_color)
        status_rect = QRectF(rect.left() + 8, rect.top() + 35, rect.width() - 16, 13)
        status_str = task.status.value.upper()
        if task.duration_s > 0:
            status_str += f" ({task.duration_s * 1000:.0f}ms)"
        elif task.retry_count > 0:
            status_str += f" (R:{task.retry_count})"
        painter.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter, status_str)
