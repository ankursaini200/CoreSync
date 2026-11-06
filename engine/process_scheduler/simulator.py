"""High-Level CPU Scheduling Simulation Engine.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides the central execution entrypoint for running single-algorithm scheduling simulations.
"""

from typing import Any, Dict, List, Optional

from engine.process_scheduler.algorithms import (
    AlgorithmType,
    SchedulerFactory,
)
from engine.process_scheduler.metrics import (
    SchedulingMetrics,
    SimulationResult,
    calculate_metrics,
)
from engine.process_scheduler.models import (
    PriorityDirection,
    Process,
    validate_context_switch,
    validate_process_list,
    validate_quantum,
)


class ProcessSchedulerSimulator:
    """Coordinates input validation, algorithm dispatch, timeline capture, and metric computation."""

    @staticmethod
    def simulate(
        processes: List[Process],
        algorithm_type: AlgorithmType = AlgorithmType.FCFS,
        time_quantum: float = 2.0,
        direction: PriorityDirection = PriorityDirection.LOWER_IS_HIGHER,
        enable_aging: bool = False,
        aging_interval: float = 5.0,
        context_switch_overhead: float = 0.0,
    ) -> SimulationResult:
        """Run an end-to-end CPU scheduling simulation.

        Args:
            processes: List of Process jobs to schedule.
            algorithm_type: The CPU scheduling policy to apply.
            time_quantum: Time slice duration for Round Robin (ignored for non-RR).
            direction: LOWER_IS_HIGHER or HIGHER_IS_HIGHER priority direction.
            enable_aging: Whether to apply priority aging to reduce starvation.
            aging_interval: Time units in ready queue before priority improves by 1.
            context_switch_overhead: Time penalty for switching between processes.

        Returns:
            SimulationResult containing scheduled processes, timeline blocks, and metrics.

        Raises:
            ValueError: If any input configuration or process attribute is invalid.
        """
        # 1. Normalize enum types (handles PySide6 QVariant string coercion)
        if isinstance(algorithm_type, str):
            algorithm_type = AlgorithmType(algorithm_type)
        if isinstance(direction, str):
            direction = PriorityDirection(direction)

        # 2. Rigorous input validation
        validate_process_list(processes)
        validate_context_switch(context_switch_overhead)
        if algorithm_type == AlgorithmType.ROUND_ROBIN:
            validate_quantum(time_quantum)

        # 3. Instantiate algorithm
        scheduler = SchedulerFactory.create(
            algorithm_type=algorithm_type,
            time_quantum=time_quantum,
            direction=direction,
            enable_aging=enable_aging,
            aging_interval=aging_interval,
            context_switch_overhead=context_switch_overhead,
        )

        # 3. Execute scheduling simulation
        completed_procs, timeline = scheduler.schedule(processes)

        # 4. Compute metrics
        metrics = calculate_metrics(completed_procs, timeline)

        params: Dict[str, Any] = {
            "algorithm": algorithm_type.value,
            "algorithm_display": algorithm_type.display_name,
            "context_switch_overhead": context_switch_overhead,
        }
        if algorithm_type == AlgorithmType.ROUND_ROBIN:
            params["time_quantum"] = time_quantum
        if algorithm_type in (AlgorithmType.PRIORITY_NON_PREEMPTIVE, AlgorithmType.PRIORITY_PREEMPTIVE):
            params["priority_direction"] = direction.value
            params["enable_aging"] = enable_aging
            params["aging_interval"] = aging_interval

        return SimulationResult(
            algorithm_name=algorithm_type.display_name,
            processes=completed_procs,
            timeline=timeline,
            metrics=metrics,
            parameters=params,
        )
