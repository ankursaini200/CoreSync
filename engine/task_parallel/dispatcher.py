"""Task Dispatcher and Worker Pool Availability Tracker.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from engine.task_parallel.task import Task
from engine.task_parallel.task_queue import SchedulingPolicy, TaskQueue
from utils.system_info import get_system_summary

logger = logging.getLogger("CoreSync.TaskParallel.Dispatcher")


class TaskDispatcher:
    """Manages queue dispatching, worker availability, and task-worker assignments."""

    def __init__(
        self,
        worker_count: int,
        policy: SchedulingPolicy = SchedulingPolicy.FIFO,
    ):
        self.worker_count = max(1, worker_count)
        self.queue = TaskQueue(policy=policy)
        self.idle_workers: Set[int] = set(range(self.worker_count))
        self.busy_workers: Dict[int, str] = {}  # worker_id -> task_id
        self.worker_pids: Dict[int, int] = {}   # worker_id -> OS PID

    @staticmethod
    def determine_automatic_workers() -> int:
        """Determine optimal worker count based on host hardware.

        Reserves 1 logical core for the OS and GUI to prevent UI starvation,
        clamping between 2 and detected logical cores.
        """
        summary = get_system_summary()
        logical = summary.logical_cores or 4
        if logical <= 2:
            return logical
        return max(2, logical - 1)

    def register_worker_pid(self, worker_id: int, pid: int) -> None:
        """Associate spawned worker ID with its actual operating system PID."""
        self.worker_pids[worker_id] = pid

    def has_idle_worker(self) -> bool:
        """Return True if at least one worker process is available for dispatch."""
        return len(self.idle_workers) > 0

    def dispatch_next(self) -> Optional[Tuple[Task, int]]:
        """If an idle worker and queued task exist, assign and return (task, worker_id)."""
        if not self.has_idle_worker() or self.queue.is_empty():
            return None

        task = self.queue.pop()
        if not task:
            return None

        # Pick the lowest numbered idle worker ID for deterministic assignment
        worker_id = min(self.idle_workers)
        self.idle_workers.remove(worker_id)
        self.busy_workers[worker_id] = task.task_id

        task.assigned_worker_id = worker_id
        if worker_id in self.worker_pids:
            task.worker_pid = self.worker_pids[worker_id]

        return task, worker_id

    def on_worker_finished(self, worker_id: int, task_id: str) -> None:
        """Mark a worker as idle and ready for subsequent task assignments."""
        if worker_id in self.busy_workers:
            del self.busy_workers[worker_id]
        self.idle_workers.add(worker_id)

    def reset(self, new_worker_count: Optional[int] = None) -> None:
        """Reset dispatcher state and re-initialize idle worker pool."""
        if new_worker_count is not None and new_worker_count > 0:
            self.worker_count = new_worker_count
        self.queue.clear()
        self.idle_workers = set(range(self.worker_count))
        self.busy_workers.clear()
        self.worker_pids.clear()

