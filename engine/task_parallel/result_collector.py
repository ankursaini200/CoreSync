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
    """Comprehensive outcome of executing a complete Task Parallelism DAG."""
    success: bool
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    worker_count: int
    makespan_s: float               # End-to-end wall-clock parallel duration
    cumulative_compute_s: float     # Sum of pure computation times across all tasks
    speedup: float                  # cumulative_compute_s / makespan_s
    worker_utilization_pct: float   # (cumulative_compute_s / (makespan_s * worker_count)) * 100%
    task_results: Dict[str, TaskExecutionResult] = field(default_factory=dict)
    verifications: Dict[str, TaskVerificationResult] = field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None


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
        overall_error: Optional[str] = None,
    ) -> TaskDAGResult:
        """Synthesize final metrics across the entire DAG."""
        total = len(tasks)
        completed = sum(1 for t in tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in tasks.values() if t.status == TaskStatus.FAILED)
        cancelled = sum(1 for t in tasks.values() if t.status == TaskStatus.CANCELLED)

        # Cumulative compute time (sum of actual worker execution time)
        cumulative_compute = sum(
            r.compute_time_s for r in self.task_results.values() if r.success
        )

        # Speedup S = T_seq / T_par
        speedup = (cumulative_compute / makespan_s) if makespan_s > 0 else 0.0

        # Worker utilization: ratio of active compute time to total available worker time
        denom = (makespan_s * self.worker_count)
        utilization = (cumulative_compute / denom * 100.0) if denom > 0 else 0.0

        overall_success = (failed == 0 and cancelled == 0 and completed == total)

        return TaskDAGResult(
            success=overall_success,
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            cancelled_tasks=cancelled,
            worker_count=self.worker_count,
            makespan_s=makespan_s,
            cumulative_compute_s=cumulative_compute,
            speedup=speedup,
            worker_utilization_pct=min(100.0, utilization),
            task_results=dict(self.task_results),
            verifications=dict(self.verifications),
            execution_log=list(self.execution_log),
            error_message=overall_error,
        )

