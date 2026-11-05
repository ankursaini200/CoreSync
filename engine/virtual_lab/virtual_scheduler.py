"""Virtual Lab Educational Task Scheduler."""

from collections import deque
from enum import Enum
import logging
from typing import Deque, Dict, List, Optional

from engine.virtual_lab.virtual_core import VirtualCoreState
from engine.virtual_lab.virtual_cpu import VirtualCPU
from engine.virtual_lab.virtual_task import TaskPriority, TaskState, VirtualTask

logger = logging.getLogger("CoreSync.VirtualScheduler")


class SchedulingAlgorithm(Enum):
    """Educational scheduling algorithm policies."""
    FCFS = "First Come First Served"
    PRIORITY = "Priority Scheduling"
    ROUND_ROBIN = "Round Robin"


class VirtualScheduler:
    """Dispatches virtual tasks onto virtual cores according to selected scheduling policy."""

    def __init__(
        self,
        virtual_cpu: VirtualCPU,
        algorithm: SchedulingAlgorithm = SchedulingAlgorithm.FCFS,
        time_quantum: int = 20,
    ):
        self.virtual_cpu = virtual_cpu
        self.algorithm = algorithm
        self.time_quantum = time_quantum

        self.ready_queue: Deque[VirtualTask] = deque()
        self.completed_tasks: List[VirtualTask] = []
        self.failed_tasks: List[VirtualTask] = []
        self._task_quantum_remaining: Dict[int, int] = {}  # core_id -> remaining quantum

    def submit_task(self, task: VirtualTask) -> None:
        """Add a new task to the ready queue."""
        task.state = TaskState.READY
        task.arrival_tick = self.virtual_cpu.current_tick
        self._insert_ready(task)

    def submit_batch(self, tasks: List[VirtualTask]) -> None:
        """Submit a batch of virtual tasks."""
        for t in tasks:
            self.submit_task(t)

    def _insert_ready(self, task: VirtualTask) -> None:
        """Insert task into ready queue according to policy."""
        if self.algorithm == SchedulingAlgorithm.PRIORITY:
            # Lower numeric value = higher priority (HIGH=1, MEDIUM=2, LOW=3)
            # Insert maintaining priority order
            temp = list(self.ready_queue)
            temp.append(task)
            temp.sort(key=lambda t: (t.priority.value, t.arrival_tick))
            self.ready_queue = deque(temp)
        else:
            self.ready_queue.append(task)

    def dispatch(self) -> None:
        """Assign ready tasks to available idle virtual cores."""
        idle_cores = self.virtual_cpu.get_idle_cores()

        while idle_cores and self.ready_queue:
            core = idle_cores.pop(0)
            task = self.ready_queue.popleft()
            core.assign_task(task, current_tick=self.virtual_cpu.current_tick)
            if self.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
                self._task_quantum_remaining[core.core_id] = self.time_quantum

    def step(self, tick_delta: int = 1) -> List[VirtualTask]:
        """Advance simulation clock, handle preemption, and track task states.

        Returns:
            List of tasks completed in this step.
        """
        # Advance waiting time for tasks still in ready queue
        for task in self.ready_queue:
            task.waiting_ticks += tick_delta

        # Check Round Robin quantum expiration before stepping
        if self.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
            for core in list(self.virtual_cpu.cores.values()):
                if core.state == VirtualCoreState.BUSY and core.current_task:
                    cid = core.core_id
                    rem_q = self._task_quantum_remaining.get(cid, self.time_quantum) - tick_delta
                    if rem_q <= 0 and core.current_task.remaining_ticks > tick_delta:
                        # Time quantum expired: preempt task back to ready queue
                        preempted = core.preempt_task()
                        if preempted:
                            self.ready_queue.append(preempted)
                            self._task_quantum_remaining.pop(cid, None)
                    else:
                        self._task_quantum_remaining[cid] = rem_q

        # Advance cores
        finished_tasks = self.virtual_cpu.step(tick_delta=tick_delta)
        for t in finished_tasks:
            self.completed_tasks.append(t)
            if t.assigned_core_id is not None and t.assigned_core_id in self._task_quantum_remaining:
                self._task_quantum_remaining.pop(t.assigned_core_id, None)

        # Dispatch newly idle cores
        self.dispatch()
        return finished_tasks

    @property
    def avg_waiting_time(self) -> float:
        """Calculate average waiting time of completed tasks."""
        if not self.completed_tasks:
            return 0.0
        return sum(t.waiting_ticks for t in self.completed_tasks) / len(self.completed_tasks)

    @property
    def avg_turnaround_time(self) -> float:
        """Calculate average turnaround time of completed tasks."""
        if not self.completed_tasks:
            return 0.0
        turnarounds = [t.turnaround_ticks for t in self.completed_tasks if t.turnaround_ticks is not None]
        return (sum(turnarounds) / len(turnarounds)) if turnarounds else 0.0

    def reset(self) -> None:
        """Clear all queues and reset virtual CPU."""
        self.ready_queue.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self._task_quantum_remaining.clear()
        self.virtual_cpu.reset_metrics()

