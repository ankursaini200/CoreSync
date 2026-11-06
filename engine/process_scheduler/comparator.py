"""Comparative Scheduling Algorithm Benchmark Runner.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes all compatible scheduling algorithms against an identical process dataset to
compare metrics side-by-side.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.process_scheduler.algorithms import AlgorithmType
from engine.process_scheduler.metrics import SimulationResult
from engine.process_scheduler.models import (
    PriorityDirection,
    Process,
    validate_context_switch,
    validate_process_list,
    validate_quantum,
)
from engine.process_scheduler.simulator import ProcessSchedulerSimulator


@dataclass
class ComparisonSummaryRow:
    """Row in an algorithm comparison table."""
    algorithm_type: str
    algorithm_name: str
    average_waiting_time: float
    average_turnaround_time: float
    average_response_time: float
    cpu_utilization_pct: float
    throughput: float
    context_switches: int
    total_simulation_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm_type": self.algorithm_type,
            "algorithm_name": self.algorithm_name,
            "average_waiting_time": round(self.average_waiting_time, 4),
            "average_turnaround_time": round(self.average_turnaround_time, 4),
            "average_response_time": round(self.average_response_time, 4),
            "cpu_utilization_pct": round(self.cpu_utilization_pct, 2),
            "throughput": round(self.throughput, 6),
            "context_switches": self.context_switches,
            "total_simulation_time": round(self.total_simulation_time, 4),
        }


def compare_all_algorithms(
    processes: List[Process],
    time_quantum: float = 2.0,
    direction: PriorityDirection = PriorityDirection.LOWER_IS_HIGHER,
    enable_aging: bool = False,
    aging_interval: float = 5.0,
    context_switch_overhead: float = 0.0,
    algorithm_list: Optional[List[AlgorithmType]] = None,
) -> Tuple[List[SimulationResult], List[ComparisonSummaryRow]]:
    """Execute all scheduling algorithms on the same process dataset.

    Args:
        processes: Input list of processes.
        time_quantum: Quantum for Round Robin.
        direction: Priority direction for Priority algorithms.
        enable_aging: Aging flag for Priority algorithms.
        aging_interval: Aging interval for Priority algorithms.
        context_switch_overhead: Context switch overhead penalty.
        algorithm_list: Optional list of algorithms to compare (defaults to all 6).

    Returns:
        Tuple of (List of SimulationResult objects, List of ComparisonSummaryRow rows).
    """
    # Normalize enum types
    if isinstance(direction, str):
        direction = PriorityDirection(direction)

    validate_process_list(processes)
    validate_context_switch(context_switch_overhead)
    validate_quantum(time_quantum)

    raw_targets = algorithm_list or [
        AlgorithmType.FCFS,
        AlgorithmType.SJF,
        AlgorithmType.SRTF,
        AlgorithmType.PRIORITY_NON_PREEMPTIVE,
        AlgorithmType.PRIORITY_PREEMPTIVE,
        AlgorithmType.ROUND_ROBIN,
    ]
    targets: List[AlgorithmType] = [
        AlgorithmType(a) if isinstance(a, str) else a for a in raw_targets
    ]

    results: List[SimulationResult] = []
    summary_rows: List[ComparisonSummaryRow] = []

    for algo in targets:
        # Clone fresh processes for each algorithm run
        cloned_procs = [p.clone() for p in processes]
        res = ProcessSchedulerSimulator.simulate(
            processes=cloned_procs,
            algorithm_type=algo,
            time_quantum=time_quantum,
            direction=direction,
            enable_aging=enable_aging,
            aging_interval=aging_interval,
            context_switch_overhead=context_switch_overhead,
        )
        results.append(res)
        m = res.metrics
        summary_rows.append(
            ComparisonSummaryRow(
                algorithm_type=algo.value,
                algorithm_name=algo.display_name,
                average_waiting_time=m.average_waiting_time,
                average_turnaround_time=m.average_turnaround_time,
                average_response_time=m.average_response_time,
                cpu_utilization_pct=m.cpu_utilization_pct,
                throughput=m.throughput,
                context_switches=m.context_switches,
                total_simulation_time=m.total_simulation_time,
            )
        )

    return results, summary_rows
