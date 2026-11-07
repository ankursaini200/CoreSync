"""Tests for CoreSync Phase 10 Comparison Metrics, Concordance, and Equivalence Verification."""

import pytest
from engine.comparison.comparison_metrics import (
    ComparisonMetricsCalculator,
    compute_order_concordance,
    compute_comparison_analysis,
)
from engine.comparison.models import (
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealExecutionResult,
    RealSystemConfig,
    VirtualExecutionResult,
    VirtualLabConfig,
    assert_no_cross_domain_ratio,
)


def test_order_concordance_identical():
    """Verify order concordance returns 1.0 when completion order is identical."""
    real_order = ["Task-A", "Task-B", "Task-C", "Task-D"]
    virt_order = ["Task-A", "Task-B", "Task-C", "Task-D"]
    concordance = compute_order_concordance(real_order, virt_order)
    assert concordance == pytest.approx(1.0)


def test_order_concordance_reversed():
    """Verify order concordance for completely reversed completion order."""
    real_order = ["Task-A", "Task-B", "Task-C", "Task-D"]
    virt_order = ["Task-D", "Task-C", "Task-B", "Task-A"]
    concordance = compute_order_concordance(real_order, virt_order)
    assert concordance == pytest.approx(0.0)


def test_order_concordance_partial_and_edge_cases():
    """Verify order concordance with partial agreement and edge cases."""
    # Single element
    assert compute_order_concordance(["A"], ["A"]) == 1.0
    # Empty
    assert compute_order_concordance([], []) == 0.0
    # Disjoint sets
    assert compute_order_concordance(["A", "B"], ["C", "D"]) == 0.0

    # Partial
    c = compute_order_concordance(["A", "B", "C", "D"], ["A", "C", "B", "D"])
    assert 0.8 < c < 1.0


def test_resource_allocation_ratio_and_utilization_delta():
    """Verify mathematical derivations of resource ratio and utilization delta."""
    real_res = RealExecutionResult(
        status="completed",
        wall_clock_time_s=2.0,
        worker_count=2,
        worker_intervals=[(0.0, 1.0), (0.0, 1.0)],
        aggregate_worker_compute_time_s=3.2,
        compute_interval_union_s=1.8,
        no_worker_compute_time_s=0.2,
        worker_utilization_pct=80.0,
        peak_memory_rss_mb=45.0,
        task_completions=[
            {"task_id": "T1", "process_id": 101, "duration_s": 1.0},
            {"task_id": "T2", "process_id": 102, "duration_s": 1.0},
        ],
    )
    virt_res = VirtualExecutionResult(
        status="completed",
        virtual_makespan_ticks=200,
        simulated_clock_ticks=200,
        virtual_core_utilization_pct=65.0,
        virtual_core_count=4,
        task_completion_order=[
            {"task_id": "T1", "assigned_core_id": 0, "finish_tick": 100},
            {"task_id": "T2", "assigned_core_id": 1, "finish_tick": 100},
        ],
    )

    config = ComparisonConfiguration(
        comparison_id="metrics-test-01",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=ComparisonWorkloadConfig(
            workload_type=ComparisonWorkloadType.TASK_PARALLEL,
            workload_id="diamond",
            workload_name="Diamond DAG",
        ),
        real_config=RealSystemConfig(worker_count=2),
        virtual_config=VirtualLabConfig(virtual_core_count=4),
    )

    analysis = ComparisonMetricsCalculator.analyze(config, real_res, virt_res)

    # Resource Allocation Ratio: 2 workers / 4 virtual cores = 0.5
    assert analysis.resource_allocation_ratio == pytest.approx(0.5)
    # Utilization Delta: 80.0% - 65.0% = +15.0%
    assert analysis.utilization_difference_pct == pytest.approx(15.0)
    # Completion order concordance for identical T1, T2: 1.0
    assert analysis.completion_order_concordance == pytest.approx(1.0)
    # Workload Equivalence is certified
    assert analysis.workload_equivalence is True
    # Verify no cross-domain ratio was computed
    assert not hasattr(analysis, "cross_domain_speedup")
    assert not hasattr(analysis, "real_over_virtual_ratio")


def test_cross_domain_ratio_assertion_safety():
    """Verify that assert_no_cross_domain_ratio strictly prevents metric contamination."""
    with pytest.raises(ValueError, match="Invalid Cross-Domain Operation"):
        assert_no_cross_domain_ratio(1.23, 456)
