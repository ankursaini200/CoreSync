"""Reusable Educational Scheduling Workload Presets.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides curated, standard textbook workloads demonstrating specific scheduling phenomena.
"""

from dataclasses import dataclass
from typing import List

from engine.process_scheduler.models import Process


@dataclass
class WorkloadPreset:
    """Predefined educational process workload."""
    preset_id: str
    name: str
    description: str
    learning_objective: str
    processes: List[Process]

    def get_cloned_processes(self) -> List[Process]:
        """Return a fresh, independent clone of the processes."""
        return [p.clone() for p in self.processes]


def get_all_presets() -> List[WorkloadPreset]:
    """Return all available educational scheduling presets."""
    return [
        WorkloadPreset(
            preset_id="simple_varying_bursts",
            name="1. Simple Workload (Varying Bursts)",
            description="Four processes arriving simultaneously at t=0 with distinctly different burst times.",
            learning_objective=(
                "Demonstrates the baseline differences between FCFS and SJF when arrival times are identical. "
                "Highlights how SJF minimizes average waiting time compared to FCFS."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=6.0, priority=3),
                Process(process_id="P2", arrival_time=0.0, burst_time=8.0, priority=1),
                Process(process_id="P3", arrival_time=0.0, burst_time=2.0, priority=4),
                Process(process_id="P4", arrival_time=0.0, burst_time=4.0, priority=2),
            ],
        ),
        WorkloadPreset(
            preset_id="staggered_arrivals",
            name="2. Staggered Arrival Times",
            description="Processes arriving at different times (t=0, 2, 4, 5) with mixed burst durations.",
            learning_objective=(
                "Illustrates ready queue evolution as new processes enter the system over time. "
                "Shows how FCFS and non-preemptive algorithms commit to running jobs even when shorter jobs arrive later."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=7.0, priority=2),
                Process(process_id="P2", arrival_time=2.0, burst_time=4.0, priority=1),
                Process(process_id="P3", arrival_time=4.0, burst_time=1.0, priority=3),
                Process(process_id="P4", arrival_time=5.0, burst_time=4.0, priority=2),
            ],
        ),
        WorkloadPreset(
            preset_id="sjf_benchmark",
            name="3. SJF vs FCFS Optimization Benchmark",
            description="Classic textbook case (P1=8, P2=4, P3=9, P4=5) arriving at t=0.",
            learning_objective=(
                "Proves the theoretical optimality of Shortest Job First in minimizing average waiting time. "
                "In FCFS, P1 executes first causing convoy effect; in SJF, P2 and P4 run first, cutting average waiting time in half."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=8.0, priority=3),
                Process(process_id="P2", arrival_time=0.0, burst_time=4.0, priority=2),
                Process(process_id="P3", arrival_time=0.0, burst_time=9.0, priority=4),
                Process(process_id="P4", arrival_time=0.0, burst_time=5.0, priority=1),
            ],
        ),
        WorkloadPreset(
            preset_id="priority_demo",
            name="4. Priority Scheduling (Mixed Priorities)",
            description="Five jobs with priorities ranging from 1 to 5 arriving at t=0 and t=1.",
            learning_objective=(
                "Demonstrates how high-priority tasks bypass low-priority tasks in the ready queue. "
                "Allows comparing Non-Preemptive Priority vs Preemptive Priority behavior."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=10.0, priority=3),
                Process(process_id="P2", arrival_time=1.0, burst_time=1.0, priority=1),
                Process(process_id="P3", arrival_time=2.0, burst_time=2.0, priority=4),
                Process(process_id="P4", arrival_time=3.0, burst_time=1.0, priority=5),
                Process(process_id="P5", arrival_time=4.0, burst_time=5.0, priority=2),
            ],
        ),
        WorkloadPreset(
            preset_id="round_robin_preemption",
            name="5. Round Robin Preemption & Quantum Impact",
            description="Three CPU-intensive jobs (bursts 24, 3, 3) arriving at t=0.",
            learning_objective=(
                "Illustrates time slicing, preemption points, and responsiveness. "
                "Shows how a quantum of 4 ms gives quick response times to P2 and P3 compared to FCFS where they wait 24 ms."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=24.0, priority=1),
                Process(process_id="P2", arrival_time=0.0, burst_time=3.0, priority=1),
                Process(process_id="P3", arrival_time=0.0, burst_time=3.0, priority=1),
            ],
        ),
        WorkloadPreset(
            preset_id="starvation_aging",
            name="6. Starvation & Priority Aging",
            description="A low-priority job (P_LOW, prio=5) arrived at t=0, followed by a continuous wave of high-priority jobs (prio=1).",
            learning_objective=(
                "Demonstrates indefinite blocking (starvation) in priority scheduling without aging. "
                "When priority aging is enabled, P_LOW's priority incrementally improves until it finally executes."
            ),
            processes=[
                Process(process_id="P_LOW", arrival_time=0.0, burst_time=6.0, priority=5),
                Process(process_id="P_HI_1", arrival_time=1.0, burst_time=3.0, priority=1),
                Process(process_id="P_HI_2", arrival_time=3.0, burst_time=3.0, priority=1),
                Process(process_id="P_HI_3", arrival_time=5.0, burst_time=3.0, priority=1),
                Process(process_id="P_HI_4", arrival_time=7.0, burst_time=3.0, priority=1),
            ],
        ),
        WorkloadPreset(
            preset_id="cpu_idle_intervals",
            name="7. CPU Idle Gaps & Sparse Arrivals",
            description="Processes arriving with significant time gaps between them (t=0, 8, 18).",
            learning_objective=(
                "Demonstrates how schedulers and the Gantt chart handle CPU idle periods when no jobs are ready. "
                "Verifies CPU utilization formula correctly deducts idle gaps."
            ),
            processes=[
                Process(process_id="P1", arrival_time=0.0, burst_time=3.0, priority=1),
                Process(process_id="P2", arrival_time=8.0, burst_time=4.0, priority=2),
                Process(process_id="P3", arrival_time=18.0, burst_time=2.0, priority=1),
            ],
        ),
    ]


def get_preset_by_id(preset_id: str) -> WorkloadPreset:
    """Retrieve preset by ID or raise KeyError."""
    presets = {p.preset_id: p for p in get_all_presets()}
    if preset_id not in presets:
        raise KeyError(f"Unknown preset ID: '{preset_id}'")
    return presets[preset_id]

