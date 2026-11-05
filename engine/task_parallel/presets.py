"""Standard Task Parallelism DAG Presets and Workflow Templates.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
"""

from typing import Dict, List
from engine.task_parallel.task import Task, TaskPriority, TaskStatus
from engine.task_parallel.task_graph import TaskGraph


def create_diamond_pipeline() -> TaskGraph:
    """Create a 4-task Diamond DAG: Root -> 2 Parallel Branches -> Reduction."""
    graph = TaskGraph()

    t_root = Task(
        task_id="t1_init",
        name="Dataset Generation & Pre-processing",
        task_type="data_transform",
        params={"size": 120_000, "passes": 2, "seed": 42},
        priority=TaskPriority.HIGH,
        estimated_duration_s=0.15,
    )
    t_branch_a = Task(
        task_id="t2_matrix",
        name="Eigen & Matrix Transform",
        task_type="matrix_mult",
        params={"size": 220, "seed": 101},
        priority=TaskPriority.NORMAL,
        dependencies=["t1_init"],
        estimated_duration_s=0.25,
    )
    t_branch_b = Task(
        task_id="t3_primes",
        name="Entropy Prime Sieve",
        task_type="prime_calc",
        params={"limit": 45_000, "start": 2},
        priority=TaskPriority.NORMAL,
        dependencies=["t1_init"],
        estimated_duration_s=0.20,
    )
    t_merge = Task(
        task_id="t4_reduce",
        name="Pipeline Summary & Moments",
        task_type="data_transform",
        params={"size": 100_000, "passes": 3, "seed": 999},
        priority=TaskPriority.CRITICAL,
        dependencies=["t2_matrix", "t3_primes"],
        estimated_duration_s=0.18,
    )

    for t in [t_root, t_branch_a, t_branch_b, t_merge]:
        graph.add_task(t)

    return graph


def create_scientific_suite() -> TaskGraph:
    """Create a 7-task Heterogeneous Scientific Pipeline spanning all kernel types."""
    graph = TaskGraph()

    t1 = Task(
        task_id="t1_signal",
        name="Sensor Signal Conditioning",
        task_type="data_transform",
        params={"size": 100_000, "passes": 2, "seed": 12},
        priority=TaskPriority.HIGH,
        estimated_duration_s=0.12,
    )
    t2 = Task(
        task_id="t2_primes",
        name="Prime Hash Key Generation",
        task_type="prime_calc",
        params={"limit": 40_000, "start": 10},
        priority=TaskPriority.NORMAL,
        dependencies=["t1_signal"],
        estimated_duration_s=0.18,
    )
    t3 = Task(
        task_id="t3_matrix",
        name="Spatial Correlation Matrix",
        task_type="matrix_mult",
        params={"size": 200, "seed": 45},
        priority=TaskPriority.HIGH,
        dependencies=["t1_signal"],
        estimated_duration_s=0.22,
    )
    t4 = Task(
        task_id="t4_simpson",
        name="Oscillatory Simpson Integration",
        task_type="numerical_integration",
        params={"intervals": 80_000, "a": 0.0, "b": 10.0},
        priority=TaskPriority.NORMAL,
        dependencies=["t1_signal"],
        estimated_duration_s=0.16,
    )
    t5 = Task(
        task_id="t5_sort",
        name="Telemetry Quantile Sorting",
        task_type="sorting",
        params={"size": 160_000, "seed": 77},
        priority=TaskPriority.NORMAL,
        dependencies=["t2_primes"],
        estimated_duration_s=0.14,
    )
    t6 = Task(
        task_id="t6_fib",
        name="Large State Fibonacci Scale",
        task_type="fibonacci",
        params={"n": 22_000},
        priority=TaskPriority.LOW,
        dependencies=["t3_matrix"],
        estimated_duration_s=0.10,
    )
    t7 = Task(
        task_id="t7_final",
        name="Scientific Report Synthesis",
        task_type="data_transform",
        params={"size": 120_000, "passes": 3, "seed": 333},
        priority=TaskPriority.CRITICAL,
        dependencies=["t4_simpson", "t5_sort", "t6_fib"],
        estimated_duration_s=0.20,
    )

    for t in [t1, t2, t3, t4, t5, t6, t7]:
        graph.add_task(t)

    return graph


def create_fan_out_fan_in_pipeline() -> TaskGraph:
    """Create a 1 Root -> 4 Concurrent Workers -> 1 Aggregator DAG."""
    graph = TaskGraph()

    root = Task(
        task_id="root_distrib",
        name="Root Batch Preparation",
        task_type="data_transform",
        params={"size": 80_000, "passes": 1, "seed": 1},
        priority=TaskPriority.HIGH,
        estimated_duration_s=0.10,
    )
    graph.add_task(root)

    branches = [
        Task("b1_matrix", "Matrix Block 1", "matrix_mult", {"size": 180, "seed": 2}, TaskPriority.NORMAL, ["root_distrib"], 0.18),
        Task("b2_primes", "Prime Sieve Block 2", "prime_calc", {"limit": 35_000}, TaskPriority.NORMAL, ["root_distrib"], 0.15),
        Task("b3_sort", "Sorting Block 3", "sorting", {"size": 140_000, "seed": 4}, TaskPriority.NORMAL, ["root_distrib"], 0.12),
        Task("b4_integ", "Integration Block 4", "numerical_integration", {"intervals": 60_000}, TaskPriority.NORMAL, ["root_distrib"], 0.14),
    ]
    for b in branches:
        graph.add_task(b)

    agg = Task(
        task_id="agg_merge",
        name="Global Batch Aggregation",
        task_type="data_transform",
        params={"size": 100_000, "passes": 2, "seed": 5},
        priority=TaskPriority.CRITICAL,
        dependencies=[b.task_id for b in branches],
        estimated_duration_s=0.15,
    )
    graph.add_task(agg)
    return graph


def create_independent_benchmark_suite() -> TaskGraph:
    """Create 6 independent tasks (0 dependencies) for maximum concurrency & policy testing."""
    graph = TaskGraph()

    tasks = [
        Task("ind_prime", "Prime Sieve (70k)", "prime_calc", {"limit": 70_000}, TaskPriority.NORMAL, [], 0.35),
        Task("ind_matrix", "Dense Matrix Mult (280x280)", "matrix_mult", {"size": 280, "seed": 11}, TaskPriority.HIGH, [], 0.40),
        Task("ind_simpson", "Simpson Integration (120k)", "numerical_integration", {"intervals": 120_000}, TaskPriority.LOW, [], 0.22),
        Task("ind_sort", "QuickSort Array (250k)", "sorting", {"size": 250_000, "seed": 22}, TaskPriority.NORMAL, [], 0.20),
        Task("ind_fib", "Fibonacci Doubling (30k)", "fibonacci", {"n": 30_000}, TaskPriority.LOW, [], 0.15),
        Task("ind_trans", "Horner Transform (200k)", "data_transform", {"size": 200_000, "passes": 3}, TaskPriority.CRITICAL, [], 0.28),
    ]
    for t in tasks:
        graph.add_task(t)
    return graph


def create_fault_tolerant_test_dag() -> TaskGraph:
    """Create a DAG containing an injected failure with retries and dependency cascades."""
    graph = TaskGraph()

    root = Task("ft_root", "Pre-flight Health Check", "data_transform", {"size": 50_000, "passes": 1}, TaskPriority.NORMAL)
    graph.add_task(root)

    # Injected failing task with 2 retries
    failing = Task(
        task_id="ft_failing",
        name="Unstable Network Fetch (Injected Fault)",
        task_type="prime_calc",
        params={"limit": 10_000, "fail_flag": True, "simulate_error": "Connection reset by peer"},
        priority=TaskPriority.HIGH,
        dependencies=["ft_root"],
        max_retries=2,
    )
    graph.add_task(failing)

    # Dependent task that will be blocked/failed due to ft_failing
    dependent = Task(
        task_id="ft_dependent",
        name="Dependent Consumer (Will Cascade)",
        task_type="matrix_mult",
        params={"size": 150},
        dependencies=["ft_failing"],
    )
    graph.add_task(dependent)

    # Independent sibling that will succeed despite the failure
    sibling = Task(
        task_id="ft_sibling",
        name="Independent Processing Channel",
        task_type="sorting",
        params={"size": 100_000},
        dependencies=["ft_root"],
    )
    graph.add_task(sibling)

    return graph


PRESET_GENERATORS = {
    "Diamond Pipeline (4 Tasks)": create_diamond_pipeline,
    "Scientific Suite (7 Tasks)": create_scientific_suite,
    "Fan-Out / Fan-In Aggregation (6 Tasks)": create_fan_out_fan_in_pipeline,
    "Independent Concurrency Suite (6 Tasks)": create_independent_benchmark_suite,
    "Fault Tolerance & Retry Test (4 Tasks)": create_fault_tolerant_test_dag,
}

