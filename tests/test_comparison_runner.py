"""Tests for CoreSync Phase 10 Comparison Runner, Execution Modes, and History Persistence."""

import pytest
from engine.comparison.models import (
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealSystemConfig,
    VirtualLabConfig,
)
from engine.comparison.comparison_runner import ComparisonRunner
from engine.analytics.history import list_comparisons, load_comparison
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm


def test_comparison_runner_virtual_only():
    """Verify executing in VIRTUAL_ONLY mode produces virtual results without running real processes."""
    workload = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="sum_of_squares",
        workload_name="Sum of Squares",
        dataset_size=2000,
    )
    virt_cfg = VirtualLabConfig(
        virtual_core_count=4,
        scheduling_algorithm=SchedulingAlgorithm.FCFS,
    )
    config = ComparisonConfiguration(
        comparison_id="run-virt-only-001",
        execution_mode=ComparisonExecutionMode.VIRTUAL_ONLY,
        workload=workload,
        real_config=RealSystemConfig(worker_count=2),
        virtual_config=virt_cfg,
    )

    runner = ComparisonRunner()
    progress_calls = []

    def progress_cb(completed, total, msg):
        progress_calls.append((completed, total, msg))

    session_res = runner.run_comparison(config, progress_callback=progress_cb, save_history=False)

    assert session_res.success is True
    assert session_res.configuration.execution_mode == ComparisonExecutionMode.VIRTUAL_ONLY
    assert session_res.real_result is None
    assert session_res.virtual_result is not None
    assert session_res.virtual_result.virtual_makespan_ticks > 0
    assert session_res.virtual_result.virtual_core_utilization_pct > 0
    assert len(progress_calls) > 0


def test_comparison_runner_real_only():
    """Verify executing in REAL_ONLY mode produces real results without virtual simulation."""
    workload = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="sum_of_squares",
        workload_name="Sum of Squares",
        dataset_size=1000,
    )
    real_cfg = RealSystemConfig(worker_count=2, timeout_s=15.0)
    config = ComparisonConfiguration(
        comparison_id="run-real-only-001",
        execution_mode=ComparisonExecutionMode.REAL_ONLY,
        workload=workload,
        real_config=real_cfg,
        virtual_config=VirtualLabConfig(virtual_core_count=2),
    )

    runner = ComparisonRunner()
    session_res = runner.run_comparison(config, save_history=False)

    assert session_res.success is True
    assert session_res.configuration.execution_mode == ComparisonExecutionMode.REAL_ONLY
    assert session_res.virtual_result is None
    assert session_res.real_result is not None
    assert session_res.real_result.wall_clock_time_s > 0
    assert len(session_res.real_result.worker_intervals) > 0


def test_comparison_runner_compare_both_and_history():
    """Verify COMPARE_BOTH runs real first, then virtual, analyzes results, and persists to history."""
    workload = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.TASK_PARALLEL,
        workload_id="diamond",
        workload_name="Diamond DAG",
    )
    real_cfg = RealSystemConfig(worker_count=2, timeout_s=15.0)
    virt_cfg = VirtualLabConfig(
        virtual_core_count=2,
        scheduling_algorithm=SchedulingAlgorithm.ROUND_ROBIN,
        time_quantum=3,
    )
    config = ComparisonConfiguration(
        comparison_id="history-test-session-001",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=workload,
        real_config=real_cfg,
        virtual_config=virt_cfg,
    )

    runner = ComparisonRunner()
    session_res = runner.run_comparison(config, save_history=True)

    assert session_res.success is True
    assert session_res.configuration.execution_mode == ComparisonExecutionMode.COMPARE_BOTH
    assert session_res.real_result is not None
    assert session_res.virtual_result is not None
    assert session_res.analysis is not None
    assert session_res.analysis.workload_equivalence is True
    assert session_res.analysis.real_worker_count == 2
    assert session_res.analysis.virtual_core_count == 2

    # Verify history retrieval
    comparisons = list_comparisons()
    assert any(c["comparison_id"] == "history-test-session-001" for c in comparisons)

    loaded = load_comparison("history-test-session-001")
    assert loaded is not None
    assert loaded["comparison_id"] == "history-test-session-001"
    assert loaded["real_result"]["wall_clock_time_s"] > 0
    assert loaded["virtual_result"]["virtual_makespan_ticks"] > 0


def test_comparison_runner_cancellation():
    """Verify that canceling the runner cooperatively halts execution."""
    workload = ComparisonWorkloadConfig(
        workload_type=ComparisonWorkloadType.DATA_PARALLEL,
        workload_id="transcendental",
        workload_name="Transcendental",
        dataset_size=50000,
    )
    config = ComparisonConfiguration(
        comparison_id="cancel-test-001",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=workload,
        real_config=RealSystemConfig(worker_count=2),
        virtual_config=VirtualLabConfig(virtual_core_count=2),
    )

    runner = ComparisonRunner()
    runner.cancel()  # Signal cancellation before execution

    session_res = runner.run_comparison(config, save_history=False)
    assert session_res.cancelled is True or session_res.success is False
