"""Real System Execution Engine for Real vs Virtual Comparison.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes workloads on actual physical hardware using multiprocessing.get_context("spawn").
Coordinates with existing DataParallelExecutor, TaskParallelExecutor, and ProcessManager.
"""

import logging
import multiprocessing
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil

from engine.analytics.input_cloner import clone_benchmark_input
from engine.analytics.interval_timing import compute_interval_metrics
from engine.analytics.models import MetricClassification
from engine.comparison.models import (
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealExecutionResult,
    RealSystemConfig,
)
from engine.comparison.workload_mapper import (
    MappedRealWorkload,
    map_data_parallel_workload,
    map_task_parallel_workload,
)
from engine.data_parallel.executor import DataParallelExecutor
from engine.process_manager import ProcessManager
from engine.task_parallel.executor import TaskParallelExecutor

logger = logging.getLogger("CoreSync.Comparison.RealExecutor")


class RealComparisonExecutor:
    """Executes comparative workloads on the host CPU using real spawned workers."""

    def __init__(self):
        self._dp_executor = DataParallelExecutor()
        self._tp_executor = TaskParallelExecutor()
        self._process_manager = ProcessManager(start_method="spawn")

    def cleanup(self) -> None:
        """Ensure all child workers across both executors are safely terminated and reaped."""
        self._dp_executor.cancel_active_execution()
        self._tp_executor.cancel_active_execution()
        self._process_manager.terminate_all()
        self._process_manager.reap_orphans()

    def execute(
        self,
        workload_config: ComparisonWorkloadConfig,
        real_config: RealSystemConfig,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> RealExecutionResult:
        """Execute the configured workload on the host machine.

        Args:
            workload_config: Logical workload definition.
            real_config: Real System execution parameters (worker count, pinning, timeout).
            progress_callback: Optional progress reporter (completed, total, message).
            cancel_event: Optional cooperative cancellation flag.

        Returns:
            RealExecutionResult with empirical timing, intervals, and memory telemetry.
        """
        if cancel_event and cancel_event.is_set():
            return RealExecutionResult(
                status="cancelled",
                wall_clock_time_s=0.0,
                worker_count=real_config.worker_count,
                error_message="Execution was cancelled prior to startup.",
            )

        # Capture initial host telemetry
        proc = psutil.Process(os.getpid())
        initial_rss = proc.memory_info().rss
        initial_cpu_pct = psutil.cpu_percent(interval=None)

        # Setup multiprocessing cancellation bridge
        ctx = multiprocessing.get_context("spawn")
        mp_cancel_event = ctx.Event()

        # Thread to propagate cancel_event to mp_cancel_event
        stop_forwarder = threading.Event()

        def _forward_cancel():
            while not stop_forwarder.is_set():
                if cancel_event and cancel_event.is_set():
                    mp_cancel_event.set()
                    self._dp_executor.cancel_active_execution()
                    self._tp_executor.cancel_active_execution()
                    break
                time.sleep(0.05)

        forwarder_thread = threading.Thread(target=_forward_cancel, daemon=True)
        forwarder_thread.start()

        try:
            if workload_config.workload_type == ComparisonWorkloadType.DATA_PARALLEL:
                return self._execute_data_parallel(
                    workload_config=workload_config,
                    real_config=real_config,
                    progress_callback=progress_callback,
                    mp_cancel_event=mp_cancel_event,
                    initial_rss=initial_rss,
                    initial_cpu_pct=initial_cpu_pct,
                )
            elif workload_config.workload_type == ComparisonWorkloadType.TASK_PARALLEL:
                return self._execute_task_parallel(
                    workload_config=workload_config,
                    real_config=real_config,
                    progress_callback=progress_callback,
                    mp_cancel_event=mp_cancel_event,
                    initial_rss=initial_rss,
                    initial_cpu_pct=initial_cpu_pct,
                )
            else:
                return RealExecutionResult(
                    status="failed",
                    wall_clock_time_s=0.0,
                    worker_count=real_config.worker_count,
                    error_message=f"Unsupported workload type: {workload_config.workload_type}",
                )
        except Exception as exc:
            logger.error("Real System execution failed with error: %s", exc, exc_info=True)
            return RealExecutionResult(
                status="failed",
                wall_clock_time_s=0.0,
                worker_count=real_config.worker_count,
                error_message=str(exc),
            )
        finally:
            stop_forwarder.set()
            forwarder_thread.join(timeout=0.5)
            # Ensure no lingering workers remain
            self.cleanup()

    def _execute_data_parallel(
        self,
        workload_config: ComparisonWorkloadConfig,
        real_config: RealSystemConfig,
        progress_callback: Optional[Callable[[int, int, str], None]],
        mp_cancel_event: Any,
        initial_rss: int,
        initial_cpu_pct: float,
    ) -> RealExecutionResult:
        """Run Data Parallel numerical kernel across real spawned workers."""
        mapped_real, _, _ = map_data_parallel_workload(
            config=workload_config,
            real_workers=real_config.worker_count,
            virtual_cores=real_config.worker_count,
        )

        dataset_copy = clone_benchmark_input(mapped_real.dataset)

        b_res = self._dp_executor.run_benchmark(
            op_id=mapped_real.op_id,
            data=dataset_copy,
            worker_count=real_config.worker_count,
            progress_callback=progress_callback,
            cancel_event=mp_cancel_event,
            custom_cpus=real_config.pinned_cpus,
        )

        if mp_cancel_event.is_set():
            return RealExecutionResult(
                status="cancelled",
                wall_clock_time_s=b_res.parallel_time_s,
                worker_count=real_config.worker_count,
                error_message="Data Parallel benchmark was cancelled.",
            )

        # Extract worker intervals
        worker_intervals: List[Tuple[float, float]] = []
        raw_durations: List[float] = []
        task_completions: List[Dict[str, Any]] = []

        if b_res.worker_results:
            for wr in b_res.worker_results:
                s_time = getattr(wr, "worker_start_time", getattr(wr, "start_timestamp", None))
                e_time = getattr(wr, "worker_finish_time", getattr(wr, "finish_timestamp", None))
                dur = getattr(wr, "compute_time_s", getattr(wr, "compute_duration_s", 0.0))
                pid = getattr(wr, "worker_pid", getattr(wr, "process_id", None))

                if s_time is not None and e_time is not None:
                    worker_intervals.append((s_time, e_time))
                raw_durations.append(dur)
                task_completions.append({
                    "task_id": f"chunk_{wr.worker_id}",
                    "worker_id": wr.worker_id,
                    "process_id": pid,
                    "duration_s": round(dur, 6),
                    "status": "COMPLETED" if wr.success else "FAILED",
                })

        window_start = min((s for s, e in worker_intervals), default=0.0)
        window_end = max((e for s, e in worker_intervals), default=b_res.parallel_time_s)
        if b_res.parallel_time_s > 0:
            window_end = max(window_end, window_start + b_res.parallel_time_s)

        int_metrics = compute_interval_metrics(
            window_start=window_start,
            window_end=window_end,
            worker_intervals=worker_intervals,
            raw_compute_durations=raw_durations,
        )

        # Telemetry
        final_rss = psutil.Process(os.getpid()).memory_info().rss
        peak_mb = max(0.0, (final_rss - initial_rss) / (1024 * 1024))
        if peak_mb <= 0.0:
            peak_mb = round(final_rss / (1024 * 1024), 2)

        # Utilization
        cap = real_config.worker_count * b_res.parallel_time_s
        util_pct = (int_metrics.aggregate_worker_compute_time_s / cap * 100.0) if cap > 0 else 0.0
        util_pct = max(0.0, min(100.0, util_pct))

        return RealExecutionResult(
            status="completed",
            wall_clock_time_s=b_res.parallel_time_s,
            worker_count=real_config.worker_count,
            worker_intervals=worker_intervals,
            aggregate_worker_compute_time_s=int_metrics.aggregate_worker_compute_time_s,
            compute_interval_union_s=int_metrics.compute_interval_union_s,
            no_worker_compute_time_s=int_metrics.no_worker_compute_time_s,
            sequential_baseline_s=b_res.sequential_time_s,
            actual_speedup=b_res.speedup,
            worker_utilization_pct=util_pct,
            peak_memory_rss_mb=peak_mb,
            host_cpu_percent=round(psutil.cpu_percent(interval=None), 1),
            task_completions=task_completions,
            verification_passed=b_res.verification.passed,
            provenance=MetricClassification.DIRECTLY_MEASURED.value,
        )

    def _execute_task_parallel(
        self,
        workload_config: ComparisonWorkloadConfig,
        real_config: RealSystemConfig,
        progress_callback: Optional[Callable[[int, int, str], None]],
        mp_cancel_event: Any,
        initial_rss: int,
        initial_cpu_pct: float,
    ) -> RealExecutionResult:
        """Run Task Parallel DAG preset across real spawned workers."""
        mapped_real, _, _ = map_task_parallel_workload(workload_config)

        graph_copy = clone_benchmark_input(mapped_real.task_graph)

        b_res = self._tp_executor.run_benchmark(
            graph=graph_copy,
            worker_count=real_config.worker_count,
            progress_callback=progress_callback,
            cancel_event=mp_cancel_event,
            custom_cpus=real_config.pinned_cpus,
        )

        if mp_cancel_event.is_set():
            return RealExecutionResult(
                status="cancelled",
                wall_clock_time_s=b_res.makespan_s,
                worker_count=real_config.worker_count,
                error_message="Task Parallel benchmark was cancelled.",
            )

        worker_intervals: List[Tuple[float, float]] = []
        raw_durations: List[float] = []
        task_completions: List[Dict[str, Any]] = []

        for t_id, tr in b_res.task_results.items():
            if tr.start_timestamp is not None and tr.finish_timestamp is not None:
                worker_intervals.append((tr.start_timestamp, tr.finish_timestamp))
            if tr.compute_time_s is not None:
                raw_durations.append(tr.compute_time_s)
            task_completions.append({
                "task_id": t_id,
                "worker_id": tr.worker_id,
                "process_id": tr.worker_pid,
                "duration_s": round(tr.compute_time_s or 0.0, 6),
                "finish_timestamp": round(tr.finish_timestamp or 0.0, 6),
                "status": "COMPLETED" if tr.success else "FAILED",
            })

        window_start = min((s for s, e in worker_intervals), default=0.0)
        window_end = max((e for s, e in worker_intervals), default=b_res.makespan_s)
        if b_res.makespan_s > 0:
            window_end = max(window_end, window_start + b_res.makespan_s)

        int_metrics = compute_interval_metrics(
            window_start=window_start,
            window_end=window_end,
            worker_intervals=worker_intervals,
            raw_compute_durations=raw_durations,
        )

        # Telemetry
        final_rss = psutil.Process(os.getpid()).memory_info().rss
        peak_mb = max(0.0, (final_rss - initial_rss) / (1024 * 1024))
        if peak_mb <= 0.0:
            peak_mb = round(final_rss / (1024 * 1024), 2)

        return RealExecutionResult(
            status="completed" if b_res.sequential_verification_passed else "failed",
            wall_clock_time_s=b_res.makespan_s,
            worker_count=real_config.worker_count,
            worker_intervals=worker_intervals,
            aggregate_worker_compute_time_s=int_metrics.aggregate_worker_compute_time_s,
            compute_interval_union_s=int_metrics.compute_interval_union_s,
            no_worker_compute_time_s=int_metrics.no_worker_compute_time_s,
            sequential_baseline_s=b_res.sequential_time_s,
            actual_speedup=b_res.speedup,
            worker_utilization_pct=b_res.worker_utilization_pct,
            peak_memory_rss_mb=peak_mb,
            host_cpu_percent=round(psutil.cpu_percent(interval=None), 1),
            task_completions=task_completions,
            verification_passed=b_res.sequential_verification_passed,
            provenance=MetricClassification.DIRECTLY_MEASURED.value,
        )
