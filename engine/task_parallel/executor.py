"""Task Parallel Multiprocessing Execution Engine.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Executes DAG task graphs across isolated spawn worker processes with zero orphans.
"""

import logging
import multiprocessing as mp
import os
import signal
import time
from typing import Callable, Dict, List, Optional

from engine.task_parallel.dispatcher import TaskDispatcher
from engine.task_parallel.result_collector import ResultCollector, TaskDAGResult
from engine.task_parallel.task import Task, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from engine.task_parallel.task_queue import SchedulingPolicy
from engine.task_parallel.worker import (
    TaskExecutionResult,
    TaskParcel,
    task_parallel_worker_loop,
)

logger = logging.getLogger("CoreSync.TaskParallel.Executor")


class TaskParallelExecutor:
    """Executes heterogeneous task dependency graphs (DAGs) on isolated child processes."""

    def __init__(self):
        self._ctx = mp.get_context("spawn")
        self._active_workers: List[mp.Process] = []
        self._active_stop_event: Optional[mp.Event] = None
        self._cancel_requested: bool = False

    def cancel_active_execution(self) -> None:
        """Cooperatively request immediate cancellation of running tasks."""
        self._cancel_requested = True
        if self._active_stop_event:
            self._active_stop_event.set()

    def run_dag(
        self,
        graph: TaskGraph,
        worker_count: int = 4,
        policy: SchedulingPolicy = SchedulingPolicy.FIFO,
        task_status_callback: Optional[Callable[[Task, TaskStatus, Optional[str]], None]] = None,
        worker_status_callback: Optional[Callable[[int, int, str], None]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_event: Optional[mp.Event] = None,
    ) -> TaskDAGResult:
        """Execute a validated TaskGraph to completion using a pool of spawn worker processes.

        Args:
            graph: TaskGraph instance defining tasks and dependencies.
            worker_count: Number of worker processes to spawn.
            policy: Scheduling policy (FIFO, PRIORITY, SJF).
            task_status_callback: Called on each task state transition: (task, status, reason).
            worker_status_callback: Called on worker state changes: (worker_id, pid, status_msg).
            progress_callback: Called periodically: (completed_count, total_count, message).
            cancel_event: External multiprocessing.Event to monitor for user cancellation.

        Returns:
            TaskDAGResult containing full metrics, verifications, and execution logs.
        """
        self._cancel_requested = False
        t_dag_start = time.perf_counter()

        # 1. Graph validation
        is_valid, err_msg = graph.validate()
        if not is_valid:
            raise ValueError(f"TaskGraph validation failed: {err_msg}")

        # 2. Status initialization (roots -> READY, dependents -> BLOCKED)
        graph.initialize_statuses()
        for task in graph.tasks.values():
            if task_status_callback:
                task_status_callback(task, task.status, None)

        actual_worker_count = max(1, worker_count)
        dispatcher = TaskDispatcher(worker_count=actual_worker_count, policy=policy)
        collector = ResultCollector(worker_count=actual_worker_count)

        # 3. Create IPC channels and worker pool
        task_queue = self._ctx.Queue()
        result_queue = self._ctx.Queue()
        stop_event = self._ctx.Event()
        self._active_stop_event = stop_event

        workers: List[mp.Process] = []
        try:
            for w_id in range(actual_worker_count):
                p = self._ctx.Process(
                    target=task_parallel_worker_loop,
                    args=(task_queue, result_queue, stop_event),
                    daemon=True,
                )
                p.start()
                workers.append(p)
                dispatcher.register_worker_pid(w_id, p.pid)
                if worker_status_callback:
                    worker_status_callback(w_id, p.pid, "Idle")
            self._active_workers = workers

            # 4. Enqueue initial READY tasks
            for ready_task in graph.get_ready_tasks():
                dispatcher.queue.push(ready_task, update_status=True)
                if task_status_callback:
                    task_status_callback(ready_task, ready_task.status, None)

            total_tasks = len(graph.tasks)
            if progress_callback:
                progress_callback(0, total_tasks, f"Initialized DAG with {total_tasks} tasks on {actual_worker_count} workers.")

            # 5. Dynamic Dispatch & Completion Loop
            while not graph.is_all_terminal():
                # Check cancellation
                if (cancel_event and cancel_event.is_set()) or self._cancel_requested:
                    logger.info("Cancellation requested during DAG execution.")
                    stop_event.set()
                    # Cancel all non-terminal tasks
                    for t in graph.tasks.values():
                        if not t.is_terminal():
                            t.transition_to(TaskStatus.CANCELLED, reason="Execution cancelled by user")
                            collector.record_cancellation(t)
                            if task_status_callback:
                                task_status_callback(t, TaskStatus.CANCELLED, "User cancellation")
                    break

                # Dispatch ready tasks to available idle workers
                while dispatcher.has_idle_worker() and not dispatcher.queue.is_empty():
                    dispatch_pair = dispatcher.dispatch_next()
                    if not dispatch_pair:
                        break
                    task_to_run, assigned_w_id = dispatch_pair

                    task_to_run.transition_to(TaskStatus.RUNNING)
                    if task_status_callback:
                        task_status_callback(task_to_run, TaskStatus.RUNNING, None)
                    if worker_status_callback:
                        worker_status_callback(assigned_w_id, task_to_run.worker_pid, f"Running: {task_to_run.name}")

                    parcel = TaskParcel(
                        task_id=task_to_run.task_id,
                        task_type=task_to_run.task_type,
                        params=task_to_run.params,
                        worker_id=assigned_w_id,
                        attempt=task_to_run.retry_count,
                        dispatch_timestamp=time.perf_counter(),
                    )
                    task_queue.put(parcel)

                # Check if any worker died unexpectedly
                for p_idx, p in enumerate(workers):
                    if not p.is_alive() and p.exitcode not in (0, None):
                        logger.error(f"Worker PID {p.pid} terminated abnormally with exit code {p.exitcode}")
                        # Mark running task on this worker as failed
                        crashed_task_id = dispatcher.busy_workers.get(p_idx)
                        if crashed_task_id and crashed_task_id in graph.tasks:
                            c_task = graph.tasks[crashed_task_id]
                            err = f"Worker process {p.pid} crashed with exitcode {p.exitcode}"
                            c_task.transition_to(TaskStatus.FAILED, reason=err)
                            collector.record_result(c_task, TaskExecutionResult(
                                task_id=c_task.task_id,
                                worker_id=p_idx,
                                worker_pid=p.pid,
                                success=False,
                                data=None,
                                compute_time_s=0.0,
                                error_message=err,
                            ))
                            graph.on_task_failed(c_task.task_id, err)
                            if task_status_callback:
                                task_status_callback(c_task, TaskStatus.FAILED, err)

                # Poll result queue
                try:
                    res: TaskExecutionResult = result_queue.get(timeout=0.05)
                except Exception:
                    # Timeout: check deadlock before continuing
                    if graph.check_deadlock(active_worker_count=len(dispatcher.busy_workers)):
                        logger.error("Deadlock detected: unresolved dependencies with no active workers.")
                        for t in graph.tasks.values():
                            if not t.is_terminal():
                                t.transition_to(TaskStatus.FAILED, reason="Deadlock: unresolved prerequisites")
                                collector.record_result(t, TaskExecutionResult(
                                    task_id=t.task_id,
                                    worker_id=-1,
                                    worker_pid=0,
                                    success=False,
                                    data=None,
                                    compute_time_s=0.0,
                                    error_message="Deadlock: unresolved prerequisites",
                                ))
                                if task_status_callback:
                                    task_status_callback(t, TaskStatus.FAILED, "Deadlock")
                        break
                    continue

                # Process task outcome
                finished_task = graph.tasks.get(res.task_id)
                if finished_task:
                    dispatcher.on_worker_finished(res.worker_id, finished_task.task_id)
                    if worker_status_callback:
                        worker_status_callback(res.worker_id, res.worker_pid, "Idle")

                    if res.success:
                        finished_task.result = res.data
                        finished_task.transition_to(TaskStatus.COMPLETED)
                        collector.record_result(finished_task, res)
                        if task_status_callback:
                            task_status_callback(finished_task, TaskStatus.COMPLETED, None)

                        # Unblock dependent children
                        newly_ready = graph.on_task_completed(finished_task.task_id)
                        for n_task in newly_ready:
                            dispatcher.queue.push(n_task, update_status=True)
                            if task_status_callback:
                                task_status_callback(n_task, TaskStatus.QUEUED, None)

                    else:
                        # Task failed: Check retry eligibility
                        if finished_task.retry_count < finished_task.max_retries:
                            finished_task.retry_count += 1
                            logger.warning(
                                f"Task '{finished_task.task_id}' failed. Retrying "
                                f"({finished_task.retry_count}/{finished_task.max_retries})..."
                            )
                            # Safe retry state transition: FAILED -> READY -> QUEUED
                            finished_task.transition_to(TaskStatus.FAILED, reason=res.error_message)
                            finished_task.transition_to(TaskStatus.READY)
                            dispatcher.queue.push(finished_task, update_status=True)
                            if task_status_callback:
                                task_status_callback(
                                    finished_task, TaskStatus.QUEUED,
                                    f"Retrying (Attempt {finished_task.retry_count})",
                                )
                        else:
                            # Retries exhausted: mark FAILED and cascade failure
                            finished_task.transition_to(TaskStatus.FAILED, reason=res.error_message)
                            collector.record_result(finished_task, res)
                            if task_status_callback:
                                task_status_callback(finished_task, TaskStatus.FAILED, res.error_message)

                            cascaded = graph.on_task_failed(finished_task.task_id, res.error_message or "Unknown failure")
                            for c_task in cascaded:
                                if task_status_callback:
                                    task_status_callback(c_task, c_task.status, c_task.error_message)

                    # Update progress
                    completed_count = sum(1 for t in graph.tasks.values() if t.status == TaskStatus.COMPLETED)
                    if progress_callback:
                        progress_callback(
                            completed_count,
                            total_tasks,
                            f"Task {finished_task.name} ({finished_task.status.value.upper()}) in {res.compute_time_s * 1000:.1f}ms",
                        )

            # 6. Shut down workers cleanly
            stop_event.set()
            for _ in range(actual_worker_count):
                try:
                    task_queue.put(None, timeout=0.05)
                except Exception:
                    pass

            t_dag_total = time.perf_counter() - t_dag_start
            return collector.synthesize_dag_result(graph.tasks, makespan_s=t_dag_total)

        finally:
            # 7. Guaranteed 4-stage worker cleanup (prevents any zombie or orphan processes)
            self._cleanup_workers(workers, timeout=1.0)
            self._active_workers.clear()
            self._active_stop_event = None

    def _cleanup_workers(self, workers: List[mp.Process], timeout: float = 1.0) -> None:
        """Strict 4-stage worker shutdown: cooperative join -> SIGTERM -> SIGKILL -> final join."""
        if not workers:
            return

        # Stage 1: Cooperative join
        deadline = time.time() + (timeout * 0.4)
        for p in workers:
            if p.is_alive():
                remaining = max(0.02, deadline - time.time())
                p.join(timeout=remaining)

        alive = [p for p in workers if p.is_alive()]
        if not alive:
            return

        # Stage 2: SIGTERM
        for p in alive:
            try:
                p.terminate()
            except Exception:
                pass

        deadline = time.time() + (timeout * 0.3)
        for p in alive:
            if p.is_alive():
                remaining = max(0.02, deadline - time.time())
                p.join(timeout=remaining)

        alive = [p for p in alive if p.is_alive()]
        if not alive:
            return

        # Stage 3: SIGKILL
        for p in alive:
            try:
                p.kill()
            except Exception:
                pass

        # Stage 4: Final join to reap zombies
        for p in alive:
            try:
                p.join(timeout=0.2)
            except Exception:
                pass

