"""Result Collector and DAG Telemetry Aggregator for Task Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional

from engine.task_parallel.task import Task, TaskStatus
from engine.task_parallel.verification import TaskVerificationResult, TaskVerifier
from engine.task_parallel.worker import TaskExecutionResult


@dataclass
class TaskDAGResult:
    """Comprehensive outcome of executing a complete Task Parallelism DAG.

    Metrics Decomposition:
        - sequential_time_s: Wall-clock execution time of the sequential baseline (T_seq).
        - makespan_s: End-to-end wall-clock parallel DAG duration (T_par).
        - cumulative_compute_s: Sum of pure CPU computation times across all tasks (T_comp_sum).
        - actual_speedup: S = T_seq / T_par (Actual Speedup vs single-threaded baseline).
        - parallelism_ratio: P = T_comp_sum / T_par (Concurrency density).
        - worker_utilization_pct: U = (T_comp_sum / (worker_count * T_par)) * 100% (bounded 0%-100%).
    """
    success: bool
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    worker_count: int
    makespan_s: float                      # End-to-end wall-clock parallel duration (T_par)
    cumulative_compute_s: float            # Sum of pure computation times across all tasks (T_comp_sum)
    sequential_time_s: float = 0.0         # Wall-clock sequential baseline duration (T_seq)
    actual_speedup: float = 0.0            # S = T_seq / T_par (Actual Speedup)
    parallelism_ratio: float = 0.0         # P = T_comp_sum / T_par (Parallelism Ratio)
    worker_utilization_pct: float = 0.0    # U = (T_comp_sum / (T_par * worker_count)) * 100%
    sequential_verification_passed: bool = False
    task_results: Dict[str, TaskExecutionResult] = field(default_factory=dict)
    verifications: Dict[str, TaskVerificationResult] = field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def speedup(self) -> float:
        """Backwards-compatible alias for actual_speedup (or parallelism_ratio if sequential baseline was not measured)."""
        return self.actual_speedup if self.actual_speedup > 0.0 else self.parallelism_ratio


class ResultCollector:
    """Collects individual task outcomes and synthesizes DAG execution metrics."""

    def __init__(self, worker_count: int):
        self.worker_count = max(1, worker_count)
        self.task_results: Dict[str, TaskExecutionResult] = {}
        self.verifications: Dict[str, TaskVerificationResult] = {}
        self.execution_log: List[Dict[str, Any]] = []

    def record_result(self, task: Task, result: TaskExecutionResult) -> None:
        """Record completed or failed task outcome and verify output."""
        self.task_results[task.task_id] = result

        if result.success and result.data is not None:
            v_res = TaskVerifier.verify(task.task_id, task.task_type, result.data)
        else:
            v_res = TaskVerificationResult(
                task_id=task.task_id,
                task_type=task.task_type,
                passed=False,
                details=result.error_message or "Task failed execution",
            )
        self.verifications[task.task_id] = v_res

        self.execution_log.append({
            "timestamp": time.time(),
            "task_id": task.task_id,
            "name": task.name,
            "type": task.task_type,
            "status": "COMPLETED" if result.success else "FAILED",
            "worker_id": result.worker_id,
            "worker_pid": result.worker_pid,
            "compute_time_s": result.compute_time_s,
            "delivery_latency_s": result.input_delivery_latency_s,
            "verified": v_res.passed,
            "error": result.error_message,
        })

    def record_cancellation(self, task: Task, reason: str = "Execution cancelled") -> None:
        """Log cancellation event for a task."""
        self.execution_log.append({
            "timestamp": time.time(),
            "task_id": task.task_id,
            "name": task.name,
            "type": task.task_type,
            "status": "CANCELLED",
            "worker_id": task.assigned_worker_id,
            "worker_pid": task.worker_pid,
            "compute_time_s": 0.0,
            "delivery_latency_s": 0.0,
            "verified": False,
            "error": reason,
        })

    def synthesize_dag_result(
        self,
        tasks: Dict[str, Task],
        makespan_s: float,
        sequential_time_s: float = 0.0,
        sequential_verification_passed: bool = False,
        overall_error: Optional[str] = None,
    ) -> TaskDAGResult:
        """Synthesize final metrics across the entire DAG."""
        total = len(tasks)
        completed = sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks.values() if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in tasks.values() if t.status == TaskStatus.CANCELLED)
        overall_success = (failed == 0 and cancelled == 0 and completed == total)

        # Cumulative compute time (sum of actual worker execution time)
        cumulative_compute = sum(
            r.compute_time_s for r in self.task_results.values() if r.success
        )

        # 1. Parallelism Ratio P = Cumulative Worker Compute Time / Parallel Makespan
        parallelism_ratio = (cumulative_compute / makespan_s) if (makespan_s > 0 and overall_success) else 0.0

        # 2. Worker Utilization U = Cumulative Worker Busy Time / (Worker Count * Parallel Makespan)
        # Strictly bounded between 0.0% and 100.0%
        denom = (makespan_s * self.worker_count)
        if denom > 0 and overall_success:
            raw_util = (cumulative_compute / denom) * 100.0
            worker_utilization_pct = min(100.0, max(0.0, raw_util))
        else:
            worker_utilization_pct = 0.0

        # 3. Actual Speedup S = Sequential Baseline Time / Parallel Makespan
        # Reported only when both sequential and parallel runs succeed and verification passes
        if overall_success and sequential_time_s > 0 and makespan_s > 0:
            actual_speedup = sequential_time_s / makespan_s
        else:
            actual_speedup = 0.0

        return TaskDAGResult(
            success=overall_success,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            cancelled_tasks=cancelled,
            worker_count=self.worker_count,
            makespan_s=makespan_s,
            cumulative_compute_s=cumulative_compute,
            sequential_time_s=sequential_time_s,
            actual_speedup=actual_speedup,
            parallelism_ratio=parallelism_ratio,
            worker_utilization_pct=worker_utilization_pct,
            sequential_verification_passed=sequential_verification_passed,
            task_results=dict(self.task_results),
            verifications=dict(self.verifications),
            execution_log=list(self.execution_log),
            error_message=overall_error,
        )

