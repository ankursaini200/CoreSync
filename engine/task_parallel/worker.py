"""Isolated Multiprocessing Worker Entrypoint for Task Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes under Python multiprocessing 'spawn' context.
"""

from dataclasses import dataclass
import os
import sys
import time
import traceback
from typing import Any, Optional

from engine.task_parallel.operations import execute_task_kernel
from engine.process_manager import enable_parent_death_protection


@dataclass
class TaskParcel:
    """Work package dispatched from master process to worker process."""
    task_id: str
    task_type: str
    params: dict
    worker_id: int
    attempt: int = 0
    dispatch_timestamp: float = 0.0


@dataclass
class TaskExecutionResult:
    """Execution outcome sent back from worker process to master process."""
    task_id: str
    worker_id: int
    worker_pid: int
    success: bool
    data: Any
    compute_time_s: float
    error_message: Optional[str] = None
    start_timestamp: float = 0.0
    finish_timestamp: float = 0.0
    input_delivery_latency_s: float = 0.0


def task_parallel_worker_loop(task_queue, result_queue, stop_event) -> None:
    """Continuous processing loop for an isolated task-parallel worker.

    Args:
        task_queue: multiprocessing.Queue providing TaskParcel instances or sentinel None.
        result_queue: multiprocessing.Queue returning TaskExecutionResult instances.
        stop_event: multiprocessing.Event signaling immediate termination.
    """
    worker_pid = os.getpid()
    enable_parent_death_protection(os.getppid())

    while not stop_event.is_set():
        try:
            # Poll with timeout to allow checking stop_event periodically
            parcel = task_queue.get(timeout=0.2)
        except Exception:
            continue

        if parcel is None:
            # Sentinel received: clean shutdown
            break

        if stop_event.is_set():
            break

        t_receive = time.perf_counter()
        delivery_latency = (t_receive - parcel.dispatch_timestamp) if parcel.dispatch_timestamp > 0 else 0.0

        t_start = time.perf_counter()
        try:
            kernel_output = execute_task_kernel(parcel.task_type, parcel.params)
            t_finish = time.perf_counter()
            t_compute = t_finish - t_start

            result_queue.put(TaskExecutionResult(
                task_id=parcel.task_id,
                worker_id=parcel.worker_id,
                worker_pid=worker_pid,
                success=True,
                data=kernel_output,
                compute_time_s=t_compute,
                error_message=None,
                start_timestamp=t_start,
                finish_timestamp=t_finish,
                input_delivery_latency_s=max(0.0, delivery_latency),
            ))
        except Exception as e:
            t_finish = time.perf_counter()
            t_compute = t_finish - t_start
            err = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            result_queue.put(TaskExecutionResult(
                task_id=parcel.task_id,
                worker_id=parcel.worker_id,
                worker_pid=worker_pid,
                success=False,
                data=None,
                compute_time_s=t_compute,
                error_message=err,
                start_timestamp=t_start,
                finish_timestamp=t_finish,
                input_delivery_latency_s=max(0.0, delivery_latency),
            ))

