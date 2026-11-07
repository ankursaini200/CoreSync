"""Virtual Lab Simulation Engine for Real vs Virtual Comparison.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes workloads purely in simulated discrete logical clock ticks using VirtualCPU and VirtualScheduler.
Never spawns host OS processes or modifies real hardware configuration.
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Set

from engine.analytics.models import MetricClassification
from engine.comparison.models import (
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    VirtualExecutionResult,
    VirtualLabConfig,
)
from engine.comparison.workload_mapper import (
    MappedVirtualWorkload,
    map_data_parallel_workload,
    map_task_parallel_workload,
)
from engine.virtual_lab.virtual_core import VirtualCoreState
from engine.virtual_lab.virtual_cpu import VirtualCPU
from engine.virtual_lab.virtual_scheduler import VirtualScheduler
from engine.virtual_lab.virtual_task import TaskState, VirtualTask

logger = logging.getLogger("CoreSync.Comparison.VirtualExecutor")


class VirtualComparisonExecutor:
    """Simulates comparative workloads on the educational Virtual CPU."""

    def execute(
        self,
        workload_config: ComparisonWorkloadConfig,
        virtual_config: VirtualLabConfig,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> VirtualExecutionResult:
        """Execute the configured workload inside the software Virtual Lab.

        Args:
            workload_config: Logical workload definition.
            virtual_config: Virtual Lab parameters (cores, speeds, scheduler, quantum).
            progress_callback: Optional progress reporter.
            cancel_event: Optional cooperative cancellation flag.

        Returns:
            VirtualExecutionResult with simulated ticks, core allocations, and events.
        """
        if cancel_event and cancel_event.is_set():
            return VirtualExecutionResult(
                status="cancelled",
                virtual_makespan_ticks=0,
                simulated_clock_ticks=0,
                virtual_core_utilization_pct=0.0,
                virtual_core_count=virtual_config.virtual_core_count,
                error_message="Simulation was cancelled prior to startup.",
            )

        try:
            # 1. Map workload to virtual tasks
            if workload_config.workload_type == ComparisonWorkloadType.DATA_PARALLEL:
                _, mapped_virtual, _ = map_data_parallel_workload(
                    config=workload_config,
                    real_workers=virtual_config.virtual_core_count,
                    virtual_cores=virtual_config.virtual_core_count,
                )
            elif workload_config.workload_type == ComparisonWorkloadType.TASK_PARALLEL:
                _, mapped_virtual, _ = map_task_parallel_workload(workload_config)
            else:
                return VirtualExecutionResult(
                    status="failed",
                    virtual_makespan_ticks=0,
                    simulated_clock_ticks=0,
                    virtual_core_utilization_pct=0.0,
                    virtual_core_count=virtual_config.virtual_core_count,
                    error_message=f"Unsupported workload type: {workload_config.workload_type}",
                )

            # 2. Build isolated VirtualCPU and VirtualScheduler instances
            cpu_cfg = virtual_config.to_virtual_cpu_config()
            virtual_cpu = VirtualCPU(cpu_cfg)
            scheduler = VirtualScheduler(
                virtual_cpu=virtual_cpu,
                algorithm=virtual_config.scheduling_algorithm,
                time_quantum=virtual_config.time_quantum,
            )

            # 3. Execute simulation with DAG dependency management
            return self._run_simulation_loop(
                mapped_virtual=mapped_virtual,
                virtual_cpu=virtual_cpu,
                scheduler=scheduler,
                virtual_config=virtual_config,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )

        except Exception as exc:
            logger.error("Virtual Lab simulation failed with error: %s", exc, exc_info=True)
            return VirtualExecutionResult(
                status="failed",
                virtual_makespan_ticks=0,
                simulated_clock_ticks=0,
                virtual_core_utilization_pct=0.0,
                virtual_core_count=virtual_config.virtual_core_count,
                error_message=str(exc),
            )

    def _run_simulation_loop(
        self,
        mapped_virtual: MappedVirtualWorkload,
        virtual_cpu: VirtualCPU,
        scheduler: VirtualScheduler,
        virtual_config: VirtualLabConfig,
        progress_callback: Optional[Callable[[int, int, str], None]],
        cancel_event: Optional[threading.Event],
    ) -> VirtualExecutionResult:
        """Step the simulation tick by tick until all tasks complete or cancelled."""
        tasks_by_name: Dict[str, VirtualTask] = {t.name: t for t in mapped_virtual.tasks}
        task_id_to_name: Dict[int, str] = {t.task_id: t.name for t in mapped_virtual.tasks}
        total_tasks = len(mapped_virtual.tasks)

        # Track DAG dependencies: task_name -> set of prerequisite task_names
        pending_deps: Dict[str, Set[str]] = {}
        for t in mapped_virtual.tasks:
            # Extract raw ID from name e.g. "[t2_matrix] Eigen & Matrix"
            raw_id = t.name.split("]")[0].strip("[") if "]" in t.name else str(t.task_id)
            deps = mapped_virtual.task_dependencies.get(raw_id, [])
            pending_deps[t.name] = set(deps)

        # Separate initially unblocked tasks vs blocked tasks
        ready_now: List[VirtualTask] = []
        blocked_tasks: Dict[str, VirtualTask] = {}

        for t in mapped_virtual.tasks:
            if not pending_deps.get(t.name):
                ready_now.append(t)
            else:
                blocked_tasks[t.name] = t

        # Submit initially ready tasks
        scheduler.submit_batch(ready_now)
        scheduler.dispatch()

        scheduling_events: List[Dict[str, Any]] = []
        virtual_core_allocation: Dict[int, List[str]] = {
            cid: [] for cid in virtual_cpu.cores.keys()
        }
        completed_records: List[Dict[str, Any]] = []
        completed_task_ids: Set[str] = set()

        max_ticks = virtual_config.max_simulation_ticks
        tick_step = 1

        while (len(completed_task_ids) < total_tasks) and (virtual_cpu.current_tick < max_ticks):
            if cancel_event and cancel_event.is_set():
                return VirtualExecutionResult(
                    status="cancelled",
                    virtual_makespan_ticks=virtual_cpu.current_tick,
                    simulated_clock_ticks=virtual_cpu.current_tick,
                    virtual_core_utilization_pct=virtual_cpu.overall_simulated_utilization,
                    virtual_core_count=virtual_config.virtual_core_count,
                    virtual_core_allocation=virtual_core_allocation,
                    task_completion_order=completed_records,
                    scheduling_events=scheduling_events,
                    error_message="Simulation was cancelled during execution.",
                )

            # Record task core assignments
            for core in virtual_cpu.cores.values():
                if core.state == VirtualCoreState.BUSY and core.current_task:
                    t_name = core.current_task.name
                    if not virtual_core_allocation[core.core_id] or virtual_core_allocation[core.core_id][-1] != t_name:
                        virtual_core_allocation[core.core_id].append(t_name)

            # Step scheduler
            finished_tasks = scheduler.step(tick_delta=tick_step)

            for ft in finished_tasks:
                completed_task_ids.add(ft.name)
                if "]" in ft.name:
                    raw_id = ft.name.split("]")[0].strip("[")
                elif "chunk_" in ft.name.lower() or "dp-chunk" in ft.name.lower():
                    raw_id = f"chunk_{ft.task_id - 1}"
                else:
                    raw_id = str(ft.task_id)

                completed_records.append({
                    "task_id": raw_id,
                    "task_number": ft.task_id,
                    "name": ft.name,
                    "assigned_core_id": ft.assigned_core_id,
                    "arrival_tick": ft.arrival_tick,
                    "start_tick": ft.start_tick,
                    "finish_tick": ft.finish_tick,
                    "turnaround_ticks": ft.turnaround_ticks,
                    "waiting_ticks": ft.waiting_ticks,
                    "status": "COMPLETED",
                })
                scheduling_events.append({
                    "tick": ft.finish_tick,
                    "event": "TASK_COMPLETED",
                    "task_id": raw_id,
                    "core_id": ft.assigned_core_id,
                })

                # Check if this completion unblocks any dependent tasks
                unblocked_names = []
                for b_name, b_task in list(blocked_tasks.items()):
                    deps = pending_deps[b_name]
                    deps.discard(raw_id)
                    if not deps:
                        unblocked_names.append(b_name)

                for u_name in unblocked_names:
                    u_task = blocked_tasks.pop(u_name)
                    scheduler.submit_task(u_task)
                    scheduling_events.append({
                        "tick": virtual_cpu.current_tick,
                        "event": "TASK_UNBLOCKED",
                        "task_id": u_task.name,
                    })

                scheduler.dispatch()

            if progress_callback and total_tasks > 0:
                progress_callback(
                    len(completed_task_ids),
                    total_tasks,
                    f"Virtual simulation tick {virtual_cpu.current_tick}: {len(completed_task_ids)}/{total_tasks} completed.",
                )

        makespan_ticks = virtual_cpu.current_tick

        # Compute accurate virtual utilization: sum of core busy ticks / total capacity ticks
        total_capacity_ticks = len(virtual_cpu.cores) * max(1, makespan_ticks)
        total_busy_ticks = sum(c.busy_ticks for c in virtual_cpu.cores.values())
        virt_util_pct = (total_busy_ticks / total_capacity_ticks * 100.0) if total_capacity_ticks > 0 else 0.0
        virt_util_pct = max(0.0, min(100.0, virt_util_pct))

        # Throughput in tasks per tick
        throughput = (len(completed_task_ids) / max(1, makespan_ticks)) if makespan_ticks > 0 else 0.0

        return VirtualExecutionResult(
            status="completed" if len(completed_task_ids) == total_tasks else "incomplete",
            virtual_makespan_ticks=makespan_ticks,
            simulated_clock_ticks=makespan_ticks,
            virtual_core_utilization_pct=virt_util_pct,
            virtual_core_count=len(virtual_cpu.cores),
            virtual_core_allocation=virtual_core_allocation,
            task_completion_order=completed_records,
            scheduling_events=scheduling_events,
            simulated_throughput_tasks_per_tick=throughput,
            avg_waiting_ticks=scheduler.avg_waiting_time,
            avg_turnaround_ticks=scheduler.avg_turnaround_time,
            provenance=MetricClassification.SIMULATED_VIRTUAL.value,
        )
