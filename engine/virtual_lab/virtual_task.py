"""Virtual task definitions and lifecycle states for the Virtual Lab."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskPriority(Enum):
    """Educational scheduling task priorities."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3

    @property
    def label(self) -> str:
        return self.name.capitalize()


class TaskState(Enum):
    """Lifecycle states of a simulated virtual task."""
    READY = "Ready"
    RUNNING = "Running"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PAUSED = "Paused"


@dataclass
class VirtualTask:
    """Represents an independent simulated compute task in the Virtual Lab."""
    task_id: int
    name: str
    workload_type: str = "Numerical Compute"
    total_ticks: int = 100
    remaining_ticks: Optional[int] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    state: TaskState = TaskState.READY
    assigned_core_id: Optional[int] = None
    arrival_tick: int = 0
    start_tick: Optional[int] = None
    finish_tick: Optional[int] = None
    waiting_ticks: int = 0
    burst_ticks: Optional[int] = None

    def __post_init__(self):
        if self.burst_ticks is not None:
            self.total_ticks = self.burst_ticks
        elif self.total_ticks is not None:
            self.burst_ticks = self.total_ticks
        if self.remaining_ticks is None:
            self.remaining_ticks = self.total_ticks

    @property
    def completion_tick(self) -> Optional[int]:
        return self.finish_tick

    @property
    def progress_pct(self) -> float:
        if self.total_ticks <= 0:
            return 100.0
        done = self.total_ticks - self.remaining_ticks
        return max(0.0, min((done / self.total_ticks) * 100.0, 100.0))

    @property
    def turnaround_ticks(self) -> Optional[int]:
        if self.finish_tick is not None:
            return self.finish_tick - self.arrival_tick
        return None
