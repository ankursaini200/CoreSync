"""Isolated Multiprocessing Worker Entrypoint for Data Parallelism.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes under Python multiprocessing 'spawn' context.
"""

from dataclasses import dataclass
import os
import sys
import time
import traceback
from typing import Any, Optional

from engine.data_parallel.operations import execute_chunk
from engine.process_manager import enable_parent_death_protection


@dataclass
class WorkerTask:
    """Task parcel dispatched from master process to worker process."""
    task_id: int
    worker_id: int
    op_id: str
    chunk_id: int
    data: Any
    extra_args: dict = None
    dispatch_timestamp: float = 0.0


@dataclass
class WorkerResult:
    """Result parcel returned from worker process to master process."""
    task_id: int
    worker_id: int
    chunk_id: int
    success: bool
    data: Any
    compute_time_s: float
    worker_pid: int = 0
    error_message: Optional[str] = None
    input_delivery_latency_s: float = 0.0  # Queue waiting, serialization/delivery, and worker wake-up / OS scheduling delay
    worker_start_time: float = 0.0
    worker_finish_time: float = 0.0

    @property
    def input_ipc_latency_s(self) -> float:
        """Backwards-compatible alias for input_delivery_latency_s."""
        return self.input_delivery_latency_s


def data_parallel_worker_loop(task_queue, result_queue, stop_event) -> None:
    """Continuous processing loop for an isolated data-parallel worker.

    Args:
        task_queue: multiprocessing.Queue providing WorkerTask instances or sentinel None.
        result_queue: multiprocessing.Queue returning WorkerResult instances.
        stop_event: multiprocessing.Event signaling immediate termination request.
    """
    worker_pid = os.getpid()
    enable_parent_death_protection(os.getppid())

    while not stop_event.is_set():
        try:
            # Poll with timeout to allow checking stop_event periodically
            task = task_queue.get(timeout=0.2)
        except Exception:
            # Timeout: loop and re-check stop_event
            continue

        if task is None:
            # Sentinel received: clean shutdown
            break

        if stop_event.is_set():
            break

        t_receive = time.perf_counter()
        # Delivery latency includes queue waiting, serialization/delivery, and worker wake-up / OS scheduling delay
        delivery_delay = (t_receive - task.dispatch_timestamp) if task.dispatch_timestamp > 0 else 0.0

        t_start = time.perf_counter()
        try:
            chunk_result = execute_chunk(task.op_id, task.data, task.extra_args)
            t_elapsed = time.perf_counter() - t_start
            t_finish = time.perf_counter()

            result_queue.put(WorkerResult(
                task_id=task.task_id,
                worker_id=task.worker_id,
                chunk_id=task.chunk_id,
                success=True,
                data=chunk_result,
                compute_time_s=t_elapsed,
                worker_pid=worker_pid,
                input_delivery_latency_s=max(0.0, delivery_delay),
                worker_start_time=t_start,
                worker_finish_time=t_finish,
            ))
        except Exception as e:
            t_elapsed = time.perf_counter() - t_start
            t_finish = time.perf_counter()
            err = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            result_queue.put(WorkerResult(
                task_id=task.task_id,
                worker_id=task.worker_id,
                chunk_id=task.chunk_id,
                success=False,
                data=None,
                compute_time_s=t_elapsed,
                worker_pid=worker_pid,
                error_message=err,
                input_delivery_latency_s=max(0.0, delivery_delay),
                worker_start_time=t_start,
                worker_finish_time=t_finish,
            ))
