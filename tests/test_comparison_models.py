"""Tests for CoreSync Phase 10 Comparison Models, Data Structures, and Clock Domain Isolation."""

import pytest
from engine.comparison.models import (
    ComparisonExecutionMode,
    ComparisonWorkloadType,
    ComparisonWorkloadConfig,
    RealSystemConfig,
    VirtualLabConfig,
    ComparisonConfiguration,
    RealExecutionResult,
    VirtualExecutionResult,
    ComparisonAnalysis,
    ComparisonSessionResult,
    assert_no_cross_domain_ratio,
)
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm


def test_comparison_configuration_round_trip():
    """Verify full serialization and deserialization round trip of ComparisonConfiguration."""
    workload = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="transcendental",
        workload_name="Transcendental (sin/cos/exp)",
        dataset_size=10000,
        task_count=4,
        extra_params={"intensity": 2.0},
    )
    real_cfg = RealSystemConfig(
        worker_count=4,
        timeout_s=30.0,
    )
    virt_cfg = VirtualLabConfig(
        virtual_core_count=8,
        enable_hybrid=True,
        p_core_count=4,
        e_core_count=4,
        p_core_speed=1.5,
        e_core_speed=0.8,
        scheduling_algorithm=SchedulingAlgorithm.ROUND_ROBIN,
        time_quantum=4,
    )
    config = ComparisonConfiguration(
        comparison_id="test-session-123",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=workload,
        real_config=real_cfg,
        virtual_config=virt_cfg,
    )

    d = config.to_dict()
    assert d["comparison_id"] == "test-session-123"
    assert d["execution_mode"] == "compare_both"
    assert d["workload"]["workload_id"] == "transcendental"
    assert d["real_config"]["worker_count"] == 4
    assert d["virtual_config"]["scheduling_algorithm"] == "ROUND_ROBIN"
    assert d["virtual_config"]["enable_hybrid"] is True

    # Reconstitute
    reconstructed = ComparisonConfiguration.from_dict(d)
    assert reconstructed.comparison_id == config.comparison_id
    assert reconstructed.execution_mode == ComparisonExecutionMode.COMPARE_BOTH
    assert reconstructed.workload.workload_type == ComparisonWorkloadType.DATA_PARALLEL
    assert reconstructed.workload.dataset_size == 10000
    assert reconstructed.real_config.worker_count == 4
    assert reconstructed.virtual_config.virtual_core_count == 8
    assert reconstructed.virtual_config.p_core_speed == 1.5


def test_comparison_results_round_trip():
    """Verify serialization and deserialization of RealExecutionResult and VirtualExecutionResult."""
    real_res = RealExecutionResult(
        status="completed",
        wall_clock_time_s=1.2345,
        worker_count=4,
        worker_intervals=[(0.1, 1.2)],
        aggregate_worker_compute_time_s=1.1,
        compute_interval_union_s=1.1,
        no_worker_compute_time_s=0.1345,
        worker_utilization_pct=89.1,
        peak_memory_rss_mb=42.5,
        task_completions=[{"task_id": "chunk_0", "process_id": 1001, "duration_s": 0.5}],
    )

    virt_res = VirtualExecutionResult(
        status="completed",
        virtual_makespan_ticks=120,
        simulated_clock_ticks=120,
        virtual_core_utilization_pct=75.0,
        virtual_core_count=8,
        virtual_core_allocation={0: ["chunk_0"]},
        task_completion_order=[{"task_id": "chunk_0", "assigned_core_id": 0, "finish_tick": 50, "waiting_ticks": 0}],
        scheduling_events=[{"tick": 0, "event": "DISPATCH", "task_id": "chunk_0", "core_id": 0}],
        avg_waiting_ticks=5.2,
        avg_turnaround_ticks=65.2,
    )

    analysis = ComparisonAnalysis(
        workload_equivalence=True,
        workload_equivalence_details="Datasets and algorithms are equivalent.",
        task_count_match=True,
        completion_order_concordance=1.0,
        real_worker_count=4,
        virtual_core_count=8,
        resource_allocation_ratio=0.5,
        real_utilization_pct=89.1,
        virtual_utilization_pct=75.0,
        utilization_difference_pct=14.1,
    )

    config = ComparisonConfiguration(
        comparison_id="session-res-999",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=ComparisonWorkloadConfig(
            workload_type=ComparisonWorkloadType.DATA_PARALLEL,
            workload_id="sum_of_squares",
            workload_name="Sum of Squares",
            dataset_size=5000,
        ),
        real_config=RealSystemConfig(worker_count=4),
        virtual_config=VirtualLabConfig(virtual_core_count=8),
    )

    session = ComparisonSessionResult(
        comparison_id="session-res-999",
        timestamp="2026-11-07T12:00:00Z",
        configuration=config,
        real_result=real_res,
        virtual_result=virt_res,
        analysis=analysis,
        success=True,
    )

    d = session.to_dict()
    assert d["comparison_id"] == "session-res-999"
    assert d["real_result"]["wall_clock_time_s"] == 1.2345
    assert d["virtual_result"]["virtual_makespan_ticks"] == 120
    assert d["analysis"]["completion_order_concordance"] == 1.0

    restored = ComparisonSessionResult.from_dict(d)
    assert restored.comparison_id == session.comparison_id
    assert restored.real_result is not None
    assert restored.real_result.wall_clock_time_s == 1.2345
    assert restored.virtual_result is not None
    assert restored.virtual_result.virtual_makespan_ticks == 120
    assert restored.analysis is not None
    assert restored.analysis.workload_equivalence is True


def test_cross_domain_ratio_forbidden():
    """Verify that assert_no_cross_domain_ratio strictly forbids dividing real seconds by virtual ticks."""
    real_time_s = 2.5
    virtual_ticks = 250

    with pytest.raises(ValueError, match="Invalid Cross-Domain Operation"):
        assert_no_cross_domain_ratio(real_time_s, virtual_ticks)

    with pytest.raises(ValueError, match="Invalid Cross-Domain Operation"):
        assert_no_cross_domain_ratio(2.5, 100)


def test_independent_clock_domain_validation():
    """Verify that RealExecutionResult rejects virtual ticks and VirtualExecutionResult rejects real PIDs."""
    real_res = RealExecutionResult(
        status="completed",
        wall_clock_time_s=1.5,
        worker_count=2,
        worker_intervals=[(0.0, 1.4)],
        aggregate_worker_compute_time_s=1.4,
        compute_interval_union_s=1.4,
        no_worker_compute_time_s=0.1,
        worker_utilization_pct=93.3,
        peak_memory_rss_mb=50.0,
    )
    # Ensure real result contains seconds, not simulated ticks
    assert real_res.wall_clock_time_s > 0
    assert not hasattr(real_res, "virtual_makespan_ticks")

    virt_res = VirtualExecutionResult(
        status="completed",
        virtual_makespan_ticks=300,
        simulated_clock_ticks=300,
        virtual_core_utilization_pct=85.0,
        virtual_core_count=4,
    )
    # Ensure virtual result contains ticks, not host seconds or PIDs
    assert virt_res.virtual_makespan_ticks == 300
    assert not hasattr(virt_res, "worker_pids")
