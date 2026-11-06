"""Process and Job Data Models for the CoreSync Process Scheduler.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides clean, validated data structures for CPU scheduling simulation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ProcessState(str, Enum):
    """Lifecycle execution states of a scheduled process."""
    NOT_ARRIVED = "not_arrived"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    WAITING = "waiting"


class PriorityDirection(str, Enum):
    """Defines how numeric priority values are interpreted.

    LOWER_IS_HIGHER: Smaller numeric value indicates higher priority (e.g. 1 is higher than 5).
                     Common in Unix/Linux nice levels.
    HIGHER_IS_HIGHER: Larger numeric value indicates higher priority (e.g. 10 is higher than 1).
                      Common in Windows / real-time RTOS schedulers.
    """
    LOWER_IS_HIGHER = "lower_is_higher"
    HIGHER_IS_HIGHER = "higher_is_higher"


@dataclass
class Process:
    """Represents an independent job or process for CPU scheduling simulation.

    Attributes:
        process_id: Unique identifier for the process (e.g., 'P1', 'P2').
        arrival_time: Time at which the process arrives in the system (must be >= 0).
        burst_time: Total CPU execution duration required by the process (must be > 0).
        priority: Base priority value (default 0).
        remaining_time: Remaining CPU burst duration required for completion.
        current_priority: Dynamic priority value after aging adjustments.
        start_time: Timestamp of the first time the process was dispatched to the CPU.
        completion_time: Timestamp when the process completed execution.
        waiting_time: Total time spent in ready queue awaiting CPU execution.
        turnaround_time: Duration from arrival to completion (Completion - Arrival).
        response_time: Duration from arrival to first execution (First Start - Arrival).
        state: Current lifecycle execution state.
    """
    process_id: str
    arrival_time: float
    burst_time: float
    priority: int = 0
    remaining_time: float = field(init=False)
    current_priority: int = field(init=False)
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    waiting_time: float = 0.0
    turnaround_time: float = 0.0
    response_time: float = 0.0
    state: ProcessState = ProcessState.NOT_ARRIVED

    def __post_init__(self):
        self.process_id = str(self.process_id).strip()
        self.arrival_time = float(self.arrival_time)
        self.burst_time = float(self.burst_time)
        self.priority = int(self.priority)
        self.remaining_time = self.burst_time
        self.current_priority = self.priority

    @property
    def is_completed(self) -> bool:
        return self.remaining_time <= 1e-9

    def reset(self) -> None:
        """Reset execution state for a new simulation run."""
        self.remaining_time = self.burst_time
        self.current_priority = self.priority
        self.start_time = None
        self.completion_time = None
        self.waiting_time = 0.0
        self.turnaround_time = 0.0
        self.response_time = 0.0
        self.state = ProcessState.NOT_ARRIVED

    def clone(self) -> "Process":
        """Create an independent copy of this process in initial state."""
        return Process(
            process_id=self.process_id,
            arrival_time=self.arrival_time,
            burst_time=self.burst_time,
            priority=self.priority,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert process state to a dictionary for UI or reporting."""
        return {
            "process_id": self.process_id,
            "arrival_time": self.arrival_time,
            "burst_time": self.burst_time,
            "priority": self.priority,
            "current_priority": self.current_priority,
            "remaining_time": round(self.remaining_time, 4),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "waiting_time": round(self.waiting_time, 4),
            "turnaround_time": round(self.turnaround_time, 4),
            "response_time": round(self.response_time, 4),
            "state": self.state.value,
        }


def validate_process(process: Process) -> None:
    """Validate process attributes against architectural constraints.

    Raises:
        ValueError: If any attribute is invalid.
    """
    if not process.process_id:
        raise ValueError("Process ID cannot be empty.")

    if process.arrival_time < 0:
        raise ValueError(
            f"Process '{process.process_id}': Invalid arrival time {process.arrival_time}. "
            "Arrival time must be non-negative (>= 0)."
        )

    if process.burst_time <= 0:
        raise ValueError(
            f"Process '{process.process_id}': Invalid burst time {process.burst_time}. "
            "Burst time must be strictly positive (> 0)."
        )


def validate_process_list(processes: List[Process]) -> None:
    """Validate a batch of processes.

    Raises:
        ValueError: If the list is empty, contains duplicate IDs, or contains invalid entries.
    """
    if not processes:
        raise ValueError("Process list cannot be empty for scheduling simulation.")

    seen_ids: Set[str] = set()
    for p in processes:
        validate_process(p)
        if p.process_id in seen_ids:
            raise ValueError(f"Duplicate process ID detected: '{p.process_id}'. IDs must be unique.")
        seen_ids.add(p.process_id)


def validate_quantum(quantum: float) -> None:
    """Validate Round Robin time quantum.

    Raises:
        ValueError: If quantum is not strictly positive.
    """
    if quantum <= 0:
        raise ValueError(
            f"Invalid time quantum: {quantum}. Time quantum must be strictly positive (> 0)."
        )


def validate_context_switch(overhead: float) -> None:
    """Validate context-switch overhead duration.

    Raises:
        ValueError: If overhead is negative.
    """
    if overhead < 0:
        raise ValueError(
            f"Invalid context-switch overhead: {overhead}. Overhead must be non-negative (>= 0)."
        )

