"""Isolated worker process execution module for CoreSync.

CRITICAL DESIGN RULE:
This module MUST NEVER import PySide6, Qt, or any GUI libraries.
Workers execute in isolated child processes created via the 'spawn' context.
All communication occurs via standard multiprocessing primitives (Queues, Pipes, Events).
"""

import os
import sys
import time
from typing import Any, Callable, Dict, Optional, Tuple
import multiprocessing as mp
from multiprocessing.synchronize import Event as EventType

def check_worker_isolation() -> None:
    """Verify that PySide6/Qt is not loaded in this worker process."""
    assert "PySide6" not in sys.modules, "Fatal: PySide6 was loaded into worker process!"


def worker_init(worker_id: int, affinity: Optional[list[int]] = None) -> None:
    """Initialize worker process, configure CPU affinity, and verify isolation."""
    check_worker_isolation()
    if affinity:
        try:
            os.sched_setaffinity(0, affinity)
        except (AttributeError, OSError):
            pass


def dummy_sleep_worker(duration: float = 5.0) -> None:
    """Top-level picklable worker function for lifecycle testing."""
    time.sleep(duration)



def execute_data_chunk(
    chunk_id: int,
    func_name: str,
    data_chunk: Any,
    cancel_event: EventType,
) -> Dict[str, Any]:
    """Execute a single data-parallel chunk with cancellation checks.

    Returns:
        Dict with status, execution timing, worker PID, and output result.
    """
    pid = os.getpid()
    start_time_ns = time.perf_counter_ns()

    if cancel_event.is_set():
        return {
            "chunk_id": chunk_id,
            "status": "cancelled",
            "pid": pid,
            "result": None,
            "compute_time_ms": 0.0,
        }

    # Dynamic dispatch for supported math operations
    result = None
    if func_name == "square":
        result = data_chunk ** 2
    elif func_name == "sum":
        result = data_chunk.sum()
    elif func_name == "sqrt":
        import numpy as np
        result = np.sqrt(data_chunk)
    else:
        raise ValueError(f"Unknown workload function: {func_name}")

    end_time_ns = time.perf_counter_ns()
    compute_time_ms = (end_time_ns - start_time_ns) / 1_000_000.0

    return {
        "chunk_id": chunk_id,
        "status": "completed",
        "pid": pid,
        "result": result,
        "compute_time_ms": compute_time_ms,
    }


def worker_loop(
    worker_id: int,
    task_queue: mp.Queue,
    result_queue: mp.Queue,
    cancel_event: EventType,
    affinity: Optional[list[int]] = None,
) -> None:
    """Continuous worker loop processing tasks from a queue."""
    worker_init(worker_id, affinity)
    pid = os.getpid()

    while not cancel_event.is_set():
        try:
            # Poll with timeout to allow checking cancel_event
            task = task_queue.get(timeout=0.2)
        except Exception:
            continue

        if task is None:  # Poison pill / shutdown sentinel
            break

        task_id, func_name, data = task
        try:
            output = execute_data_chunk(task_id, func_name, data, cancel_event)
            result_queue.put(output)
        except Exception as e:
            result_queue.put({
                "chunk_id": task_id,
                "status": "error",
                "pid": pid,
                "error": str(e),
                "compute_time_ms": 0.0,
            })
