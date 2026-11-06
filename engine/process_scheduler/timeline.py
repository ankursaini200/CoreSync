"""Execution Timeline and Gantt Chart Event Tracking.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Records granular intervals for process execution, CPU idle periods, and context switches.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class BlockType(str, Enum):
    """Categorization of a time interval on the CPU execution timeline."""
    PROCESS = "process"
    IDLE = "idle"
    CONTEXT_SWITCH = "context_switch"


@dataclass
class TimelineBlock:
    """Represents a contiguous execution slice on the CPU timeline.

    Attributes:
        block_type: PROCESS, IDLE, or CONTEXT_SWITCH.
        process_id: Associated process identifier (or None for IDLE / CONTEXT_SWITCH).
        start_time: Start timestamp of the interval.
        end_time: End timestamp of the interval.
        duration: Duration of this slice (end_time - start_time).
        preempted: Whether this slice ended because the process was preempted.
        priority_at_execution: Priority value of the process during this slice (if applicable).
        context_from_pid: Previous process PID during context switch (if applicable).
        context_to_pid: Next process PID during context switch (if applicable).
    """
    block_type: BlockType
    process_id: Optional[str]
    start_time: float
    end_time: float
    duration: float = field(init=False)
    preempted: bool = False
    priority_at_execution: Optional[int] = None
    context_from_pid: Optional[str] = None
    context_to_pid: Optional[str] = None

    def __post_init__(self):
        self.start_time = round(float(self.start_time), 4)
        self.end_time = round(float(self.end_time), 4)
        self.duration = round(self.end_time - self.start_time, 4)

    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary representation."""
        return {
            "block_type": self.block_type.value,
            "process_id": self.process_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "preempted": self.preempted,
            "priority": self.priority_at_execution,
            "from_pid": self.context_from_pid,
            "to_pid": self.context_to_pid,
        }


@dataclass
class SchedulingTimeline:
    """Chronological record of all scheduling events, CPU bursts, and idle intervals."""
    blocks: List[TimelineBlock] = field(default_factory=list)

    def add_process_burst(
        self,
        process_id: str,
        start_time: float,
        end_time: float,
        preempted: bool = False,
        priority: Optional[int] = None,
    ) -> TimelineBlock:
        """Record an active CPU execution interval for a process."""
        if end_time <= start_time:
            return None  # Ignore zero-duration bursts

        # Merge with previous block if it is the same process and contiguous without preemption
        if (
            self.blocks
            and self.blocks[-1].block_type == BlockType.PROCESS
            and self.blocks[-1].process_id == process_id
            and abs(self.blocks[-1].end_time - start_time) < 1e-9
            and not self.blocks[-1].preempted
        ):
            self.blocks[-1].end_time = round(float(end_time), 4)
            self.blocks[-1].duration = round(self.blocks[-1].end_time - self.blocks[-1].start_time, 4)
            self.blocks[-1].preempted = preempted
            return self.blocks[-1]

        block = TimelineBlock(
            block_type=BlockType.PROCESS,
            process_id=process_id,
            start_time=start_time,
            end_time=end_time,
            preempted=preempted,
            priority_at_execution=priority,
        )
        self.blocks.append(block)
        return block

    def add_idle(self, start_time: float, end_time: float) -> Optional[TimelineBlock]:
        """Record an idle interval where no ready processes were available."""
        if end_time <= start_time:
            return None
        block = TimelineBlock(
            block_type=BlockType.IDLE,
            process_id=None,
            start_time=start_time,
            end_time=end_time,
        )
        self.blocks.append(block)
        return block

    def add_context_switch(
        self,
        start_time: float,
        end_time: float,
        from_pid: Optional[str] = None,
        to_pid: Optional[str] = None,
    ) -> Optional[TimelineBlock]:
        """Record a context-switch overhead interval between processes."""
        if end_time <= start_time:
            return None
        block = TimelineBlock(
            block_type=BlockType.CONTEXT_SWITCH,
            process_id=None,
            start_time=start_time,
            end_time=end_time,
            context_from_pid=from_pid,
            context_to_pid=to_pid,
        )
        self.blocks.append(block)
        return block

    @property
    def total_simulation_time(self) -> float:
        """Total time elapsed from beginning of simulation to completion of all processes."""
        if not self.blocks:
            return 0.0
        return self.blocks[-1].end_time

    @property
    def total_busy_time(self) -> float:
        """Total time the CPU spent actively executing process burst instructions."""
        return sum(b.duration for b in self.blocks if b.block_type == BlockType.PROCESS)

    @property
    def total_idle_time(self) -> float:
        """Total time the CPU was idle with no ready jobs."""
        return sum(b.duration for b in self.blocks if b.block_type == BlockType.IDLE)

    @property
    def total_context_switch_time(self) -> float:
        """Total time spent in context-switch overhead transitions."""
        return sum(b.duration for b in self.blocks if b.block_type == BlockType.CONTEXT_SWITCH)

    @property
    def context_switch_count(self) -> int:
        """Count of process switches that occurred during simulation.

        A switch occurs when CPU shifts between different processes, or explicitly
        recorded context-switch blocks. Transitions across idle intervals do not count.
        """
        # If explicit context switch blocks are recorded
        cs_blocks = sum(1 for b in self.blocks if b.block_type == BlockType.CONTEXT_SWITCH)
        if cs_blocks > 0:
            return cs_blocks

        # Otherwise count transitions between different processes, resetting after idle gaps
        switches = 0
        last_pid = None
        for b in self.blocks:
            if b.block_type == BlockType.IDLE:
                last_pid = None
            elif b.block_type == BlockType.PROCESS:
                if last_pid is not None and b.process_id != last_pid:
                    switches += 1
                last_pid = b.process_id
        return switches

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Serialize all blocks for GUI Gantt rendering."""
        return [b.to_dict() for b in self.blocks]

