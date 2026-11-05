"""CoreSync Task Parallelism Subsystem.

Provides genuine CPU-bound heterogeneous task parallelism, DAG dependency resolution,
pluggable scheduling queues (FIFO, Priority, SJF), spawn worker pools, verification,
and 4-stage worker process lifecycle management.
"""

from engine.task_parallel.dispatcher import TaskDispatcher
from engine.task_parallel.executor import TaskParallelExecutor
from engine.task_parallel.operations import execute_task_kernel
from engine.task_parallel.presets import (
    PRESET_GENERATORS,
    create_diamond_pipeline,
    create_fan_out_fan_in_pipeline,
    create_fault_tolerant_test_dag,
    create_independent_benchmark_suite,
    create_scientific_suite,
)
from engine.task_parallel.result_collector import ResultCollector, TaskDAGResult
from engine.task_parallel.task import Task, TaskPriority, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from engine.task_parallel.task_queue import SchedulingPolicy, TaskQueue
from engine.task_parallel.verification import TaskVerificationResult, TaskVerifier
from engine.task_parallel.worker import TaskExecutionResult, TaskParcel

__all__ = [
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskGraph",
    "TaskQueue",
    "SchedulingPolicy",
    "TaskDispatcher",
    "TaskParallelExecutor",
    "TaskDAGResult",
    "ResultCollector",
    "TaskVerifier",
    "TaskVerificationResult",
    "TaskParcel",
    "TaskExecutionResult",
    "execute_task_kernel",
    "PRESET_GENERATORS",
]
