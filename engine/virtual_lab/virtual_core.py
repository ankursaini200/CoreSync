"""Virtual processor core model and execution state simulation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from engine.virtual_lab.virtual_task import TaskState, VirtualTask


class VirtualCoreType(Enum):
    """Virtual core architectural specialization."""
    STANDARD = "Standard Core"
    PERFORMANCE = "Virtual P-Core"
    EFFICIENCY = "Virtual E-Core"


class VirtualCoreState(Enum):
    """Operational state of a virtual core."""
    IDLE = "Idle"
    BUSY = "Busy"
    PAUSED = "Paused"


@dataclass
class VirtualCore:
    """Simulated processor core executing assigned virtual tasks."""
    core_id: int
    core_type: VirtualCoreType = VirtualCoreType.STANDARD
    speed_multiplier: float = 1.0  # Relative computational throughput (e.g., 1.5x for P-Core, 0.8x for E-Core)
    state: VirtualCoreState = VirtualCoreState.IDLE
    current_task: Optional[VirtualTask] = None
    busy_ticks: int = 0
    total_ticks: int = 0
    simulated_utilization: float = 0.0

    def assign_task(self, task: VirtualTask, current_tick: int) -> None:
        """Assign a task to this core for execution."""
        self.current_task = task
        self.state = VirtualCoreState.BUSY
        task.state = TaskState.RUNNING
        task.assigned_core_id = self.core_id
        if task.start_tick is None:
            task.start_tick = current_tick

    def step(self, tick_delta: int = 1, current_tick: int = 0) -> Optional[VirtualTask]:
        """Advance execution on this core by tick_delta units.

        Returns:
            The finished VirtualTask if completed, or None if still executing or idle.
        """
        self.total_ticks += tick_delta

        if self.state != VirtualCoreState.BUSY or not self.current_task:
            self.state = VirtualCoreState.IDLE
            self._update_utilization()
            return None

        # Core is busy executing current task
        self.busy_ticks += tick_delta
        work_done = int(round(tick_delta * self.speed_multiplier))
        self.current_task.remaining_ticks -= max(1, work_done)

        # Check for task completion
        if self.current_task.remaining_ticks <= 0:
            finished = self.current_task
            finished.remaining_ticks = 0
            finished.state = TaskState.COMPLETED
            finished.finish_tick = current_tick
            self.current_task = None
            self.state = VirtualCoreState.IDLE
            self._update_utilization()
            return finished

        self._update_utilization()
        return None

    def preempt_task(self) -> Optional[VirtualTask]:
        """Preempt the current task back to ready state (for Round Robin / Priority)."""
        if self.current_task and self.state == VirtualCoreState.BUSY:
            task = self.current_task
            task.state = TaskState.READY
            task.assigned_core_id = None
            self.current_task = None
            self.state = VirtualCoreState.IDLE
            return task
        return None

    def _update_utilization(self) -> None:
        """Update recent simulated utilization percentage."""
        if self.total_ticks > 0:
            # Exponential moving average / windowed ratio
            self.simulated_utilization = (self.busy_ticks / self.total_ticks) * 100.0
        else:
            self.simulated_utilization = 0.0

