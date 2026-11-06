"""CoreSync Classical CPU Scheduling Simulation Engine.

Strict Architectural Rule: This package MUST NOT import PySide6 or any Qt modules.
Provides classical CPU scheduling policies, process models, execution timelines,
and performance metrics.
"""

from engine.process_scheduler.models import (
    PriorityDirection,
    Process,
    ProcessState,
    validate_context_switch,
    validate_process,
    validate_process_list,
    validate_quantum,
)
from engine.process_scheduler.timeline import (
    BlockType,
    SchedulingTimeline,
    TimelineBlock,
)
from engine.process_scheduler.metrics import (
    SchedulingMetrics,
    SimulationResult,
    calculate_metrics,
)
from engine.process_scheduler.algorithms import (
    AlgorithmType,
    BaseScheduler,
    FCFSScheduler,
    PriorityScheduler,
    RoundRobinScheduler,
    SchedulerFactory,
    SJFScheduler,
    SRTFScheduler,
)
from engine.process_scheduler.simulator import ProcessSchedulerSimulator
from engine.process_scheduler.comparator import (
    ComparisonSummaryRow,
    compare_all_algorithms,
)
from engine.process_scheduler.presets import (
    WorkloadPreset,
    get_all_presets,
    get_preset_by_id,
)

__all__ = [
    # Models
    "Process",
    "ProcessState",
    "PriorityDirection",
    "validate_process",
    "validate_process_list",
    "validate_quantum",
    "validate_context_switch",
    # Timeline
    "BlockType",
    "TimelineBlock",
    "SchedulingTimeline",
    # Metrics
    "SchedulingMetrics",
    "SimulationResult",
    "calculate_metrics",
    # Algorithms
    "AlgorithmType",
    "BaseScheduler",
    "FCFSScheduler",
    "SJFScheduler",
    "SRTFScheduler",
    "PriorityScheduler",
    "RoundRobinScheduler",
    "SchedulerFactory",
    # High-level Runner
    "ProcessSchedulerSimulator",
    "ComparisonSummaryRow",
    "compare_all_algorithms",
    # Presets
    "WorkloadPreset",
    "get_all_presets",
    "get_preset_by_id",
]

