"""CPU Scheduling Algorithms for CoreSync Process Scheduler.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Implements classical CPU scheduling policies:
    - First Come First Serve (FCFS)
    - Shortest Job First (SJF - Non-Preemptive)
    - Shortest Remaining Time First (SRTF - Preemptive SJF)
    - Priority Scheduling (Non-Preemptive & Preemptive with Aging)
    - Round Robin (RR - Time Sliced with Preemption & Context Switch Overhead)
"""

from abc import ABC, abstractmethod
from collections import deque
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple

from engine.process_scheduler.models import (
    PriorityDirection,
    Process,
    ProcessState,
    validate_context_switch,
    validate_process_list,
    validate_quantum,
)
from engine.process_scheduler.timeline import SchedulingTimeline


class AlgorithmType(str, Enum):
    """Supported CPU scheduling algorithm types."""
    FCFS = "fcfs"
    SJF = "sjf"
    SRTF = "srtf"
    PRIORITY_NON_PREEMPTIVE = "priority_non_preemptive"
    PRIORITY_PREEMPTIVE = "priority_preemptive"
    ROUND_ROBIN = "round_robin"

    @property
    def display_name(self) -> str:
        names = {
            AlgorithmType.FCFS: "First Come First Serve (FCFS)",
            AlgorithmType.SJF: "Shortest Job First (SJF - Non-Preemptive)",
            AlgorithmType.SRTF: "Shortest Remaining Time First (SRTF - Preemptive)",
            AlgorithmType.PRIORITY_NON_PREEMPTIVE: "Priority Scheduling (Non-Preemptive)",
            AlgorithmType.PRIORITY_PREEMPTIVE: "Priority Scheduling (Preemptive)",
            AlgorithmType.ROUND_ROBIN: "Round Robin (RR)",
        }
        return names.get(self, self.value)


class BaseScheduler(ABC):
    """Abstract base class for CPU scheduling algorithm implementations."""

    def __init__(
        self,
        context_switch_overhead: float = 0.0,
    ):
        validate_context_switch(context_switch_overhead)
        self.context_switch_overhead = float(context_switch_overhead)

    @abstractmethod
    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        """Execute the scheduling policy on a list of processes.

        Args:
            processes: Input list of Process instances.

        Returns:
            Tuple of (completed_processes_list, execution_timeline).
        """
        pass


class FCFSScheduler(BaseScheduler):
    """First-Come, First-Served (FCFS) CPU scheduling algorithm (Non-Preemptive)."""

    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        validate_process_list(processes)
        # Clone processes so caller input is untouched
        procs = [p.clone() for p in processes]
        # Sort by arrival time, tie-breaking by process_id
        procs.sort(key=lambda p: (p.arrival_time, p.process_id))

        timeline = SchedulingTimeline()
        current_time = 0.0
        last_pid: Optional[str] = None

        for p in procs:
            # Handle CPU idle interval if process has not arrived yet
            if p.arrival_time > current_time:
                timeline.add_idle(current_time, p.arrival_time)
                current_time = p.arrival_time
                last_pid = None  # CPU was idle, no CS overhead from idle to process

            # Handle context switch overhead between distinct processes
            if self.context_switch_overhead > 0 and last_pid is not None and last_pid != p.process_id:
                cs_end = current_time + self.context_switch_overhead
                timeline.add_context_switch(current_time, cs_end, from_pid=last_pid, to_pid=p.process_id)
                current_time = cs_end

            # First start time
            p.start_time = current_time
            p.state = ProcessState.RUNNING

            burst_end = current_time + p.burst_time
            timeline.add_process_burst(
                process_id=p.process_id,
                start_time=current_time,
                end_time=burst_end,
                preempted=False,
                priority=p.priority,
            )

            current_time = burst_end
            p.remaining_time = 0.0
            p.completion_time = current_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
            p.response_time = max(0.0, p.start_time - p.arrival_time) if p.start_time is not None else 0.0
            p.state = ProcessState.COMPLETED
            last_pid = p.process_id

        return procs, timeline


class SJFScheduler(BaseScheduler):
    """Shortest Job First (SJF) CPU scheduling algorithm (Non-Preemptive)."""

    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        validate_process_list(processes)
        procs = [p.clone() for p in processes]
        n = len(procs)

        timeline = SchedulingTimeline()
        current_time = 0.0
        last_pid: Optional[str] = None
        completed_count = 0

        while completed_count < n:
            # Find arrived and unfinished processes
            available = [p for p in procs if p.arrival_time <= current_time and not p.is_completed]

            if not available:
                # CPU is idle: jump to earliest arrival of remaining processes
                remaining = [p for p in procs if not p.is_completed]
                next_arr = min(p.arrival_time for p in remaining)
                timeline.add_idle(current_time, next_arr)
                current_time = next_arr
                last_pid = None
                continue

            # Pick process with smallest burst time; tie-break: arrival time, then process_id
            selected = min(available, key=lambda p: (p.burst_time, p.arrival_time, p.process_id))

            # Context switch overhead
            if self.context_switch_overhead > 0 and last_pid is not None and last_pid != selected.process_id:
                cs_end = current_time + self.context_switch_overhead
                timeline.add_context_switch(current_time, cs_end, from_pid=last_pid, to_pid=selected.process_id)
                current_time = cs_end

            if selected.start_time is None:
                selected.start_time = current_time

            selected.state = ProcessState.RUNNING
            burst_end = current_time + selected.burst_time
            timeline.add_process_burst(
                process_id=selected.process_id,
                start_time=current_time,
                end_time=burst_end,
                preempted=False,
                priority=selected.priority,
            )

            current_time = burst_end
            selected.remaining_time = 0.0
            selected.completion_time = current_time
            selected.state = ProcessState.COMPLETED
            completed_count += 1
            last_pid = selected.process_id

        # Return in original input order
        for p in procs:
            if p.completion_time is not None:
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
                p.response_time = max(0.0, p.start_time - p.arrival_time) if p.start_time is not None else 0.0

        proc_map = {p.process_id: p for p in procs}
        return [proc_map[orig.process_id] for orig in processes], timeline


class SRTFScheduler(BaseScheduler):
    """Shortest Remaining Time First (SRTF) CPU scheduling algorithm (Preemptive SJF)."""

    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        validate_process_list(processes)
        procs = [p.clone() for p in processes]
        n = len(procs)

        timeline = SchedulingTimeline()
        current_time = 0.0
        last_pid: Optional[str] = None
        completed_count = 0

        while completed_count < n:
            available = [p for p in procs if p.arrival_time <= current_time and not p.is_completed]

            if not available:
                remaining = [p for p in procs if not p.is_completed]
                next_arr = min(p.arrival_time for p in remaining)
                timeline.add_idle(current_time, next_arr)
                current_time = next_arr
                last_pid = None
                continue

            # Pick process with shortest remaining time; tie-break: arrival time, then PID
            selected = min(available, key=lambda p: (p.remaining_time, p.arrival_time, p.process_id))

            # Context switch overhead
            if self.context_switch_overhead > 0 and last_pid is not None and last_pid != selected.process_id:
                cs_end = current_time + self.context_switch_overhead
                timeline.add_context_switch(current_time, cs_end, from_pid=last_pid, to_pid=selected.process_id)
                current_time = cs_end
                # Re-query available processes in case arrivals happened during context switch
                available = [p for p in procs if p.arrival_time <= current_time and not p.is_completed]
                selected = min(available, key=lambda p: (p.remaining_time, p.arrival_time, p.process_id))

            if selected.start_time is None:
                selected.start_time = current_time

            selected.state = ProcessState.RUNNING

            # Determine run duration: run until completion or next future arrival
            future_arrivals = [p.arrival_time for p in procs if p.arrival_time > current_time and not p.is_completed]

            if future_arrivals:
                next_arrival = min(future_arrivals)
                time_to_arrival = next_arrival - current_time
                step_duration = min(selected.remaining_time, time_to_arrival)
            else:
                step_duration = selected.remaining_time

            step_end = current_time + step_duration
            selected.remaining_time = max(0.0, selected.remaining_time - step_duration)

            # Check if preempted by a newly arrived job at step_end
            preempted = False
            if selected.remaining_time > 1e-9:
                # Check if newly arrived processes at step_end have strictly shorter remaining time
                newly_available = [p for p in procs if p.arrival_time <= step_end and not p.is_completed]
                best_at_end = min(newly_available, key=lambda p: (p.remaining_time, p.arrival_time, p.process_id))
                if best_at_end.process_id != selected.process_id:
                    preempted = True
                    selected.state = ProcessState.READY

            timeline.add_process_burst(
                process_id=selected.process_id,
                start_time=current_time,
                end_time=step_end,
                preempted=preempted,
                priority=selected.priority,
            )

            current_time = step_end

            if selected.remaining_time <= 1e-9:
                selected.remaining_time = 0.0
                selected.completion_time = current_time
                selected.state = ProcessState.COMPLETED
                completed_count += 1

            last_pid = selected.process_id

        for p in procs:
            if p.completion_time is not None:
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
                p.response_time = max(0.0, p.start_time - p.arrival_time) if p.start_time is not None else 0.0

        proc_map = {p.process_id: p for p in procs}
        return [proc_map[orig.process_id] for orig in processes], timeline


class PriorityScheduler(BaseScheduler):
    """Priority-based CPU scheduling algorithm supporting Preemptive & Non-Preemptive modes,
    configurable priority direction, and exact per-process priority aging to prevent starvation.
    """

    def __init__(
        self,
        preemptive: bool = False,
        direction: PriorityDirection = PriorityDirection.LOWER_IS_HIGHER,
        enable_aging: bool = False,
        aging_interval: float = 5.0,
        context_switch_overhead: float = 0.0,
    ):
        super().__init__(context_switch_overhead=context_switch_overhead)
        self.preemptive = preemptive
        self.direction = direction
        self.enable_aging = enable_aging
        self.aging_interval = max(0.1, float(aging_interval))

    def _priority_sort_key(self, p: Process) -> Tuple[int, float, str]:
        """Generate sort key where smaller tuple element represents higher priority."""
        if self.direction == PriorityDirection.LOWER_IS_HIGHER:
            # Lower numeric value = higher priority
            p_val = p.current_priority
        else:
            # Higher numeric value = higher priority -> invert for min-sorting
            p_val = -p.current_priority
        return (p_val, p.arrival_time, p.process_id)

    def _update_process_priority(self, p: Process, ready_wait: float) -> None:
        """Update effective priority based strictly on completed aging intervals in ready queue."""
        if self.enable_aging and self.aging_interval > 0:
            steps = int(math.floor(ready_wait / self.aging_interval))
            if self.direction == PriorityDirection.LOWER_IS_HIGHER:
                p.current_priority = p.priority - steps
            else:
                p.current_priority = p.priority + steps
        else:
            p.current_priority = p.priority

    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        validate_process_list(processes)
        procs = [p.clone() for p in processes]
        n = len(procs)

        timeline = SchedulingTimeline()
        current_time = 0.0
        last_pid: Optional[str] = None
        completed_count = 0

        # Accumulated waiting time in ready queue for each process
        ready_wait_time: Dict[str, float] = {p.process_id: 0.0 for p in procs}

        # Helper to advance ready wait time for waiting processes during an interval [t_start, t_end]
        def advance_ready_wait(t_start: float, t_end: float, running_pid: Optional[str] = None):
            duration = t_end - t_start
            if duration <= 1e-9:
                return
            for p in procs:
                if p.is_completed:
                    continue
                if p.process_id == running_pid:
                    continue
                overlap_start = max(t_start, p.arrival_time)
                overlap_end = t_end
                if overlap_end > overlap_start:
                    ready_wait_time[p.process_id] += (overlap_end - overlap_start)
                    self._update_process_priority(p, ready_wait_time[p.process_id])

        while completed_count < n:
            available = [p for p in procs if p.arrival_time <= current_time and not p.is_completed]

            if not available:
                remaining = [p for p in procs if not p.is_completed]
                next_arr = min(p.arrival_time for p in remaining)
                timeline.add_idle(current_time, next_arr)
                current_time = next_arr
                last_pid = None
                continue

            selected = min(available, key=self._priority_sort_key)

            # Context switch overhead if switching between different processes
            if self.context_switch_overhead > 0 and last_pid is not None and last_pid != selected.process_id:
                cs_end = current_time + self.context_switch_overhead
                timeline.add_context_switch(current_time, cs_end, from_pid=last_pid, to_pid=selected.process_id)
                advance_ready_wait(current_time, cs_end, running_pid=None)
                current_time = cs_end
                available = [p for p in procs if p.arrival_time <= current_time and not p.is_completed]
                selected = min(available, key=self._priority_sort_key)

            if selected.start_time is None:
                selected.start_time = current_time

            selected.state = ProcessState.RUNNING

            if not self.preemptive:
                # Non-preemptive: executes burst until completion
                burst_end = current_time + selected.remaining_time
                timeline.add_process_burst(
                    process_id=selected.process_id,
                    start_time=current_time,
                    end_time=burst_end,
                    preempted=False,
                    priority=selected.current_priority,
                )
                advance_ready_wait(current_time, burst_end, running_pid=selected.process_id)
                current_time = burst_end
                selected.remaining_time = 0.0
                selected.completion_time = current_time
                selected.state = ProcessState.COMPLETED
                completed_count += 1
                last_pid = selected.process_id
            else:
                # Preemptive mode: determine time to next event
                # Event 1: Selected process finishes execution
                delta_events = [selected.remaining_time]

                # Event 2: Future process arrival
                future_arrivals = [p.arrival_time for p in procs if p.arrival_time > current_time and not p.is_completed]
                if future_arrivals:
                    delta_events.append(min(future_arrivals) - current_time)

                # Event 3: Aging step for any process in the ready queue
                if self.enable_aging and self.aging_interval > 0:
                    for p in procs:
                        if p.arrival_time <= current_time and not p.is_completed and p.process_id != selected.process_id:
                            w = ready_wait_time[p.process_id]
                            next_boundary = (math.floor(w / self.aging_interval) + 1) * self.aging_interval
                            time_to_aging = next_boundary - w
                            if time_to_aging > 1e-9:
                                delta_events.append(time_to_aging)

                step_duration = min(delta_events)
                step_end = current_time + step_duration
                selected.remaining_time = max(0.0, selected.remaining_time - step_duration)

                # Advance queue wait time for waiting processes
                advance_ready_wait(current_time, step_end, running_pid=selected.process_id)

                # Check if preempted at step_end
                preempted = False
                if selected.remaining_time > 1e-9:
                    newly_available = [p for p in procs if p.arrival_time <= step_end and not p.is_completed]
                    best_at_end = min(newly_available, key=self._priority_sort_key)
                    if best_at_end.process_id != selected.process_id:
                        preempted = True
                        selected.state = ProcessState.READY

                timeline.add_process_burst(
                    process_id=selected.process_id,
                    start_time=current_time,
                    end_time=step_end,
                    preempted=preempted,
                    priority=selected.current_priority,
                )

                current_time = step_end

                if selected.remaining_time <= 1e-9:
                    selected.remaining_time = 0.0
                    selected.completion_time = current_time
                    selected.state = ProcessState.COMPLETED
                    completed_count += 1

                last_pid = selected.process_id

        for p in procs:
            if p.completion_time is not None:
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
                p.response_time = max(0.0, p.start_time - p.arrival_time) if p.start_time is not None else 0.0

        proc_map = {p.process_id: p for p in procs}
        return [proc_map[orig.process_id] for orig in processes], timeline


class RoundRobinScheduler(BaseScheduler):
    """Round Robin (RR) CPU scheduling algorithm with configurable time quantum,
    proper context-switch overhead handling, and deterministic ready queue management.
    """

    def __init__(
        self,
        time_quantum: float = 2.0,
        context_switch_overhead: float = 0.0,
    ):
        super().__init__(context_switch_overhead=context_switch_overhead)
        validate_quantum(time_quantum)
        self.time_quantum = float(time_quantum)

    def schedule(self, processes: List[Process]) -> Tuple[List[Process], SchedulingTimeline]:
        validate_process_list(processes)
        procs = [p.clone() for p in processes]
        n = len(procs)

        timeline = SchedulingTimeline()
        current_time = 0.0
        last_pid: Optional[str] = None
        completed_count = 0

        # Ready queue holding processes currently waiting for CPU
        ready_queue: deque[Process] = deque()

        # Track which processes have already entered the ready queue
        enqueued_ids = set()

        # Helper to enqueue all processes that have arrived by `t`
        def enqueue_arrived(t: float):
            # Sort newly arrived processes by (arrival_time, process_id)
            newly_arrived = [
                p for p in procs
                if p.arrival_time <= t and p.process_id not in enqueued_ids and not p.is_completed
            ]
            newly_arrived.sort(key=lambda p: (p.arrival_time, p.process_id))
            for p in newly_arrived:
                p.state = ProcessState.READY
                ready_queue.append(p)
                enqueued_ids.add(p.process_id)

        # Initial enqueue at t=0
        enqueue_arrived(current_time)

        while completed_count < n:
            if not ready_queue:
                # CPU is idle: jump to next process arrival time
                remaining = [p for p in procs if not p.is_completed]
                next_arr = min(p.arrival_time for p in remaining)
                timeline.add_idle(current_time, next_arr)
                current_time = next_arr
                last_pid = None
                enqueue_arrived(current_time)
                continue

            # Pop next process from head of ready queue
            p = ready_queue.popleft()

            # Context switch overhead if switching between different processes
            if self.context_switch_overhead > 0 and last_pid is not None and last_pid != p.process_id:
                cs_end = current_time + self.context_switch_overhead
                timeline.add_context_switch(current_time, cs_end, from_pid=last_pid, to_pid=p.process_id)
                current_time = cs_end
                # Processes arriving during the context switch enter the ready queue
                enqueue_arrived(current_time)

            if p.start_time is None:
                p.start_time = current_time

            p.state = ProcessState.RUNNING

            # Time slice to execute
            slice_time = min(self.time_quantum, p.remaining_time)
            slice_end = current_time + slice_time
            p.remaining_time = max(0.0, p.remaining_time - slice_time)

            # Check completion vs preemption
            if p.remaining_time <= 1e-9:
                p.remaining_time = 0.0
                p.completion_time = slice_end
                p.state = ProcessState.COMPLETED
                completed_count += 1
                preempted = False

                timeline.add_process_burst(
                    process_id=p.process_id,
                    start_time=current_time,
                    end_time=slice_end,
                    preempted=preempted,
                    priority=p.priority,
                )
                current_time = slice_end
                # Enqueue all processes arriving up to slice_end
                enqueue_arrived(current_time)
            else:
                preempted = True
                p.state = ProcessState.READY
                timeline.add_process_burst(
                    process_id=p.process_id,
                    start_time=current_time,
                    end_time=slice_end,
                    preempted=preempted,
                    priority=p.priority,
                )
                current_time = slice_end
                # CRITICAL OS RULE: Arriving processes are enqueued BEFORE re-appending preempted process!
                enqueue_arrived(current_time)
                ready_queue.append(p)

            last_pid = p.process_id

        for p in procs:
            if p.completion_time is not None:
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
                p.response_time = max(0.0, p.start_time - p.arrival_time) if p.start_time is not None else 0.0

        proc_map = {p.process_id: p for p in procs}
        return [proc_map[orig.process_id] for orig in processes], timeline


class SchedulerFactory:
    """Factory creating scheduling algorithm instances based on algorithm type and parameters."""

    @staticmethod
    def create(
        algorithm_type: AlgorithmType,
        time_quantum: float = 2.0,
        direction: PriorityDirection = PriorityDirection.LOWER_IS_HIGHER,
        enable_aging: bool = False,
        aging_interval: float = 5.0,
        context_switch_overhead: float = 0.0,
    ) -> BaseScheduler:
        """Instantiate the requested scheduling algorithm with configured parameters."""
        if algorithm_type == AlgorithmType.FCFS:
            return FCFSScheduler(context_switch_overhead=context_switch_overhead)
        elif algorithm_type == AlgorithmType.SJF:
            return SJFScheduler(context_switch_overhead=context_switch_overhead)
        elif algorithm_type == AlgorithmType.SRTF:
            return SRTFScheduler(context_switch_overhead=context_switch_overhead)
        elif algorithm_type == AlgorithmType.PRIORITY_NON_PREEMPTIVE:
            return PriorityScheduler(
                preemptive=False,
                direction=direction,
                enable_aging=enable_aging,
                aging_interval=aging_interval,
                context_switch_overhead=context_switch_overhead,
            )
        elif algorithm_type == AlgorithmType.PRIORITY_PREEMPTIVE:
            return PriorityScheduler(
                preemptive=True,
                direction=direction,
                enable_aging=enable_aging,
                aging_interval=aging_interval,
                context_switch_overhead=context_switch_overhead,
            )
        elif algorithm_type == AlgorithmType.ROUND_ROBIN:
            return RoundRobinScheduler(
                time_quantum=time_quantum,
                context_switch_overhead=context_switch_overhead,
            )
        else:
            raise ValueError(f"Unknown scheduling algorithm type: '{algorithm_type}'")

