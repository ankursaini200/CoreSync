"""Interactive DAG Dependency Graph Visualization Canvas."""

import math
from typing import Dict, List, Optional, Set, Tuple
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


STATUS_COLORS = {
    TaskStatus.PENDING: (QColor("#161b22"), QColor("#30363d"), QColor("#8b949e")),
    TaskStatus.BLOCKED: (QColor("#161b22"), QColor("#30363d"), QColor("#6e7681")),
    TaskStatus.READY: (QColor("#2d2206"), QColor("#d29922"), QColor("#e3b341")),
    TaskStatus.QUEUED: (QColor("#3d2007"), QColor("#db6d28"), QColor("#ffa657")),
    TaskStatus.RUNNING: (QColor("#0c2d6b"), QColor("#58a6ff"), QColor("#79c0ff")),
    TaskStatus.COMPLETED: (QColor("#0e4429"), QColor("#3fb950"), QColor("#56d364")),
    TaskStatus.FAILED: (QColor("#490202"), QColor("#f85149"), QColor("#ff7b72")),
    TaskStatus.CANCELLED: (QColor("#21262d"), QColor("#6e7681"), QColor("#8b949e")),
}


class DAGCanvasWidget(QWidget):
    """Custom QPainter widget rendering DAG nodes and dependency edges in real-time."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._graph: Optional[TaskGraph] = None
        self._node_positions: Dict[str, QRectF] = {}
        self.setMinimumHeight(280)
        self.setStyleSheet("background-color: #0d1117; border-radius: 8px;")

    def set_graph(self, graph: Optional[TaskGraph]) -> None:
        """Bind graph and recompute layout."""
        self._graph = graph
        self._compute_layout()
        self.update()

    def update_task_state(self, task_id: str) -> None:
        """Trigger canvas repaint on task status changes."""
        self.update()

    def _compute_layout(self) -> None:
        """Calculate layered left-to-right topological layout coordinates."""
        self._node_positions.clear()
        if not self._graph or not self._graph.tasks:
            return

        # 1. Compute layer (depth) for each node using topological sort / DFS
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
        node_w = 170.0
        node_h = 58.0
        col_gap = 60.0
        row_gap = 18.0
        left_margin = 28.0
        top_margin = 24.0

        max_layer = max(nodes_by_layer.keys()) if nodes_by_layer else 0
        max_rows = max(len(col) for col in nodes_by_layer.values()) if nodes_by_layer else 1

        total_width = left_margin * 2 + (max_layer + 1) * (node_w + col_gap)
        total_height = top_margin * 2 + max_rows * (node_h + row_gap)
        self.setMinimumSize(int(total_width), max(280, int(total_height)))

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
        painter.fillRect(self.rect(), QColor("#0d1117"))

        if not self._graph or not self._node_positions:
            painter.setPen(QColor("#8b949e"))
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
            edge_color = QColor("#238636")
        elif p_task and p_task.status == TaskStatus.RUNNING:
            edge_color = QColor("#388bfd")
        elif p_task and p_task.status == TaskStatus.FAILED:
            edge_color = QColor("#da3633")
        else:
            edge_color = QColor("#30363d")

        pen = QPen(edge_color, 2.0, Qt.SolidLine)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(start)
        dx = (end.x() - start.x()) * 0.5
        c1 = QPointF(start.x() + dx, start.y())
        c2 = QPointF(end.x() - dx, end.y())
        path.cubicTo(c1, c2, end)
        painter.drawPath(path)

        # Draw arrowhead
        arrow_size = 7.0
        arrow = QPolygonF([
            end,
            QPointF(end.x() - arrow_size * 1.5, end.y() - arrow_size),
            QPointF(end.x() - arrow_size * 1.5, end.y() + arrow_size),
        ])
        painter.setBrush(QBrush(edge_color))
        painter.drawPolygon(arrow)

    def _draw_node(self, painter: QPainter, rect: QRectF, task: Task) -> None:
        """Draw rounded task card with status badge and metadata."""
        bg_color, border_color, text_color = STATUS_COLORS.get(
            task.status,
            (QColor("#161b22"), QColor("#30363d"), QColor("#8b949e")),
        )

        # Card shadow / background
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        # Title text
        painter.setPen(QColor("#f0f6fc"))
        title_font = QFont("Sans-Serif", 8, QFont.Bold)
        painter.setFont(title_font)
        title_rect = QRectF(rect.left() + 8, rect.top() + 6, rect.width() - 16, 16)
        # Elide title if too long
        title_text = task.name if len(task.name) <= 22 else (task.name[:20] + "…")
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, title_text)

        # Type badge
        type_font = QFont("Monospace", 7)
        painter.setFont(type_font)
        painter.setPen(QColor("#8b949e"))
        type_rect = QRectF(rect.left() + 8, rect.top() + 23, rect.width() - 16, 14)
        painter.drawText(type_rect, Qt.AlignLeft | Qt.AlignVCenter, f"[{task.task_type}]")

        # Status text & duration
        status_font = QFont("Sans-Serif", 7, QFont.Bold)
        painter.setFont(status_font)
        painter.setPen(text_color)
        status_rect = QRectF(rect.left() + 8, rect.top() + 38, rect.width() - 16, 14)
        status_str = task.status.value.upper()
        if task.duration_s > 0:
            status_str += f" ({task.duration_s * 1000:.0f}ms)"
        elif task.retry_count > 0:
            status_str += f" (R:{task.retry_count})"
        painter.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter, status_str)

