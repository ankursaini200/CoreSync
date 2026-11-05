"""Background QThread execution coordinator for Task Parallelism DAG workflows."""

import logging
import multiprocessing as mp
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal

from engine.task_parallel.executor import TaskParallelExecutor
from engine.task_parallel.task import Task, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from engine.task_parallel.task_queue import SchedulingPolicy

logger = logging.getLogger("CoreSync.GUI.TaskParallelRunner")


class TaskParallelRunnerThread(QThread):
    """Executes TaskGraph workflows in a background thread to prevent UI freezing."""

    task_status_changed = Signal(str, str, str, str, str)  # (task_id, status, error, pid_str, duration_str)
    worker_status_changed = Signal(int, int, str)          # (worker_id, pid, status_msg)
    progress_updated = Signal(int, int, str)              # (completed_tasks, total_tasks, status_msg)
    dag_finished = Signal(object)                         # TaskDAGResult
    dag_failed = Signal(str)                              # error_msg

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._graph: Optional[TaskGraph] = None
        self._worker_count: int = 4
        self._policy: SchedulingPolicy = SchedulingPolicy.FIFO
        self._cancel_event = mp.get_context("spawn").Event()
        self._executor = TaskParallelExecutor()

    def configure(
        self,
        graph: TaskGraph,
        worker_count: int,
        policy: SchedulingPolicy = SchedulingPolicy.FIFO,
    ) -> None:
        """Set execution parameters before starting thread."""
        self._graph = graph
        self._worker_count = worker_count
        self._policy = policy
        self._cancel_event.clear()

    def cancel(self) -> None:
        """Signal cancellation to executor and workers."""
        self._cancel_event.set()
        self._executor.cancel_active_execution()

    def run(self) -> None:
        """Run DAG execution in background thread."""
        if not self._graph:
            self.dag_failed.emit("No TaskGraph configured.")
            return

        try:
            def on_task_status(task: Task, status: TaskStatus, reason: Optional[str]):
                dur_str = f"{task.duration_s * 1000:.1f}ms" if task.duration_s > 0 else "--"
                pid_str = f"PID {task.worker_pid}" if task.worker_pid > 0 else "Pending"
                err_str = reason or task.error_message or ""
                self.task_status_changed.emit(task.task_id, status.value, err_str, pid_str, dur_str)

            def on_worker_status(w_id: int, pid: int, msg: str):
                self.worker_status_changed.emit(w_id, pid, msg)

            def on_progress(completed: int, total: int, msg: str):
                self.progress_updated.emit(completed, total, msg)

            result = self._executor.run_dag(
                graph=self._graph,
                worker_count=self._worker_count,
                policy=self._policy,
                task_status_callback=on_task_status,
                worker_status_callback=on_worker_status,
                progress_callback=on_progress,
                cancel_event=self._cancel_event,
            )

            if self._cancel_event.is_set():
                self.dag_failed.emit("Task execution was cancelled by user.")
            else:
                self.dag_finished.emit(result)

        except Exception as e:
            logger.error(f"Error executing DAG workflow: {e}", exc_info=True)
            self.dag_failed.emit(f"Execution Error: {str(e)}")

