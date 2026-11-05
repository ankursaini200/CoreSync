"""Task Queue with Pluggable Scheduling Policies (FIFO, Priority, SJF).

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from enum import Enum
import heapq
import time
from typing import Any, List, Optional

from engine.task_parallel.task import Task, TaskStatus


class SchedulingPolicy(str, Enum):
    """Supported scheduling strategies for task dispatching."""
    FIFO = "fifo"          # First-Come, First-Served based on enqueue timestamp
    PRIORITY = "priority"  # Highest priority first (higher integer = higher priority)
    SJF = "sjf"            # Shortest Job First based on estimated duration


class TaskQueue:
    """Task queue ordering ready tasks according to the configured scheduling policy."""

    def __init__(self, policy: SchedulingPolicy = SchedulingPolicy.FIFO):
        self.policy = policy
        # Internal list of tuples: (priority_key, enqueue_counter, task)
        self._heap: List[Any] = []
        self._counter: int = 0  # Monotonic sequence counter for stable tie-breaking

    def set_policy(self, policy: SchedulingPolicy) -> None:
        """Update scheduling policy and re-order the existing queued tasks."""
        if policy == self.policy:
            return
        tasks = [item[2] for item in self._heap]
        self.policy = policy
        self._heap.clear()
        self._counter = 0
        for task in tasks:
            self.push(task, update_status=False)

    def _make_key(self, task: Task) -> Any:
        """Generate sort key for heapq (min-heap)."""
        if self.policy == SchedulingPolicy.FIFO:
            # Min-heap on arrival order
            return self._counter
        elif self.policy == SchedulingPolicy.PRIORITY:
            # Min-heap, so invert priority (-priority) so highest priority pops first
            return -task.priority
        elif self.policy == SchedulingPolicy.SJF:
            # Smallest estimated duration first; if 0, put at end or treat as neutral
            est = task.estimated_duration_s if task.estimated_duration_s > 0 else 9999.0
            return (est, -task.priority)
        else:
            return self._counter

    def push(self, task: Task, update_status: bool = True) -> None:
        """Enqueue a task and transition its status to QUEUED if requested."""
        if update_status and task.status == TaskStatus.READY:
            task.transition_to(TaskStatus.QUEUED)

        key = self._make_key(task)
        heapq.heappush(self._heap, (key, self._counter, task))
        self._counter += 1

    def pop(self) -> Optional[Task]:
        """Pop and return the highest-ranked task according to policy, or None if empty."""
        if not self._heap:
            return None
        _, _, task = heapq.heappop(self._heap)
        return task

    def peek(self) -> Optional[Task]:
        """Inspect the top task without removing it."""
        if not self._heap:
            return None
        return self._heap[0][2]

    def remove(self, task_id: str) -> Optional[Task]:
        """Remove a specific task by ID (e.g. on cancellation)."""
        target_idx = -1
        for idx, (_, _, task) in enumerate(self._heap):
            if task.task_id == task_id:
                target_idx = idx
                break

        if target_idx == -1:
            return None

        _, _, removed_task = self._heap.pop(target_idx)
        heapq.heapify(self._heap)
        return removed_task

    def size(self) -> int:
        """Return count of tasks currently in queue."""
        return len(self._heap)

    def is_empty(self) -> bool:
        """Return True if queue has no tasks."""
        return len(self._heap) == 0

    def get_all_tasks(self) -> List[Task]:
        """Return shallow list of tasks currently queued."""
        return [item[2] for item in self._heap]

    def clear(self) -> None:
        """Purge all tasks from queue."""
        self._heap.clear()
        self._counter = 0

