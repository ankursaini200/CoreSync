"""Comprehensive Test Suite for Task Parallelism Engine.

Tests DAG dependencies, cycle detection, pluggable scheduling policies,
isolated multiprocessing execution under spawn, retry policies, failure cascades,
cancellation, verification, and worker Qt isolation.
"""

import multiprocessing as mp
import subprocess
import sys
import time
import pytest

from engine.task_parallel.dispatcher import TaskDispatcher
from engine.task_parallel.executor import TaskParallelExecutor
from engine.task_parallel.operations import execute_task_kernel
from engine.task_parallel.presets import (
    create_diamond_pipeline,
    create_fan_out_fan_in_pipeline,
    create_fault_tolerant_test_dag,
    create_independent_benchmark_suite,
    create_scientific_suite,
)
from engine.task_parallel.task import Task, TaskPriority, TaskStatus
from engine.task_parallel.task_graph import TaskGraph
from engine.task_parallel.task_queue import SchedulingPolicy, TaskQueue
from engine.task_parallel.verification import TaskVerifier
from gui.task_parallelism import TaskParallelismPage


# --- 1. Task Model & State Machine Tests ---

def test_task_creation_and_defaults():
    """Verify Task dataclass defaults, IDs, and initial states."""
    t = Task(
        task_id="t_001",
        name="Unit Test Prime Sieve",
        task_type="prime_calc",
        params={"limit": 5000},
        priority=TaskPriority.HIGH,
    )
    assert t.task_id == "t_001"
    assert t.status == TaskStatus.PENDING
    assert t.priority == TaskPriority.HIGH
    assert t.dependencies == []
    assert t.retry_count == 0
    assert t.is_terminal() is False


def test_task_status_valid_transitions():
    """Verify permitted state transitions succeed and update timestamps."""
    t = Task("t_valid", "Valid Transitions", "sorting")
    assert t.status == TaskStatus.PENDING

    # PENDING -> READY
    assert t.transition_to(TaskStatus.READY) is True
    assert t.status == TaskStatus.READY

    # READY -> QUEUED
    assert t.transition_to(TaskStatus.QUEUED) is True
    assert t.status == TaskStatus.QUEUED

    # QUEUED -> RUNNING
    assert t.transition_to(TaskStatus.RUNNING) is True
    assert t.status == TaskStatus.RUNNING
    assert t.started_at > 0.0

    # RUNNING -> COMPLETED (terminal)
    assert t.transition_to(TaskStatus.COMPLETED) is True
    assert t.status == TaskStatus.COMPLETED
    assert t.completed_at >= t.started_at
    assert t.is_terminal() is True


def test_task_status_invalid_transitions_raise():
    """Verify that invalid transitions raise ValueError."""
    t = Task("t_invalid", "Invalid Transitions", "matrix_mult")
    # PENDING -> COMPLETED directly is invalid
    with pytest.raises(ValueError, match="cannot move from pending to completed"):
        t.transition_to(TaskStatus.COMPLETED)

    # Transition to READY
    t.transition_to(TaskStatus.READY)
    # READY -> COMPLETED directly is invalid
    with pytest.raises(ValueError, match="cannot move from ready to completed"):
        t.transition_to(TaskStatus.COMPLETED)


def test_task_retry_transition_cycle():
    """Verify FAILED -> READY is allowed for retries, but COMPLETED -> READY is not."""
    t = Task("t_retry", "Retry Test", "prime_calc")
    t.transition_to(TaskStatus.READY)
    t.transition_to(TaskStatus.QUEUED)
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.FAILED, reason="Connection dropped")

    # Allowed for retry
    assert t.transition_to(TaskStatus.READY) is True
    assert t.status == TaskStatus.READY

    # Progress to completed
    t.transition_to(TaskStatus.QUEUED)
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.COMPLETED)

    # Terminal state cannot transition back
    with pytest.raises(ValueError):
        t.transition_to(TaskStatus.READY)


# --- 2. Task Queue & Scheduling Policy Tests ---

def test_task_queue_fifo_policy():
    """Verify FIFO queue returns tasks strictly in arrival order."""
    queue = TaskQueue(policy=SchedulingPolicy.FIFO)
    t1 = Task("task_1", "First", "sorting", priority=TaskPriority.LOW)
    t2 = Task("task_2", "Second", "sorting", priority=TaskPriority.CRITICAL)
    t3 = Task("task_3", "Third", "sorting", priority=TaskPriority.NORMAL)

    t1.transition_to(TaskStatus.READY)
    t2.transition_to(TaskStatus.READY)
    t3.transition_to(TaskStatus.READY)

    queue.push(t1)
    queue.push(t2)
    queue.push(t3)

    assert queue.size() == 3
    assert queue.pop().task_id == "task_1"
    assert queue.pop().task_id == "task_2"
    assert queue.pop().task_id == "task_3"
    assert queue.is_empty() is True


def test_task_queue_priority_policy():
    """Verify Priority queue pops highest priority tasks first."""
    queue = TaskQueue(policy=SchedulingPolicy.PRIORITY)
    t_low = Task("t_low", "Low", "sorting", priority=TaskPriority.LOW)
    t_med = Task("t_med", "Med", "sorting", priority=TaskPriority.NORMAL)
    t_crit = Task("t_crit", "Critical", "sorting", priority=TaskPriority.CRITICAL)

    for t in [t_low, t_med, t_crit]:
        t.transition_to(TaskStatus.READY)
        queue.push(t)

    assert queue.pop().task_id == "t_crit"
    assert queue.pop().task_id == "t_med"
    assert queue.pop().task_id == "t_low"


def test_task_queue_sjf_policy():
    """Verify Shortest Job First queue pops smallest estimated duration first."""
    queue = TaskQueue(policy=SchedulingPolicy.SJF)
    t_long = Task("t_long", "Long Job", "matrix_mult", estimated_duration_s=2.5)
    t_short = Task("t_short", "Short Job", "sorting", estimated_duration_s=0.1)
    t_med = Task("t_med", "Medium Job", "prime_calc", estimated_duration_s=0.8)

    for t in [t_long, t_short, t_med]:
        t.transition_to(TaskStatus.READY)
        queue.push(t)

    assert queue.pop().task_id == "t_short"
    assert queue.pop().task_id == "t_med"
    assert queue.pop().task_id == "t_long"


# --- 3. DAG Dependency Graph & Validation Tests ---

def test_dag_topological_sort_and_validation():
    """Verify diamond DAG has valid topological order."""
    graph = create_diamond_pipeline()
    is_valid, err = graph.validate()
    assert is_valid is True
    assert err is None

    order = graph.get_topological_order()
    assert len(order) == 4
    # Root must come first
    assert order[0] == "t1_init"
    # Merge must come last
    assert order[-1] == "t4_reduce"


def test_dag_cycle_detection():
    """Verify circular dependency is detected and raises error."""
    graph = TaskGraph()
    t1 = Task("task_A", "A", "sorting", dependencies=["task_C"])
    t2 = Task("task_B", "B", "sorting", dependencies=["task_A"])
    t3 = Task("task_C", "C", "sorting", dependencies=["task_B"])

    graph.add_task(t1)
    graph.add_task(t2)
    graph.add_task(t3)

    assert graph.has_cycle() is True
    is_valid, err = graph.validate()
    assert is_valid is False
    assert "cycle" in err.lower()


def test_dag_self_dependency_rejected():
    """Verify self-dependency raises ValueError."""
    graph = TaskGraph()
    t = Task("self_dep", "Self", "sorting")
    graph.add_task(t)
    with pytest.raises(ValueError, match="Self-dependency"):
        graph.add_dependency("self_dep", "self_dep")


def test_dag_missing_dependency_rejected():
    """Verify reference to non-existent parent task fails validation."""
    graph = TaskGraph()
    t = Task("child", "Child", "sorting", dependencies=["ghost_parent"])
    graph.add_task(t)

    is_valid, err = graph.validate()
    assert is_valid is False
    assert "non-existent" in err


def test_dag_dependency_resolution_and_unblocking():
    """Verify child tasks transition from BLOCKED to READY only when all parents complete."""
    graph = create_diamond_pipeline()
    graph.initialize_statuses()

    assert graph.tasks["t1_init"].status == TaskStatus.READY
    assert graph.tasks["t2_matrix"].status == TaskStatus.BLOCKED
    assert graph.tasks["t3_primes"].status == TaskStatus.BLOCKED
    assert graph.tasks["t4_reduce"].status == TaskStatus.BLOCKED

    # Complete root task
    graph.tasks["t1_init"].transition_to(TaskStatus.QUEUED)
    graph.tasks["t1_init"].transition_to(TaskStatus.RUNNING)
    graph.tasks["t1_init"].transition_to(TaskStatus.COMPLETED)

    newly_ready = graph.on_task_completed("t1_init")
    ready_ids = {t.task_id for t in newly_ready}
    assert ready_ids == {"t2_matrix", "t3_primes"}

    # t4_reduce depends on BOTH t2 and t3, so completing only t2 must NOT unblock t4
    graph.tasks["t2_matrix"].transition_to(TaskStatus.QUEUED)
    graph.tasks["t2_matrix"].transition_to(TaskStatus.RUNNING)
    graph.tasks["t2_matrix"].transition_to(TaskStatus.COMPLETED)
    assert graph.on_task_completed("t2_matrix") == []
    assert graph.tasks["t4_reduce"].status == TaskStatus.BLOCKED

    # Now complete t3; t4 should unblock
    graph.tasks["t3_primes"].transition_to(TaskStatus.QUEUED)
    graph.tasks["t3_primes"].transition_to(TaskStatus.RUNNING)
    graph.tasks["t3_primes"].transition_to(TaskStatus.COMPLETED)
    unblocked = graph.on_task_completed("t3_primes")
    assert len(unblocked) == 1
    assert unblocked[0].task_id == "t4_reduce"
    assert graph.tasks["t4_reduce"].status == TaskStatus.READY


# --- 4. Computational Kernel Tests ---

def test_all_six_computational_kernels():
    """Verify that all 6 CPU-bound kernels execute and return valid data structures."""
    # 1. prime_calc
    res_prime = execute_task_kernel("prime_calc", {"limit": 1000})
    assert res_prime["count"] == 168
    assert res_prime["largest_prime"] == 997

    # 2. matrix_mult
    res_mat = execute_task_kernel("matrix_mult", {"size": 80, "seed": 42})
    assert res_mat["matrix_shape"] == [80, 80]
    assert res_mat["frobenius_norm"] > 0.0

    # 3. numerical_integration
    res_integ = execute_task_kernel("numerical_integration", {"intervals": 1000})
    assert isinstance(res_integ["integral"], float)

    # 4. sorting
    res_sort = execute_task_kernel("sorting", {"size": 5000, "seed": 99})
    assert res_sort["is_sorted"] is True
    assert res_sort["min"] <= res_sort["max"]

    # 5. fibonacci
    res_fib = execute_task_kernel("fibonacci", {"n": 1000})
    assert res_fib["digit_count"] > 200

    # 6. data_transform
    res_trans = execute_task_kernel("data_transform", {"size": 5000, "passes": 2})
    assert res_trans["std"] > 0.0


def test_kernel_simulated_failure():
    """Verify kernel throws exception when fail_flag or simulate_error is passed."""
    with pytest.raises(RuntimeError, match="Network timeout"):
        execute_task_kernel("sorting", {"simulate_error": "Network timeout"})


def test_task_verifiers():
    """Verify TaskVerifier mathematically checks results for all task types."""
    v1 = TaskVerifier.verify("t1", "prime_calc", {"count": 10, "largest_prime": 29})
    assert v1.passed is True

    v2 = TaskVerifier.verify("t2", "sorting", {"is_sorted": True, "min": -10.0, "max": 20.0})
    assert v2.passed is True

    v3 = TaskVerifier.verify("t3", "sorting", {"is_sorted": False, "min": 5.0, "max": 1.0})
    assert v3.passed is False


# --- 5. Multiprocessing Execution & Concurrency Tests ---

def test_diamond_dag_parallel_execution():
    """Verify end-to-end execution of a Diamond DAG on 2 spawn workers."""
    graph = create_diamond_pipeline()
    executor = TaskParallelExecutor()

    result = executor.run_dag(graph, worker_count=2, policy=SchedulingPolicy.FIFO)

    assert result.success is True
    assert result.total_tasks == 4
    assert result.completed_tasks == 4
    assert result.failed_tasks == 0
    assert result.cancelled_tasks == 0
    assert result.makespan_s > 0.0
    assert result.cumulative_compute_s > 0.0
    assert len(result.verifications) == 4
    assert all(v.passed for v in result.verifications.values())


def test_scientific_suite_execution():
    """Verify 7-task heterogeneous scientific suite across 3 workers."""
    graph = create_scientific_suite()
    executor = TaskParallelExecutor()

    result = executor.run_dag(graph, worker_count=3, policy=SchedulingPolicy.PRIORITY)

    assert result.success is True
    assert result.total_tasks == 7
    assert result.completed_tasks == 7
    assert result.failed_tasks == 0


def test_independent_suite_concurrent_execution():
    """Verify max concurrency across independent tasks."""
    graph = create_independent_benchmark_suite()
    executor = TaskParallelExecutor()

    result = executor.run_dag(graph, worker_count=4, policy=SchedulingPolicy.SJF)

    assert result.success is True
    assert result.total_tasks == 6
    assert result.completed_tasks == 6
    assert result.worker_count == 4


# --- 6. Fault Tolerance, Retries & Failure Cascades ---

def test_task_retries_and_failure_cascade():
    """Verify task retries up to max_retries, cascades failure to children, while independent branch succeeds."""
    graph = create_fault_tolerant_test_dag()
    executor = TaskParallelExecutor()

    result = executor.run_dag(graph, worker_count=2)

    assert result.success is False
    assert result.failed_tasks == 2  # failing task + dependent child
    assert result.completed_tasks == 2  # root + independent sibling

    # Verify retry count
    failing_task = graph.tasks["ft_failing"]
    assert failing_task.status == TaskStatus.FAILED
    assert failing_task.retry_count == 2
    assert failing_task.max_retries == 2

    # Verify dependent task was cascaded to FAILED
    dep_task = graph.tasks["ft_dependent"]
    assert dep_task.status == TaskStatus.FAILED
    assert "Prerequisite" in dep_task.error_message

    # Verify independent sibling succeeded
    sibling = graph.tasks["ft_sibling"]
    assert sibling.status == TaskStatus.COMPLETED


# --- 7. Cancellation & Clean Shutdown Tests ---

def test_cooperative_cancellation_and_zero_orphans():
    """Verify cancellation marks tasks CANCELLED and reaps all child worker processes."""
    graph = create_fan_out_fan_in_pipeline()
    executor = TaskParallelExecutor()
    cancel_event = mp.get_context("spawn").Event()

    # Cancel immediately
    cancel_event.set()
    result = executor.run_dag(graph, worker_count=2, cancel_event=cancel_event)

    assert result.success is False
    assert result.cancelled_tasks > 0
    assert len(executor._active_workers) == 0


def test_worker_isolation_from_qt():
    """Strict Architectural Rule: Verify worker modules do not import PySide6."""
    cmd = [
        sys.executable,
        "-c",
        "import engine.task_parallel.worker; import sys; assert 'PySide6' not in sys.modules, 'PySide6 found in worker!'",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Worker isolation assertion failed: {res.stderr}"


# --- 8. GUI Integration Tests ---

def test_task_parallelism_page_initialization(qapp):
    """Verify TaskParallelismPage instantiates cleanly with all widgets and defaults."""
    page = TaskParallelismPage()
    assert page.combo_preset.count() >= 5
    assert page.spin_workers.value() >= 1
    assert page.btn_run.isEnabled() is True
    assert page.btn_cancel.isEnabled() is False
    assert page.table_tasks.rowCount() == 4  # Default diamond pipeline
    page.shutdown()


def test_task_parallelism_page_preset_switching(qapp):
    """Verify switching presets updates table rows and canvas graph."""
    page = TaskParallelismPage()

    # Switch to Scientific Suite (7 tasks)
    page.combo_preset.setCurrentText("Scientific Suite (7 Tasks)")
    assert page.table_tasks.rowCount() == 7
    assert page.card_total.value_label.text() == "7"

    # Switch to Fan-Out / Fan-In (6 tasks)
    page.combo_preset.setCurrentText("Fan-Out / Fan-In Aggregation (6 Tasks)")
    assert page.table_tasks.rowCount() == 6
    assert page.card_total.value_label.text() == "6"
    page.shutdown()
