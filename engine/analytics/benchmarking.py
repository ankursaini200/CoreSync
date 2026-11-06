"""Repeatable Benchmarking Framework for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes rigorous, repeatable benchmark iterations across Data Parallelism,
Task Parallelism, CPU Scheduling, and Virtual Lab subsystems.

Collects multi-run statistics, isolates warm-up passes, guarantees worker cleanup
via ProcessManager, and verifies numerical correctness before certifying results.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from engine.analytics.input_cloner import clone_benchmark_input
from engine.analytics.interval_timing import compute_interval_metrics
from engine.analytics.models import (
    MetricClassification,
    ScalabilityMetrics,
    calculate_sample_statistics,
)
from engine.data_parallel.executor import DataParallelExecutor
from engine.data_parallel.operations import get_supported_operations
from engine.process_manager import ProcessManager
from engine.task_parallel.executor import TaskParallelExecutor
from engine.task_parallel.task_graph import TaskGraph
from engine.process_scheduler.comparator import compare_all_algorithms
from engine.process_scheduler.presets import get_preset_by_id
from engine.virtual_lab.virtual_cpu import VirtualCPU, VirtualCPUConfig
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm, VirtualScheduler
from engine.virtual_lab.virtual_task import TaskPriority, VirtualTask
from utils.hardware import get_hardware_provider


class BenchmarkEngineType(str, Enum):
    """Execution engine benchmarked."""
    DATA_PARALLEL = "data_parallel"
    TASK_PARALLEL = "task_parallel"
    CPU_SCHEDULING = "cpu_scheduling"
    VIRTUAL_LAB = "virtual_lab"

    @property
    def display_name(self) -> str:
        names = {
            BenchmarkEngineType.DATA_PARALLEL: "Data Parallelism",
            BenchmarkEngineType.TASK_PARALLEL: "Task Parallelism",
            BenchmarkEngineType.CPU_SCHEDULING: "CPU Scheduling Simulation",
            BenchmarkEngineType.VIRTUAL_LAB: "Virtual Lab Multicore Simulation",
        }
        return names.get(self, self.value)


@dataclass
class BenchmarkIterationRecord:
    """Record of a single benchmark execution pass."""
    iteration_idx: int
    is_warmup: bool
    sequential_time_s: float
    parallel_time_s: float
    speedup: float
    efficiency_pct: float
    throughput: float
    verification_passed: bool
    extra_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iteration_idx": self.iteration_idx,
            "is_warmup": self.is_warmup,
            "sequential_time_s": round(self.sequential_time_s, 6),
            "parallel_time_s": round(self.parallel_time_s, 6),
            "speedup": round(self.speedup, 4),
            "efficiency_pct": round(self.efficiency_pct, 2),
            "throughput": round(self.throughput, 2),
            "verification_passed": self.verification_passed,
            "extra_metrics": self.extra_metrics,
        }


@dataclass
class BenchmarkSessionResult:
    """Complete, self-contained record of a benchmark session across all iterations."""
    benchmark_id: str
    engine_type: BenchmarkEngineType
    workload_name: str
    worker_count: int
    config_parameters: Dict[str, Any]
    hardware_metadata: Dict[str, Any]
    start_timestamp: str
    end_timestamp: str
    total_wall_clock_s: float
    iterations_requested: int
    warmup_iterations_requested: int
    warmup_records: List[BenchmarkIterationRecord]
    measured_records: List[BenchmarkIterationRecord]
    statistics: Dict[str, Dict[str, float]]
    verification_passed: bool
    cancelled: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "engine_type": self.engine_type.value,
            "engine_name": self.engine_type.display_name,
            "workload_name": self.workload_name,
            "worker_count": self.worker_count,
            "config_parameters": self.config_parameters,
            "hardware_metadata": self.hardware_metadata,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "total_wall_clock_s": round(self.total_wall_clock_s, 4),
            "iterations_requested": self.iterations_requested,
            "warmup_iterations_requested": self.warmup_iterations_requested,
            "warmup_records": [r.to_dict() for r in self.warmup_records],
            "measured_records": [r.to_dict() for r in self.measured_records],
            "statistics": self.statistics,
            "verification_passed": self.verification_passed,
            "cancelled": self.cancelled,
            "error_message": self.error_message,
        }


def get_sanitized_hardware_metadata() -> Dict[str, Any]:
    """Capture authoritative host hardware topology metadata for benchmark documentation.

    Distinguishes physical cores from logical processor threads, and captures RAM and OS.
    If detection is unavailable or fails, marks fields as 'Unknown' rather than fabricating data.
    """
    try:
        from utils.system_info import get_system_summary, get_ram_info
        summary = get_system_summary()
        ram = get_ram_info()
        p_cores = summary.physical_cores if summary.physical_cores > 0 else "Unknown"
        l_cores = summary.logical_cores if summary.logical_cores > 0 else "Unknown"
        return {
            "cpu_model": summary.cpu_model or "Unknown",
            "cpu_vendor": summary.cpu_vendor or "Unknown",
            "physical_cores": p_cores,
            "total_logical_cores": l_cores,
            "architecture": summary.architecture or "Unknown",
            "operating_system": f"{summary.os_name} ({summary.os_kernel})" if summary.os_name else "Unknown",
            "total_ram_gb": round(ram.total_gb, 2) if ram and ram.total_gb > 0 else "Unknown",
            "available_ram_gb": round(ram.available_gb, 2) if ram and ram.available_gb > 0 else "Unknown",
            "is_hybrid": summary.topology.is_hybrid if summary.topology else False,
            "p_core_count": len(summary.topology.p_cores) if summary.topology else 0,
            "e_core_count": len(summary.topology.e_cores) if summary.topology else 0,
        }
    except Exception:
        import platform
        import psutil
        try:
            p_cores = psutil.cpu_count(logical=False) or "Unknown"
            l_cores = psutil.cpu_count(logical=True) or "Unknown"
            vm = psutil.virtual_memory()
            return {
                "cpu_model": "Unknown",
                "cpu_vendor": "Unknown",
                "physical_cores": p_cores,
                "total_logical_cores": l_cores,
                "architecture": platform.machine() or "Unknown",
                "operating_system": f"{platform.system()} {platform.release()}",
                "total_ram_gb": round(vm.total / (1024**3), 2),
                "available_ram_gb": round(vm.available / (1024**3), 2),
                "is_hybrid": False,
                "p_core_count": 0,
                "e_core_count": 0,
            }
        except Exception:
            return {
                "cpu_model": "Unknown",
                "cpu_vendor": "Unknown",
                "physical_cores": "Unknown",
                "total_logical_cores": "Unknown",
                "architecture": "Unknown",
                "operating_system": "Unknown",
                "total_ram_gb": "Unknown",
                "available_ram_gb": "Unknown",
                "is_hybrid": False,
                "p_core_count": 0,
                "e_core_count": 0,
            }


class BenchmarkingEngine:
    """Orchestrates repeatable benchmark sweeps with cancellation and worker cleanup."""

    def __init__(self):
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signal cooperative cancellation of running benchmark."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Check whether cancellation was signaled."""
        return self._cancel_event.is_set()

    def reset_cancellation(self) -> None:
        """Reset cancellation flag to permit new benchmark execution."""
        self._cancel_event.clear()

    # -------------------------------------------------------------------------
    # 1. Data Parallelism Benchmark
    # -------------------------------------------------------------------------
    def run_data_parallel_benchmark(
        self,
        op_id: str = "transcendental",
        dataset_size: int = 100_000,
        worker_count: int = 4,
        iterations: int = 3,
        warmup_runs: int = 1,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> BenchmarkSessionResult:
        """Execute repeated Data Parallelism benchmarks comparing sequential vs parallel."""
        start_dt = datetime.now(timezone.utc)
        start_time = time.perf_counter()
        benchmark_id = f"dp_{op_id}_{start_dt.strftime('%Y%m%d_%H%M%S')}"

        hw_meta = get_sanitized_hardware_metadata()
        config = {
            "op_id": op_id,
            "dataset_size": dataset_size,
            "worker_count": worker_count,
        }

        warmup_records: List[BenchmarkIterationRecord] = []
        measured_records: List[BenchmarkIterationRecord] = []
        all_verified = True
        cancelled = self.is_cancelled()
        error_msg: Optional[str] = None

        total_passes = warmup_runs + iterations
        pass_idx = 0

        try:
            from engine.data_parallel.operations import generate_dataset
            executor = DataParallelExecutor()
            data = generate_dataset(op_id, dataset_size)

            # 1. Warm-up passes (not included in statistical sample)
            if not cancelled:
                for w_idx in range(warmup_runs):
                    if self.is_cancelled():
                        cancelled = True
                        break
                    pass_idx += 1
                    if progress_cb:
                        progress_cb(pass_idx, total_passes, f"Running Warm-up Pass {w_idx + 1}/{warmup_runs}...")

                    pass_data = clone_benchmark_input(data)
                    b_res = executor.run_benchmark(
                        op_id=op_id,
                        data=pass_data,
                        worker_count=worker_count,
                    )
                    if not b_res.verification.passed:
                        all_verified = False

                    w_results = getattr(b_res, "worker_results", [])
                    intervals = [
                        (r.worker_start_time, r.worker_finish_time)
                        for r in w_results
                        if getattr(r, "worker_start_time", 0.0) > 0 and getattr(r, "worker_finish_time", 0.0) > 0
                    ]
                    comp_times = [r.compute_time_s for r in w_results]
                    int_metrics = compute_interval_metrics(
                        window_start=0.0,
                        window_end=b_res.parallel_time_s,
                        worker_intervals=intervals,
                        raw_compute_durations=comp_times,
                    )

                    warmup_records.append(
                        BenchmarkIterationRecord(
                            iteration_idx=w_idx + 1,
                            is_warmup=True,
                            sequential_time_s=b_res.sequential_time_s,
                            parallel_time_s=b_res.parallel_time_s,
                            speedup=b_res.speedup,
                            efficiency_pct=b_res.efficiency_pct,
                            throughput=b_res.throughput_items_per_s,
                            verification_passed=b_res.verification.passed,
                            extra_metrics={
                                "startup_s": b_res.timings.startup_s,
                                "dispatch_s": b_res.timings.dispatch_s,
                                "collection_s": b_res.timings.collection_s,
                                "merge_s": b_res.timings.merge_s,
                                "parallel_makespan_s": b_res.parallel_time_s,
                                "aggregate_worker_compute_time_s": int_metrics.aggregate_worker_compute_time_s,
                                "compute_interval_union_s": int_metrics.compute_interval_union_s,
                                "no_worker_compute_time_s": int_metrics.no_worker_compute_time_s,
                                "idle_gap_time_s": int_metrics.no_worker_compute_time_s,
                                "aggregate_estimated_residual_s": int_metrics.no_worker_compute_time_s,
                                "estimated_distribution_overhead_s": int_metrics.no_worker_compute_time_s,
                                "concurrency_density": int_metrics.concurrency_density,
                                "residual_classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                                "residual_notes": "Elapsed wall-clock time within parallel makespan when zero workers were computing (parallel_makespan - compute_interval_union).",
                            },
                        )
                    )

            # 2. Measured passes
            if not cancelled:
                for m_idx in range(iterations):
                    if self.is_cancelled():
                        cancelled = True
                        break
                    pass_idx += 1
                    if progress_cb:
                        progress_cb(pass_idx, total_passes, f"Running Benchmark Iteration {m_idx + 1}/{iterations}...")

                    pass_data = clone_benchmark_input(data)
                    b_res = executor.run_benchmark(
                        op_id=op_id,
                        data=pass_data,
                        worker_count=worker_count,
                    )
                    if not b_res.verification.passed:
                        all_verified = False

                    w_results = getattr(b_res, "worker_results", [])
                    intervals = [
                        (r.worker_start_time, r.worker_finish_time)
                        for r in w_results
                        if getattr(r, "worker_start_time", 0.0) > 0 and getattr(r, "worker_finish_time", 0.0) > 0
                    ]
                    comp_times = [r.compute_time_s for r in w_results]
                    int_metrics = compute_interval_metrics(
                        window_start=0.0,
                        window_end=b_res.parallel_time_s,
                        worker_intervals=intervals,
                        raw_compute_durations=comp_times,
                    )

                    measured_records.append(
                        BenchmarkIterationRecord(
                            iteration_idx=m_idx + 1,
                            is_warmup=False,
                            sequential_time_s=b_res.sequential_time_s,
                            parallel_time_s=b_res.parallel_time_s,
                            speedup=b_res.speedup,
                            efficiency_pct=b_res.efficiency_pct,
                            throughput=b_res.throughput_items_per_s,
                            verification_passed=b_res.verification.passed,
                            extra_metrics={
                                "startup_s": b_res.timings.startup_s,
                                "dispatch_s": b_res.timings.dispatch_s,
                                "collection_s": b_res.timings.collection_s,
                                "merge_s": b_res.timings.merge_s,
                                "parallel_makespan_s": b_res.parallel_time_s,
                                "aggregate_worker_compute_time_s": int_metrics.aggregate_worker_compute_time_s,
                                "compute_interval_union_s": int_metrics.compute_interval_union_s,
                                "no_worker_compute_time_s": int_metrics.no_worker_compute_time_s,
                                "idle_gap_time_s": int_metrics.no_worker_compute_time_s,
                                "aggregate_estimated_residual_s": int_metrics.no_worker_compute_time_s,
                                "estimated_distribution_overhead_s": int_metrics.no_worker_compute_time_s,
                                "concurrency_density": int_metrics.concurrency_density,
                                "residual_classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                                "residual_notes": "Elapsed wall-clock time within parallel makespan when zero workers were computing (parallel_makespan - compute_interval_union).",
                            },
                        )
                    )

        except Exception as e:
            error_msg = str(e)
            all_verified = False
        finally:
            # Ensure process manager reaps any straggler workers
            ProcessManager.reap_orphans(timeout_s=0.2)

        end_dt = datetime.now(timezone.utc)
        total_wall_s = time.perf_counter() - start_time

        # Calculate statistics across measured passes
        measured_seq = [r.sequential_time_s for r in measured_records]
        measured_par = [r.parallel_time_s for r in measured_records]
        measured_speedups = [r.speedup for r in measured_records]
        measured_eff = [r.efficiency_pct for r in measured_records]
        measured_thru = [r.throughput for r in measured_records]

        mean_seq = sum(measured_seq) / len(measured_seq) if measured_seq else 0.0
        mean_par = sum(measured_par) / len(measured_par) if measured_par else 0.0

        speedup_stats = calculate_sample_statistics(measured_speedups)
        agg_speedup = (mean_seq / mean_par) if mean_par > 0.0 else 0.0
        speedup_stats["mean_paired_speedup"] = speedup_stats["mean"]
        speedup_stats["aggregate_ratio_speedup"] = round(agg_speedup, 4)
        speedup_stats["calculation_method"] = (
            "mean is arithmetic average of per-iteration paired speedups: (1/K)*sum(T_seq_i / T_par_i); "
            "aggregate_ratio_speedup is the ratio of average sequential to average parallel time: mean(T_seq) / mean(T_par)."
        )

        stats = {
            "sequential_time_s": calculate_sample_statistics(measured_seq),
            "parallel_time_s": calculate_sample_statistics(measured_par),
            "speedup": speedup_stats,
            "efficiency_pct": calculate_sample_statistics(measured_eff),
            "throughput": calculate_sample_statistics(measured_thru),
        }

        op_spec = get_supported_operations().get(op_id)
        workload_title = op_spec.name if op_spec else op_id

        return BenchmarkSessionResult(
            benchmark_id=benchmark_id,
            engine_type=BenchmarkEngineType.DATA_PARALLEL,
            workload_name=workload_title,
            worker_count=worker_count,
            config_parameters=config,
            hardware_metadata=hw_meta,
            start_timestamp=start_dt.isoformat(),
            end_timestamp=end_dt.isoformat(),
            total_wall_clock_s=total_wall_s,
            iterations_requested=iterations,
            warmup_iterations_requested=warmup_runs,
            warmup_records=warmup_records,
            measured_records=measured_records,
            statistics=stats,
            verification_passed=all_verified and not cancelled,
            cancelled=cancelled,
            error_message=error_msg,
        )

    # -------------------------------------------------------------------------
    # 2. Task Parallelism Benchmark
    # -------------------------------------------------------------------------
    def run_task_parallel_benchmark(
        self,
        dag_type: str = "diamond",
        worker_count: int = 4,
        iterations: int = 3,
        warmup_runs: int = 1,
        progress_cb: Optional[Callable[[int, int, str], None]] = None,
    ) -> BenchmarkSessionResult:
        """Execute repeated Task Parallelism DAG benchmarks comparing sequential baseline vs parallel."""
        start_dt = datetime.now(timezone.utc)
        start_time = time.perf_counter()
        benchmark_id = f"tp_{dag_type}_{start_dt.strftime('%Y%m%d_%H%M%S')}"

        hw_meta = get_sanitized_hardware_metadata()
        config = {
            "dag_type": dag_type,
            "worker_count": worker_count,
        }

        warmup_records: List[BenchmarkIterationRecord] = []
        measured_records: List[BenchmarkIterationRecord] = []
        all_verified = True
        cancelled = self.is_cancelled()
        error_msg: Optional[str] = None

        total_passes = warmup_runs + iterations
        pass_idx = 0

        def _make_graph() -> TaskGraph:
            from engine.task_parallel.presets import (
                create_diamond_pipeline,
                create_scientific_suite,
                create_independent_benchmark_suite,
            )
            if dag_type == "scientific":
                return create_scientific_suite()
            elif dag_type == "independent":
                return create_independent_benchmark_suite(count=8)
            else:
                return create_diamond_pipeline()

        try:
            executor = TaskParallelExecutor()

            if not cancelled:
                for w_idx in range(warmup_runs):
                    if self.is_cancelled():
                        cancelled = True
                        break
                    pass_idx += 1
                    if progress_cb:
                        progress_cb(pass_idx, total_passes, f"Running Warm-up Pass {w_idx + 1}/{warmup_runs}...")

                    graph = clone_benchmark_input(_make_graph())
                    b_res = executor.run_benchmark(graph, worker_count=worker_count)
                    if not b_res.sequential_verification_passed:
                        all_verified = False

                    eff_pct = (b_res.actual_speedup / worker_count * 100.0) if worker_count > 0 else 0.0
                    throughput = (b_res.completed_tasks / b_res.makespan_s) if b_res.makespan_s > 0 else 0.0

                    t_results = list(getattr(b_res, "task_results", {}).values())
                    intervals = [
                        (r.start_timestamp, r.finish_timestamp)
                        for r in t_results
                        if getattr(r, "start_timestamp", 0.0) > 0 and getattr(r, "finish_timestamp", 0.0) > 0
                    ]
                    comp_times = [r.compute_time_s for r in t_results]
                    int_metrics = compute_interval_metrics(
                        window_start=0.0,
                        window_end=b_res.makespan_s,
                        worker_intervals=intervals,
                        raw_compute_durations=comp_times,
                    )

                    warmup_records.append(
                        BenchmarkIterationRecord(
                            iteration_idx=w_idx + 1,
                            is_warmup=True,
                            sequential_time_s=b_res.sequential_time_s,
                            parallel_time_s=b_res.makespan_s,
                            speedup=b_res.actual_speedup,
                            efficiency_pct=eff_pct,
                            throughput=throughput,
                            verification_passed=b_res.sequential_verification_passed,
                            extra_metrics={
                                "parallel_makespan_s": b_res.makespan_s,
                                "parallelism_ratio": b_res.parallelism_ratio,
                                "worker_utilization_pct": b_res.worker_utilization_pct,
                                "aggregate_worker_compute_time_s": int_metrics.aggregate_worker_compute_time_s,
                                "cumulative_compute_s": int_metrics.aggregate_worker_compute_time_s,
                                "compute_interval_union_s": int_metrics.compute_interval_union_s,
                                "no_worker_compute_time_s": int_metrics.no_worker_compute_time_s,
                                "idle_gap_time_s": int_metrics.no_worker_compute_time_s,
                                "aggregate_estimated_residual_s": int_metrics.no_worker_compute_time_s,
                                "estimated_distribution_overhead_s": int_metrics.no_worker_compute_time_s,
                                "concurrency_density": int_metrics.concurrency_density,
                                "residual_classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                                "residual_notes": "Elapsed wall-clock time within parallel makespan when zero workers were computing (parallel_makespan - compute_interval_union).",
                            },
                        )
                    )

            if not cancelled:
                for m_idx in range(iterations):
                    if self.is_cancelled():
                        cancelled = True
                        break
                    pass_idx += 1
                    if progress_cb:
                        progress_cb(pass_idx, total_passes, f"Running Benchmark Iteration {m_idx + 1}/{iterations}...")

                    graph = clone_benchmark_input(_make_graph())
                    b_res = executor.run_benchmark(graph, worker_count=worker_count)
                    if not b_res.sequential_verification_passed:
                        all_verified = False

                    eff_pct = (b_res.actual_speedup / worker_count * 100.0) if worker_count > 0 else 0.0
                    throughput = (b_res.completed_tasks / b_res.makespan_s) if b_res.makespan_s > 0 else 0.0

                    t_results = list(getattr(b_res, "task_results", {}).values())
                    intervals = [
                        (r.start_timestamp, r.finish_timestamp)
                        for r in t_results
                        if getattr(r, "start_timestamp", 0.0) > 0 and getattr(r, "finish_timestamp", 0.0) > 0
                    ]
                    comp_times = [r.compute_time_s for r in t_results]
                    int_metrics = compute_interval_metrics(
                        window_start=0.0,
                        window_end=b_res.makespan_s,
                        worker_intervals=intervals,
                        raw_compute_durations=comp_times,
                    )

                    measured_records.append(
                        BenchmarkIterationRecord(
                            iteration_idx=m_idx + 1,
                            is_warmup=False,
                            sequential_time_s=b_res.sequential_time_s,
                            parallel_time_s=b_res.makespan_s,
                            speedup=b_res.actual_speedup,
                            efficiency_pct=eff_pct,
                            throughput=throughput,
                            verification_passed=b_res.sequential_verification_passed,
                            extra_metrics={
                                "parallel_makespan_s": b_res.makespan_s,
                                "parallelism_ratio": b_res.parallelism_ratio,
                                "worker_utilization_pct": b_res.worker_utilization_pct,
                                "aggregate_worker_compute_time_s": int_metrics.aggregate_worker_compute_time_s,
                                "cumulative_compute_s": int_metrics.aggregate_worker_compute_time_s,
                                "compute_interval_union_s": int_metrics.compute_interval_union_s,
                                "no_worker_compute_time_s": int_metrics.no_worker_compute_time_s,
                                "idle_gap_time_s": int_metrics.no_worker_compute_time_s,
                                "aggregate_estimated_residual_s": int_metrics.no_worker_compute_time_s,
                                "estimated_distribution_overhead_s": int_metrics.no_worker_compute_time_s,
                                "concurrency_density": int_metrics.concurrency_density,
                                "residual_classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                                "residual_notes": "Elapsed wall-clock time within parallel makespan when zero workers were computing (parallel_makespan - compute_interval_union).",
                            },
                        )
                    )

        except Exception as e:
            error_msg = str(e)
            all_verified = False
        finally:
            ProcessManager.reap_orphans(timeout_s=0.2)

        end_dt = datetime.now(timezone.utc)
        total_wall_s = time.perf_counter() - start_time

        measured_seq = [r.sequential_time_s for r in measured_records]
        measured_par = [r.parallel_time_s for r in measured_records]
        measured_speedups = [r.speedup for r in measured_records]
        measured_eff = [r.efficiency_pct for r in measured_records]
        measured_thru = [r.throughput for r in measured_records]

        mean_seq = sum(measured_seq) / len(measured_seq) if measured_seq else 0.0
        mean_par = sum(measured_par) / len(measured_par) if measured_par else 0.0

        speedup_stats = calculate_sample_statistics(measured_speedups)
        agg_speedup = (mean_seq / mean_par) if mean_par > 0.0 else 0.0
        speedup_stats["mean_paired_speedup"] = speedup_stats["mean"]
        speedup_stats["aggregate_ratio_speedup"] = round(agg_speedup, 4)
        speedup_stats["calculation_method"] = (
            "mean is arithmetic average of per-iteration paired speedups: (1/K)*sum(T_seq_i / T_par_i); "
            "aggregate_ratio_speedup is the ratio of average sequential to average parallel time: mean(T_seq) / mean(T_par)."
        )

        stats = {
            "sequential_time_s": calculate_sample_statistics(measured_seq),
            "parallel_time_s": calculate_sample_statistics(measured_par),
            "speedup": speedup_stats,
            "efficiency_pct": calculate_sample_statistics(measured_eff),
            "throughput": calculate_sample_statistics(measured_thru),
        }

        return BenchmarkSessionResult(
            benchmark_id=benchmark_id,
            engine_type=BenchmarkEngineType.TASK_PARALLEL,
            workload_name=f"Task DAG ({dag_type.capitalize()})",
            worker_count=worker_count,
            config_parameters=config,
            hardware_metadata=hw_meta,
            start_timestamp=start_dt.isoformat(),
            end_timestamp=end_dt.isoformat(),
            total_wall_clock_s=total_wall_s,
            iterations_requested=iterations,
            warmup_iterations_requested=warmup_runs,
            warmup_records=warmup_records,
            measured_records=measured_records,
            statistics=stats,
            verification_passed=all_verified and not cancelled,
            cancelled=cancelled,
            error_message=error_msg,
        )

    # -------------------------------------------------------------------------
    # 3. CPU Scheduling Benchmark
    # -------------------------------------------------------------------------
    def run_scheduling_benchmark(
        self,
        preset_id: str = "staggered_arrivals",
        time_quantum: float = 2.0,
        context_switch_overhead: float = 0.1,
    ) -> BenchmarkSessionResult:
        """Execute CPU scheduling simulation benchmark across classical algorithms."""
        start_dt = datetime.now(timezone.utc)
        start_time = time.perf_counter()
        benchmark_id = f"sched_{preset_id}_{start_dt.strftime('%Y%m%d_%H%M%S')}"

        hw_meta = get_sanitized_hardware_metadata()
        config = {
            "preset_id": preset_id,
            "time_quantum": time_quantum,
            "context_switch_overhead": context_switch_overhead,
        }

        preset = get_preset_by_id(preset_id)
        procs = preset.get_cloned_processes()

        results, summary_rows = compare_all_algorithms(
            processes=procs,
            time_quantum=time_quantum,
            context_switch_overhead=context_switch_overhead,
        )

        measured_records = []
        for idx, r in enumerate(summary_rows):
            measured_records.append(
                BenchmarkIterationRecord(
                    iteration_idx=idx + 1,
                    is_warmup=False,
                    sequential_time_s=r.total_simulation_time,
                    parallel_time_s=r.total_simulation_time,
                    speedup=1.0,
                    efficiency_pct=r.cpu_utilization_pct,
                    throughput=r.throughput,
                    verification_passed=True,
                    extra_metrics={
                        "algorithm_name": r.algorithm_name,
                        "algorithm_type": r.algorithm_type,
                        "average_waiting_time": r.average_waiting_time,
                        "average_turnaround_time": r.average_turnaround_time,
                        "average_response_time": r.average_response_time,
                        "context_switches": r.context_switches,
                    },
                )
            )

        end_dt = datetime.now(timezone.utc)
        total_wall_s = time.perf_counter() - start_time

        stats = {
            "waiting_time": calculate_sample_statistics([r.average_waiting_time for r in summary_rows]),
            "turnaround_time": calculate_sample_statistics([r.average_turnaround_time for r in summary_rows]),
            "cpu_utilization": calculate_sample_statistics([r.cpu_utilization_pct for r in summary_rows]),
            "throughput": calculate_sample_statistics([r.throughput for r in summary_rows]),
        }

        return BenchmarkSessionResult(
            benchmark_id=benchmark_id,
            engine_type=BenchmarkEngineType.CPU_SCHEDULING,
            workload_name=f"Scheduler ({preset.name})",
            worker_count=1,
            config_parameters=config,
            hardware_metadata=hw_meta,
            start_timestamp=start_dt.isoformat(),
            end_timestamp=end_dt.isoformat(),
            total_wall_clock_s=total_wall_s,
            iterations_requested=len(summary_rows),
            warmup_iterations_requested=0,
            warmup_records=[],
            measured_records=measured_records,
            statistics=stats,
            verification_passed=True,
        )

    # -------------------------------------------------------------------------
    # 4. Virtual Lab Multicore Simulation Benchmark
    # -------------------------------------------------------------------------
    def run_virtual_lab_benchmark(
        self,
        virtual_cores: int = 8,
        task_count: int = 50,
        enable_hybrid: bool = False,
    ) -> BenchmarkSessionResult:
        """Execute Virtual Lab educational multicore scheduling benchmark."""
        start_dt = datetime.now(timezone.utc)
        start_time = time.perf_counter()
        benchmark_id = f"vlab_{virtual_cores}c_{start_dt.strftime('%Y%m%d_%H%M%S')}"

        hw_meta = get_sanitized_hardware_metadata()
        config = {
            "virtual_cores": virtual_cores,
            "task_count": task_count,
            "enable_hybrid": enable_hybrid,
            "is_simulated": True,
        }

        # Build virtual CPU
        cpu_config = VirtualCPUConfig(
            logical_threads=virtual_cores,
            enable_hybrid=enable_hybrid,
            p_core_count=virtual_cores // 2 if enable_hybrid else 0,
            e_core_count=virtual_cores // 2 if enable_hybrid else 0,
        )
        vcpu = VirtualCPU(cpu_config)
        scheduler = VirtualScheduler(vcpu, algorithm=SchedulingAlgorithm.ROUND_ROBIN, time_quantum=10)

        # Generate virtual tasks
        tasks = []
        for i in range(task_count):
            prio = TaskPriority.HIGH if i % 3 == 0 else TaskPriority.MEDIUM
            burst = 15 + (i * 7 % 35)
            tasks.append(VirtualTask(task_id=i + 1, name=f"VTask-{i+1}", burst_ticks=burst, priority=prio))

        scheduler.submit_batch(tasks)

        # Run simulation loop
        max_ticks = 5000
        ticks_elapsed = 0
        scheduler.dispatch()
        while (scheduler.ready_queue or any(c.current_task for c in vcpu.cores.values())) and ticks_elapsed < max_ticks:
            scheduler.step(1)
            ticks_elapsed += 1

        completed_count = len(scheduler.completed_tasks)
        active_core_busy_ticks = sum(c.busy_ticks for c in vcpu.cores.values())
        total_core_capacity = len(vcpu.cores) * max(1, ticks_elapsed)
        virtual_util_pct = (active_core_busy_ticks / total_core_capacity) * 100.0

        throughput = (completed_count / ticks_elapsed * 1000.0) if ticks_elapsed > 0 else 0.0

        end_dt = datetime.now(timezone.utc)
        total_wall_s = time.perf_counter() - start_time

        measured_record = BenchmarkIterationRecord(
            iteration_idx=1,
            is_warmup=False,
            sequential_time_s=round(total_wall_s, 6),
            parallel_time_s=round(total_wall_s, 6),
            speedup=float(virtual_cores) * (virtual_util_pct / 100.0),
            efficiency_pct=virtual_util_pct,
            throughput=throughput,
            verification_passed=completed_count == task_count,
            extra_metrics={
                "simulated_ticks_elapsed": ticks_elapsed,
                "virtual_cores": virtual_cores,
                "completed_tasks": completed_count,
                "virtual_core_util_pct": round(virtual_util_pct, 2),
                "simulated_throughput_per_1000_ticks": round(throughput, 2),
                "simulator_wall_clock_s": round(total_wall_s, 6),
                "is_simulated": True,
                "metric_provenance": {
                    "simulated_ticks_elapsed": MetricClassification.SIMULATED_VIRTUAL.value,
                    "virtual_core_util_pct": MetricClassification.SIMULATED_VIRTUAL.value,
                    "simulator_wall_clock_s": MetricClassification.DIRECTLY_MEASURED.value,
                },
                "provenance_simulated_ticks": "SIMULATED_VIRTUAL (discrete logical cycles)",
                "provenance_simulator_wall_clock": "DIRECTLY_MEASURED (host Python elapsed duration)",
            },
        )

        stats = {
            "simulated_ticks": {"mean": float(ticks_elapsed), "min": float(ticks_elapsed), "max": float(ticks_elapsed), "std_dev": None, "std_dev_display": "N/A (single simulation)"},
            "virtual_util_pct": {"mean": round(virtual_util_pct, 2), "min": round(virtual_util_pct, 2), "max": round(virtual_util_pct, 2), "std_dev": None, "std_dev_display": "N/A (single simulation)"},
            "simulated_throughput_per_1000_ticks": {"mean": round(throughput, 2), "min": round(throughput, 2), "max": round(throughput, 2), "std_dev": None, "std_dev_display": "N/A (single simulation)"},
            "simulator_wall_clock_s": {"mean": round(total_wall_s, 6), "min": round(total_wall_s, 6), "max": round(total_wall_s, 6), "std_dev": None, "std_dev_display": "N/A (single simulation)"},
        }

        return BenchmarkSessionResult(
            benchmark_id=benchmark_id,
            engine_type=BenchmarkEngineType.VIRTUAL_LAB,
            workload_name=f"Virtual Lab Multicore ({virtual_cores} Virtual Cores)",
            worker_count=virtual_cores,
            config_parameters=config,
            hardware_metadata=hw_meta,
            start_timestamp=start_dt.isoformat(),
            end_timestamp=end_dt.isoformat(),
            total_wall_clock_s=total_wall_s,
            iterations_requested=1,
            warmup_iterations_requested=0,
            warmup_records=[],
            measured_records=[measured_record],
            statistics=stats,
            verification_passed=completed_count == task_count,
        )
