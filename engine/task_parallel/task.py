"""Task Model and Status State Machine for Task Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Set


class TaskStatus(str, Enum):
    """Execution lifecycle statuses for a task."""
    PENDING = "pending"        # Initial state before graph readiness evaluation
    READY = "ready"            # All prerequisites satisfied; eligible for queueing
    QUEUED = "queued"          # Placed in dispatch queue awaiting an idle worker
    RUNNING = "running"        # Currently executing in a child worker process
    COMPLETED = "completed"    # Successfully executed and verified
    FAILED = "failed"          # Execution threw exception or retries exhausted
    CANCELLED = "cancelled"    # Cancelled before or during execution
    BLOCKED = "blocked"        # Blocked due to unfinished or failed prerequisite tasks


class TaskPriority(int, Enum):
    """Standard priority levels for task scheduling."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


# Valid state transitions ensuring safe and deterministic lifecycle management
VALID_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.READY},  # Allowed only when eligible for retry
    TaskStatus.COMPLETED: set(),           # Terminal state
    TaskStatus.CANCELLED: set(),           # Terminal state
}


@dataclass
class Task:
    """Individual unit of computation within a Task Parallel DAG."""
    task_id: str
    name: str
    task_type: str
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = TaskPriority.NORMAL
    dependencies: List[str] = field(default_factory=list)
    estimated_duration_s: float = 0.0

    # Lifecycle state
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.perf_counter)
    started_at: float = 0.0
    completed_at: float = 0.0
    duration_s: float = 0.0

    # Telemetry and process mapping
    assigned_worker_id: int = -1
    worker_pid: int = 0
    result: Any = None
    error_message: Optional[str] = None

    # Fault tolerance
    retry_count: int = 0
    max_retries: int = 0

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if transition from current status to new_status is valid."""
        if new_status == self.status:
            return True
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: TaskStatus, reason: Optional[str] = None) -> bool:
        """Enforce safe state machine transitions with timestamp tracking."""
        if new_status == self.status:
            return True

        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid task status transition for task '{self.task_id}': "
                f"cannot move from {self.status.value} to {new_status.value}."
            )

        self.status = new_status

        # Timestamp updates
        now = time.perf_counter()
        if new_status == TaskStatus.RUNNING:
            self.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.completed_at = now
            if self.started_at > 0:
                self.duration_s = max(0.0, self.completed_at - self.started_at)
            if reason and not self.error_message:
                self.error_message = reason

        return True

    def is_terminal(self) -> bool:
        """Return True if task has reached a final state (COMPLETED, FAILED, CANCELLED)."""
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    def is_ready(self) -> bool:
        """Return True if task is ready to be dispatched."""
        return self.status == TaskStatus.READY

    def to_dict(self) -> Dict[str, Any]:
        """Serialize task metadata for telemetry and UI visualization."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "priority": self.priority,
            "dependencies": list(self.dependencies),
            "status": self.status.value,
            "duration_s": self.duration_s,
            "assigned_worker_id": self.assigned_worker_id,
            "worker_pid": self.worker_pid,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
        }

