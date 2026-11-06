"""Data Parallel Multiprocessing Execution Engine.

Orchestrates sequential baseline execution, dataset partitioning, spawn-based worker pools,
scatter/gather IPC pipelines, verification, and speedup metrics calculation.
"""

from dataclasses import dataclass, field
import logging
import multiprocessing as mp
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from engine.affinity import (
    AffinityPolicy,
    resolve_worker_affinities,
    set_process_affinity,
)
from engine.process_manager import ProcessManager, WorkerLifecycleStatus
from utils.cpu_topology import CPUTopology
from utils.system_info import get_system_summary
from engine.data_parallel.operations import (
    OperationSpec,
    execute_chunk,
    generate_dataset,
    get_supported_operations,
)
from engine.data_parallel.partitioner import Chunk, DataPartitioner
from engine.data_parallel.result_collector import ResultCollector
from engine.data_parallel.verification import ResultVerifier, VerificationResult
from engine.data_parallel.worker import (
    WorkerResult,
    WorkerTask,
    data_parallel_worker_loop,
)

logger = logging.getLogger("CoreSync.DataParallel.Executor")


@dataclass
class ParallelTimingBreakdown:
    """Detailed non-overlapping latency metrics separating multiprocessing overheads.

    Sequential Phase Progression on Master Process:
        total_s = startup_s + dispatch_s + collection_s + merge_s

    Granular Decomposition:
        - startup_s: Time spent spawning child processes under 'spawn' context.
        - dispatch_s: Time spent partitioning data, packaging tasks, and serializing to IPC queue.
        - collection_s: Parallel Execution and Result Collection Window. Wall-clock interval
          gathering results from the worker pool. Note: worker computation overlaps with this interval.
        - compute_s: Primary compute window alias (collection_s).
        - merge_s: Time spent reassembling arrays or reducing scalar outputs.
        - total_s: End-to-end parallel wall-clock duration.
        - max_worker_compute_s: Pure computational duration on slowest worker (critical path).
        - avg_worker_compute_s: Average pure compute time across workers.
        - sum_worker_compute_s: Cumulative CPU compute time across all workers.
        - avg_input_delivery_latency_s: Average measured input delivery latency per chunk,
          encompassing queue waiting, serialization/delivery, and worker wake-up / OS scheduling delay.
        - estimated_distribution_overhead_s: Estimated Distribution and Collection Overhead.
          Derived residual estimate calculated as: T_dispatch + max(0, T_collection - max_worker_compute).
          Note: This is a derived residual estimate and may include OS scheduling and synchronization delays.
    """
    startup_s: float = 0.0             # Phase 1: Process spawn overhead
    dispatch_s: float = 0.0            # Phase 2: Input preparation, serialization & IPC dispatch
    collection_s: float = 0.0          # Phase 3: Parallel Execution and Result Collection Window (worker compute overlaps)
    compute_s: float = 0.0             # Primary compute window alias (collection_s)
    merge_s: float = 0.0               # Phase 4: Output reassembly & merge
    total_s: float = 0.0               # End-to-end parallel wall-clock duration

    # Granular Worker & Delivery Metrics
    max_worker_compute_s: float = 0.0  # Pure computation time of slowest worker (critical path)
    avg_worker_compute_s: float = 0.0  # Average pure compute time across all workers
    sum_worker_compute_s: float = 0.0  # Cumulative CPU compute time across all workers
    avg_input_delivery_latency_s: float = 0.0  # Average measured delivery latency per chunk (queue + IPC + wake-up)
    estimated_distribution_overhead_s: float = 0.0  # Derived residual estimate (dispatch + collection residual)

    @property
    def avg_input_ipc_s(self) -> float:
        """Backwards-compatible alias for avg_input_delivery_latency_s."""
        return self.avg_input_delivery_latency_s

    @property
    def ipc_overhead_s(self) -> float:
        """Backwards-compatible alias for estimated_distribution_overhead_s."""
        return self.estimated_distribution_overhead_s


@dataclass
class ParallelExecutionResult:
    """Consolidated parallel run outcome."""
    success: bool
    data: Any
    timings: ParallelTimingBreakdown
    worker_count: int
    chunks: List[Chunk]
    worker_results: List[WorkerResult]
    error_message: Optional[str] = None


@dataclass
class DataParallelBenchmarkResult:
    """Comprehensive benchmark comparing sequential vs parallel execution."""
    op_id: str
    op_name: str
    dataset_size: int
    worker_count: int
    chunks_count: int
    sequential_time_s: float
    parallel_time_s: float
    timings: ParallelTimingBreakdown
    speedup: float
    efficiency_pct: float
    throughput_items_per_s: float
    verification: VerificationResult
    chunks: List[Chunk]
    worker_results: List[WorkerResult]
    success: bool
    error_message: Optional[str] = None


class DataParallelExecutor:
    """High-performance data-parallel executor running across isolated spawn workers."""

    def __init__(self):
        self._ctx = mp.get_context("spawn")
        self._active_workers: List[mp.Process] = []
        self._active_stop_event: Optional[mp.Event] = None
        self._pm: Optional[ProcessManager] = None

    @staticmethod
    def determine_automatic_workers(dataset_size: int, op_id: str) -> int:
        """Dynamically compute optimal worker count based on system hardware and problem size.

        Avoids excessive worker creation on small workloads where process spawn overhead
        would dominate computation.
        """
        summary = get_system_summary()
        logical_cpus = summary.logical_cores or 4
        physical_cores = summary.physical_cores or max(1, logical_cpus // 2)

        # Workload-size heuristic
        if dataset_size <= 20_000:
            # Very small dataset: 1 or 2 workers to limit spawn overhead
            return min(2, logical_cpus)
        elif dataset_size <= 200_000:
            # Medium-small: up to physical cores or 4
            return min(4, physical_cores)
        elif dataset_size <= 1_000_000:
            # Medium-large: physical cores
            return min(physical_cores, logical_cpus)
        else:
            # Large dataset: utilize full logical core capacity (capped at 32)
            return min(logical_cpus, 32)

    def run_sequential(
        self,
        op_id: str,
        data: Any,
        extra_args: dict = None,
    ) -> Tuple[Any, float]:
        """Execute operation sequentially in the current process.

        Returns:
            Tuple of (result_data, elapsed_seconds).
        """
        t_start = time.perf_counter()
        result = execute_chunk(op_id, data, extra_args)
        elapsed = time.perf_counter() - t_start
        return result, elapsed

    def run_parallel(
        self,
        op_id: str,
        data: Any,
        worker_count: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[mp.Event] = None,
        extra_args: dict = None,
        affinity_policy: AffinityPolicy = AffinityPolicy.AUTOMATIC,
        custom_cpus: Optional[List[int]] = None,
        manual_affinity: Optional[Dict[int, List[int]]] = None,
        topology: Optional[CPUTopology] = None,
    ) -> ParallelExecutionResult:
        """Execute operation in parallel using a pool of isolated worker processes."""
        t_parallel_start = time.perf_counter()
        extra_args = extra_args or {}

        # 1. Determine dataset length and partition
        if op_id == "prime_count":
            # For prime count, data is (start_int, end_int)
            start_int, end_int = data
            total_items = max(0, end_int - start_int)
        else:
            total_items = len(data)

        if total_items == 0:
            # Empty dataset edge case
            op_spec = get_supported_operations()[op_id]
            empty_res = 0 if op_spec.is_reduction else np.array([])
            return ParallelExecutionResult(
                success=True,
                data=empty_res,
                timings=ParallelTimingBreakdown(total_s=0.0),
                worker_count=worker_count,
                chunks=[],
                worker_results=[],
            )

        # 2. Partition dataset
        chunks = DataPartitioner.partition_indices(total_items, worker_count)
        actual_worker_count = len(chunks)

        if progress_callback:
            progress_callback(0, actual_worker_count, f"Partitioned into {actual_worker_count} chunks. Spawning workers...")

        # 3. Setup multiprocessing queues & stop event
        t_spawn_start = time.perf_counter()
        affinities = resolve_worker_affinities(
            worker_count=actual_worker_count,
            policy=affinity_policy,
            topology=topology,
            manual_mapping=manual_affinity,
            custom_cpus=custom_cpus,
        )

        pm = ProcessManager(start_method="spawn")
        self._pm = pm
        task_queue = pm.ctx.Queue()
        result_queue = pm.ctx.Queue()
        stop_event = pm.cancel_event
        self._active_stop_event = stop_event

        workers: List[mp.Process] = []
        try:
            for w_id in range(actual_worker_count):
                aff = affinities[w_id] if w_id < len(affinities) else []
                p = pm.spawn_worker(
                    target=data_parallel_worker_loop,
                    args=(task_queue, result_queue, stop_event),
                    name=f"CoreSync-DP-Worker-{w_id}",
                    engine_name="DataParallel",
                    worker_id=f"DP-{w_id}",
                    affinity_cpus=aff,
                    task_or_chunk_id=f"chunk-{w_id}",
                    daemon=True,
                )
                workers.append(p)
            self._active_workers = workers

            t_spawn = time.perf_counter() - t_spawn_start

            # 4. Input Preparation & IPC Dispatch
            if progress_callback:
                progress_callback(0, actual_worker_count, f"Dispatched {actual_worker_count} tasks to worker pool...")

            t_dispatch_start = time.perf_counter()
            for chunk in chunks:
                if op_id == "prime_count":
                    chunk_data = (start_int + chunk.start_idx, start_int + chunk.end_idx)
                else:
                    chunk_data = data[chunk.start_idx:chunk.end_idx]

                t_task_dispatch = time.perf_counter()
                task = WorkerTask(
                    task_id=chunk.chunk_id,
                    worker_id=chunk.chunk_id % actual_worker_count,
                    op_id=op_id,
                    chunk_id=chunk.chunk_id,
                    data=chunk_data,
                    extra_args=extra_args,
                    dispatch_timestamp=t_task_dispatch,
                )
                task_queue.put(task)
            t_dispatch = time.perf_counter() - t_dispatch_start

            # 5. Parallel Execution & Result Gathering Window
            t_collection_start = time.perf_counter()
            results: List[WorkerResult] = []

            while len(results) < actual_worker_count:
                # Check cancellation request
                if cancel_event and cancel_event.is_set():
                    stop_event.set()
                    self._cleanup_workers(workers, timeout=0.5)
                    return ParallelExecutionResult(
                        success=False,
                        data=None,
                        timings=ParallelTimingBreakdown(),
                        worker_count=actual_worker_count,
                        chunks=chunks,
                        worker_results=results,
                        error_message="Execution cancelled by user.",
                    )

                # Check if any worker died abnormally (non-zero exitcode)
                for p in workers:
                    if not p.is_alive() and p.exitcode not in (0, None):
                        stop_event.set()
                        self._cleanup_workers(workers, timeout=0.5)
                        return ParallelExecutionResult(
                            success=False,
                            data=None,
                            timings=ParallelTimingBreakdown(),
                            worker_count=actual_worker_count,
                            chunks=chunks,
                            worker_results=results,
                            error_message=f"Worker process {p.pid} terminated unexpectedly (exitcode {p.exitcode}).",
                        )

                try:
                    res = result_queue.get(timeout=0.1)
                    results.append(res)
                    pm.update_worker_status(
                        f"DP-{res.worker_id}",
                        WorkerLifecycleStatus.COMPLETED if res.success else WorkerLifecycleStatus.FAILED,
                        error_message=res.error_message,
                    )
                    if progress_callback:
                        progress_callback(
                            len(results),
                            actual_worker_count,
                            f"Completed chunk {res.chunk_id + 1}/{actual_worker_count} (PID {res.worker_pid}) in {res.compute_time_s * 1000:.1f}ms",
                        )
                except Exception:
                    # Queue get timeout, continue polling
                    continue

            # Signal workers that work is complete
            stop_event.set()
            for _ in range(actual_worker_count):
                try:
                    task_queue.put(None, timeout=0.05)
                except Exception:
                    pass

            t_collection = time.perf_counter() - t_collection_start

            # 6. Merge & Aggregate Results
            op_spec = get_supported_operations()[op_id]
            merged_data, t_merge = ResultCollector.merge_results(
                results=results,
                chunks=chunks,
                is_reduction=op_spec.is_reduction,
            )

            t_total = time.perf_counter() - t_parallel_start

            # Granular worker compute and delivery calculations
            worker_compute_times = [r.compute_time_s for r in results]
            max_comp = max(worker_compute_times) if worker_compute_times else 0.0
            avg_comp = (sum(worker_compute_times) / len(worker_compute_times)) if worker_compute_times else 0.0
            sum_comp = sum(worker_compute_times)

            delivery_latencies = [r.input_delivery_latency_s for r in results if r.input_delivery_latency_s > 0]
            avg_delivery_latency = (sum(delivery_latencies) / len(delivery_latencies)) if delivery_latencies else 0.0

            # Estimated Distribution and Collection Overhead:
            # Derived residual estimate: T_dispatch + max(0, T_collection - max_comp).
            # Includes queue wait times, OS wake-up/scheduling, and synchronization delays.
            collection_residual_gap = max(0.0, t_collection - max_comp)
            est_distribution_overhead = t_dispatch + collection_residual_gap

            timings = ParallelTimingBreakdown(
                startup_s=t_spawn,
                dispatch_s=t_dispatch,
                collection_s=t_collection,
                compute_s=t_collection,
                merge_s=t_merge,
                total_s=t_total,
                max_worker_compute_s=max_comp,
                avg_worker_compute_s=avg_comp,
                sum_worker_compute_s=sum_comp,
                avg_input_delivery_latency_s=avg_delivery_latency,
                estimated_distribution_overhead_s=est_distribution_overhead,
            )

            return ParallelExecutionResult(
                success=True,
                data=merged_data,
                timings=timings,
                worker_count=actual_worker_count,
                chunks=chunks,
                worker_results=results,
            )

        finally:
            # Ensure all workers are reaped
            self._cleanup_workers(workers, timeout=1.0)
            self._active_workers.clear()
            self._active_stop_event = None

    def run_benchmark(
        self,
        op_id: str,
        data: Any,
        worker_count: int,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[mp.Event] = None,
        extra_args: dict = None,
        warm_up: bool = False,
        affinity_policy: AffinityPolicy = AffinityPolicy.AUTOMATIC,
        custom_cpus: Optional[List[int]] = None,
        manual_affinity: Optional[Dict[int, List[int]]] = None,
        topology: Optional[CPUTopology] = None,
    ) -> DataParallelBenchmarkResult:
        """Run full end-to-end benchmark: sequential baseline, parallel run, and verification."""
        op_specs = get_supported_operations()
        if op_id not in op_specs:
            raise ValueError(f"Unknown operation: '{op_id}'")
        spec = op_specs[op_id]

        dataset_size = (data[1] - data[0]) if op_id == "prime_count" else len(data)

        # Optional warm-up run (helps stabilize CPU cache / frequency governor)
        if warm_up and dataset_size > 0:
            if progress_callback:
                progress_callback(0, worker_count, "Executing warm-up run...")
            if op_id == "prime_count":
                warm_data = (data[0], data[0] + min(1000, dataset_size))
            else:
                warm_data = data[:min(1000, dataset_size)]
            self.run_sequential(op_id, warm_data, extra_args)

        # 1. Sequential Execution
        if progress_callback:
            progress_callback(0, worker_count, "Running sequential baseline...")

        if cancel_event and cancel_event.is_set():
            return self._abort_benchmark("Benchmark cancelled before start.")

        seq_data, t_seq = self.run_sequential(op_id, data, extra_args)

        if cancel_event and cancel_event.is_set():
            return self._abort_benchmark("Benchmark cancelled after sequential phase.")

        # 2. Parallel Execution
        par_result = self.run_parallel(
            op_id=op_id,
            data=data,
            worker_count=worker_count,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            extra_args=extra_args,
            affinity_policy=affinity_policy,
            custom_cpus=custom_cpus,
            manual_affinity=manual_affinity,
            topology=topology,
        )

        if not par_result.success:
            # Parallel run was cancelled or encountered an error
            return DataParallelBenchmarkResult(
                op_id=op_id,
                op_name=spec.name,
                dataset_size=dataset_size,
                worker_count=worker_count,
                chunks_count=len(par_result.chunks),
                sequential_time_s=t_seq,
                parallel_time_s=0.0,
                timings=ParallelTimingBreakdown(),
                speedup=0.0,
                efficiency_pct=0.0,
                throughput_items_per_s=0.0,
                verification=VerificationResult(
                    passed=False,
                    mismatch_count=1,
                    total_items=dataset_size,
                    max_difference=0.0,
                    mean_difference=0.0,
                    rtol=0.0,
                    atol=0.0,
                    status_message=par_result.error_message or "Parallel execution failed.",
                ),
                chunks=par_result.chunks,
                worker_results=par_result.worker_results,
                success=False,
                error_message=par_result.error_message,
            )

        # 3. Verification
        if progress_callback:
            progress_callback(worker_count, worker_count, "Verifying parallel result against sequential baseline...")

        verification = ResultVerifier.verify(
            sequential_result=seq_data,
            parallel_result=par_result.data,
            is_reduction=spec.is_reduction,
        )

        # 4. Metric Calculations
        t_par = par_result.timings.total_s
        speedup = (t_seq / t_par) if t_par > 0 else 0.0
        eff = (speedup / par_result.worker_count * 100.0) if par_result.worker_count > 0 else 0.0
        throughput = (dataset_size / t_par) if t_par > 0 else 0.0

        return DataParallelBenchmarkResult(
            op_id=op_id,
            op_name=spec.name,
            dataset_size=dataset_size,
            worker_count=par_result.worker_count,
            chunks_count=len(par_result.chunks),
            sequential_time_s=t_seq,
            parallel_time_s=t_par,
            timings=par_result.timings,
            speedup=speedup,
            efficiency_pct=eff,
            throughput_items_per_s=throughput,
            verification=verification,
            chunks=par_result.chunks,
            worker_results=par_result.worker_results,
            success=verification.passed,
            error_message=None if verification.passed else "Verification failed: output does not match sequential baseline.",
        )

    def cancel_active_execution(self) -> None:
        """Immediately trigger cancellation of any running parallel workers."""
        if self._active_stop_event:
            self._active_stop_event.set()
        if self._active_workers:
            self._cleanup_workers(self._active_workers, timeout=0.5)

    def _cleanup_workers(self, workers: List[mp.Process], timeout: float = 1.0) -> None:
        """Safely terminate child worker processes using unified ProcessManager."""
        if self._pm:
            self._pm.terminate_all(
                coop_timeout=min(0.2, timeout),
                term_timeout=min(0.3, timeout),
                kill_timeout=0.2,
            )
            self._pm = None
        elif workers:
            # Fallback direct termination
            t_end = time.time() + min(0.3, timeout)
            for p in workers:
                if p.is_alive():
                    rem = max(0.01, t_end - time.time())
                    p.join(timeout=rem)
            for p in workers:
                if p.is_alive():
                    try:
                        p.terminate()
                        p.join(timeout=0.2)
                    except Exception:
                        pass
            for p in workers:
                if p.is_alive():
                    try:
                        p.kill()
                        p.join(timeout=0.1)
                    except Exception:
                        pass

    def _abort_benchmark(self, message: str) -> DataParallelBenchmarkResult:
        return DataParallelBenchmarkResult(
            op_id="cancelled",
            op_name="Cancelled",
            dataset_size=0,
            worker_count=0,
            chunks_count=0,
            sequential_time_s=0.0,
            parallel_time_s=0.0,
            timings=ParallelTimingBreakdown(),
            speedup=0.0,
            efficiency_pct=0.0,
            throughput_items_per_s=0.0,
            verification=VerificationResult(
                passed=False,
                mismatch_count=0,
                total_items=0,
                max_difference=0.0,
                mean_difference=0.0,
                rtol=0.0,
                atol=0.0,
                status_message=message,
            ),
            chunks=[],
            worker_results=[],
            success=False,
            error_message=message,
        )
