"""Scheduling Metrics and Simulation Results.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Computes standard operating system scheduling metrics from simulation execution data.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from engine.process_scheduler.models import Process
from engine.process_scheduler.timeline import SchedulingTimeline


@dataclass
class SchedulingMetrics:
    """Aggregated performance metrics for a completed scheduling simulation run.

    Mathematical definitions:
        Turnaround Time = Completion Time - Arrival Time
        Waiting Time = Turnaround Time - Burst Time
        Response Time = First Start Time - Arrival Time
        CPU Utilization = (Busy CPU Time / Total Simulation Time) * 100
        Throughput = Completed Processes / Total Simulation Time
    """
    total_processes: int
    completed_processes: int
    total_simulation_time: float
    busy_cpu_time: float
    idle_cpu_time: float
    context_switch_time: float
    context_switches: int
    average_turnaround_time: float
    average_waiting_time: float
    average_response_time: float
    cpu_utilization_pct: float
    throughput: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to a displayable dictionary."""
        return {
            "total_processes": self.total_processes,
            "completed_processes": self.completed_processes,
            "total_simulation_time": round(self.total_simulation_time, 4),
            "busy_cpu_time": round(self.busy_cpu_time, 4),
            "idle_cpu_time": round(self.idle_cpu_time, 4),
            "context_switch_time": round(self.context_switch_time, 4),
            "context_switches": self.context_switches,
            "average_turnaround_time": round(self.average_turnaround_time, 4),
            "average_waiting_time": round(self.average_waiting_time, 4),
            "average_response_time": round(self.average_response_time, 4),
            "cpu_utilization_pct": round(self.cpu_utilization_pct, 2),
            "throughput": round(self.throughput, 6),
        }


@dataclass
class SimulationResult:
    """Comprehensive outcome parcel of a CPU scheduling simulation run."""
    algorithm_name: str
    processes: List[Process]
    timeline: SchedulingTimeline
    metrics: SchedulingMetrics
    parameters: Dict[str, Any] = field(default_factory=dict)
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "algorithm_name": self.algorithm_name,
            "parameters": self.parameters,
            "metrics": self.metrics.to_dict(),
            "processes": [p.to_dict() for p in self.processes],
            "timeline": self.timeline.to_dict_list(),
            "notes": self.notes,
        }


def calculate_metrics(
    processes: List[Process],
    timeline: SchedulingTimeline,
) -> SchedulingMetrics:
    """Compute comprehensive performance metrics from executed processes and timeline.

    Args:
        processes: List of completed processes with arrival, burst, start, and completion times.
        timeline: The detailed execution timeline recorded by the scheduler.

    Returns:
        SchedulingMetrics instance with all derived metrics.
    """
    n = len(processes)
    if n == 0:
        return SchedulingMetrics(
            total_processes=0,
            completed_processes=0,
            total_simulation_time=0.0,
            busy_cpu_time=0.0,
            idle_cpu_time=0.0,
            context_switch_time=0.0,
            context_switches=0,
            average_turnaround_time=0.0,
            average_waiting_time=0.0,
            average_response_time=0.0,
            cpu_utilization_pct=0.0,
            throughput=0.0,
        )

    completed = [p for p in processes if p.completion_time is not None]
    completed_count = len(completed)

    # Calculate per-process metrics accurately
    total_tat = 0.0
    total_wt = 0.0
    total_rt = 0.0

    for p in processes:
        if p.completion_time is not None:
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = max(0.0, p.turnaround_time - p.burst_time)
            if p.start_time is not None:
                p.response_time = max(0.0, p.start_time - p.arrival_time)
            else:
                p.response_time = 0.0

            total_tat += p.turnaround_time
            total_wt += p.waiting_time
            total_rt += p.response_time

    avg_tat = (total_tat / completed_count) if completed_count > 0 else 0.0
    avg_wt = (total_wt / completed_count) if completed_count > 0 else 0.0
    avg_rt = (total_rt / completed_count) if completed_count > 0 else 0.0

    total_sim_time = timeline.total_simulation_time
    busy_time = timeline.total_busy_time
    idle_time = timeline.total_idle_time
    cs_time = timeline.total_context_switch_time
    cs_count = timeline.context_switch_count

    # CPU Utilization = (Busy CPU Time / Total Simulation Time) * 100
    cpu_util = ((busy_time / total_sim_time) * 100.0) if total_sim_time > 0 else 0.0
    cpu_util = max(0.0, min(100.0, cpu_util))

    # Throughput = Number of Completed Processes / Total Simulation Time
    throughput = (completed_count / total_sim_time) if total_sim_time > 0 else 0.0

    return SchedulingMetrics(
        total_processes=n,
        completed_processes=completed_count,
        total_simulation_time=total_sim_time,
        busy_cpu_time=busy_time,
        idle_cpu_time=idle_time,
        context_switch_time=cs_time,
        context_switches=cs_count,
        average_turnaround_time=avg_tat,
        average_waiting_time=avg_wt,
        average_response_time=avg_rt,
        cpu_utilization_pct=cpu_util,
        throughput=throughput,
    )

