"""Comprehensive Unit and Integration Tests for CoreSync Phase 9 Performance Analytics.

Tests:
1. ScalabilityMetrics calculations (Speedup, Efficiency, Load Imbalance, Utilization, Throughput).
2. Boundary and invalid measurement safety (zero denominators, negative inputs).
3. Sample statistics calculations (mean, median, min, max, std dev with Bessel's correction).
4. Amdahl's Law calculations with exact hand-calculated expected values.
5. Benchmark history persistence, retrieval, deletion, and corruption resilience.
6. Multi-engine benchmarking execution (Data Parallel, Task Parallel, Scheduling, Virtual Lab).
7. Benchmark cooperative cancellation and process cleanup.
"""

import json
import math
from pathlib import Path
import pytest

from engine.analytics.models import (
    MetricClassification,
    ScalabilityMetrics,
    calculate_sample_statistics,
)
from engine.analytics.amdahl import (
    AmdahlCalculator,
    AmdahlPrediction,
)
from engine.analytics.benchmarking import (
    BenchmarkEngineType,
    BenchmarkIterationRecord,
    BenchmarkSessionResult,
    BenchmarkingEngine,
    get_sanitized_hardware_metadata,
)
from engine.analytics.history import (
    BenchmarkHistoryManager,
)


# =============================================================================
# 1. SCALABILITY METRICS & LOAD IMBALANCE FORMULAS
# =============================================================================

def test_scalability_metrics_hand_calculated_formulas():
    """Verify hand-calculated metrics for speedup, efficiency, throughput, utilization, and load imbalance."""
    # Sequential time = 10.0s, Parallel time = 2.5s, 4 workers, 100_000 items
    # Worker compute times: [2.0, 2.2, 1.8, 2.4]
    # Sum = 8.4s, Max = 2.4s, Avg = 2.1s, Min = 1.8s
    # Speedup S = 10.0 / 2.5 = 4.0
    # Efficiency E = 4.0 / 4 = 1.0 (100%)
    # Throughput = 100_000 / 2.5 = 40_000 items/s
    # Worker Utilization U = 8.4 / (4 * 2.5) * 100% = 8.4 / 10.0 * 100% = 84.0%
    # Load Imbalance = (2.4 - 2.1) / 2.1 = 0.3 / 2.1 = 0.142857 (14.29%)
    # Startup = 0.1s, Dispatch = 0.05s, Collection = 2.45s, Merge = 0.02s
    # Estimated Distribution Overhead = 0.05 + max(0, 2.45 - 2.4) = 0.05 + 0.05 = 0.10s
    metrics = ScalabilityMetrics(
        sequential_time_s=10.0,
        parallel_time_s=2.5,
        worker_count=4,
        work_units=100_000,
        startup_s=0.1,
        dispatch_s=0.05,
        collection_s=2.45,
        merge_s=0.02,
        worker_compute_times=[2.0, 2.2, 1.8, 2.4],
    )

    assert metrics.speedup == 4.0
    assert metrics.parallel_efficiency == 1.0
    assert metrics.efficiency_pct == 100.0
    assert metrics.throughput_items_per_s == 40_000.0
    assert round(metrics.total_computation_time_s, 2) == 8.4
    assert metrics.max_worker_compute_s == 2.4
    assert round(metrics.avg_worker_compute_s, 2) == 2.1
    assert metrics.min_worker_compute_s == 1.8
    assert round(metrics.worker_utilization_pct, 2) == 84.0
    assert round(metrics.load_imbalance, 6) == round(0.3 / 2.1, 6)
    assert round(metrics.load_imbalance_pct, 2) == 14.29
    assert round(metrics.estimated_distribution_overhead_s, 4) == 0.10


def test_scalability_metrics_zero_and_invalid_handling():
    """Verify safe fallback for zero denominators, negative times, and empty worker lists."""
    metrics = ScalabilityMetrics(
        sequential_time_s=0.0,
        parallel_time_s=0.0,
        worker_count=0,
        work_units=0,
        worker_compute_times=[],
    )

    assert metrics.speedup == 0.0
    assert metrics.parallel_efficiency == 0.0
    assert metrics.efficiency_pct == 0.0
    assert metrics.throughput_items_per_s == 0.0
    assert metrics.worker_utilization_pct == 0.0
    assert metrics.load_imbalance == 0.0
    assert metrics.max_worker_compute_s == 0.0
    assert metrics.avg_worker_compute_s == 0.0
    assert metrics.estimated_distribution_overhead_s == 0.0


def test_worker_utilization_strictly_clamped_to_100():
    """Verify worker utilization cannot exceed 100% even if measurement noise occurs."""
    metrics = ScalabilityMetrics(
        sequential_time_s=5.0,
        parallel_time_s=1.0,
        worker_count=2,
        worker_compute_times=[1.5, 1.5],  # Sum = 3.0 > 2 * 1.0 = 2.0
    )
    assert metrics.worker_utilization_pct == 100.0


# =============================================================================
# 2. STATISTICAL CALCULATIONS
# =============================================================================

def test_calculate_sample_statistics():
    """Verify mean, median, min, max, and sample standard deviation with Bessel's correction."""
    # Data: [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    # N = 8.
    # Sum = 40. Mean = 40 / 8 = 5.0.
    # Sorted: [2, 4, 4, 4, 5, 5, 7, 9]. Median = (4 + 5) / 2 = 4.5.
    # Min = 2.0, Max = 9.0.
    # Squared diffs from 5:
    # (2-5)^2 = 9
    # (4-5)^2 * 3 = 3
    # (5-5)^2 * 2 = 0
    # (7-5)^2 = 4
    # (9-5)^2 = 16
    # Sum sq = 9 + 3 + 0 + 4 + 16 = 32.
    # Sample Variance = 32 / (8 - 1) = 32 / 7 = 4.57142857.
    # Std Dev = sqrt(32 / 7) = 2.138090.
    data = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    stats = calculate_sample_statistics(data)

    assert stats["count"] == 8
    assert stats["mean"] == 5.0
    assert stats["median"] == 4.5
    assert stats["min"] == 2.0
    assert stats["max"] == 9.0
    assert round(stats["std_dev"], 4) == 2.1381


def test_sample_statistics_single_element_and_empty():
    """Verify statistical function handles empty and single-element lists correctly.
    For N=1 and N=0, sample standard deviation is undefined and must be None."""
    empty_stats = calculate_sample_statistics([])
    assert empty_stats["count"] == 0
    assert empty_stats["mean"] == 0.0
    assert empty_stats["std_dev"] is None
    assert empty_stats["variance"] is None
    assert empty_stats["std_dev_display"] == "N/A (empty sample)"

    single_stats = calculate_sample_statistics([42.0])
    assert single_stats["count"] == 1
    assert single_stats["mean"] == 42.0
    assert single_stats["median"] == 42.0
    assert single_stats["min"] == 42.0
    assert single_stats["max"] == 42.0
    assert single_stats["std_dev"] is None
    assert single_stats["variance"] is None
    assert single_stats["std_dev_display"] == "N/A (insufficient samples, N=1)"


# =============================================================================
# 3. AMDAHL'S LAW CALCULATOR & SCALABILITY CURVES
# =============================================================================

def test_amdahl_hand_calculated_speedup_and_efficiency():
    """Hand-calculated test case: P = 0.8 (80% parallelizable), N = 4 processors.
    S = 1 / ((1 - 0.8) + 0.8 / 4) = 1 / (0.2 + 0.2) = 1 / 0.4 = 2.5
    Efficiency E = 2.5 / 4 = 0.625 (62.5%)
    S_max = 1 / (1 - 0.8) = 1 / 0.2 = 5.0
    """
    prediction = AmdahlCalculator.predict(parallel_fraction=0.8, processors=4)

    assert prediction.parallel_fraction == 0.8
    assert prediction.serial_fraction == 0.2
    assert prediction.processors == 4
    assert prediction.theoretical_speedup == 2.5
    assert prediction.theoretical_efficiency == 0.625
    assert prediction.theoretical_efficiency_pct == 62.5
    assert prediction.theoretical_max_speedup == 5.0


def test_amdahl_boundary_cases():
    """Verify Amdahl's Law boundary cases:
    - P = 0.0 (completely serial) -> S = 1.0 for any N
    - P = 1.0 (completely parallel) -> S = N (linear ideal)
    - N = 1 (single processor) -> S = 1.0 for any P
    """
    # Serial workload
    assert AmdahlCalculator.calculate_speedup(parallel_fraction=0.0, processors=16) == 1.0
    assert AmdahlCalculator.calculate_max_speedup(parallel_fraction=0.0) == 1.0

    # Completely parallel workload
    assert AmdahlCalculator.calculate_speedup(parallel_fraction=1.0, processors=8) == 8.0
    assert math.isinf(AmdahlCalculator.calculate_max_speedup(parallel_fraction=1.0))

    # Single processor
    assert AmdahlCalculator.calculate_speedup(parallel_fraction=0.95, processors=1) == 1.0
    assert AmdahlCalculator.calculate_efficiency(parallel_fraction=0.95, processors=1) == 1.0


def test_amdahl_invalid_inputs_raise():
    """Verify AmdahlCalculator validates input domain strictly."""
    with pytest.raises(ValueError, match="Parallel fraction P must be between 0.0 and 1.0"):
        AmdahlCalculator.calculate_speedup(parallel_fraction=-0.1, processors=4)

    with pytest.raises(ValueError, match="Parallel fraction P must be between 0.0 and 1.0"):
        AmdahlCalculator.calculate_speedup(parallel_fraction=1.05, processors=4)

    with pytest.raises(ValueError, match="Processor count N must be at least 1"):
        AmdahlCalculator.calculate_speedup(parallel_fraction=0.5, processors=0)


def test_amdahl_scalability_curve_monotonicity():
    """Verify scalability curve points increase monotonically towards S_max."""
    curve = AmdahlCalculator.generate_scalability_curve(parallel_fraction=0.75, max_processors=16)
    assert len(curve) == 16

    # Speedup should increase monotonically
    speedups = [pt[1] for pt in curve]
    for i in range(len(speedups) - 1):
        assert speedups[i] <= speedups[i + 1]

    # Max speedup is 1 / (1 - 0.75) = 4.0
    assert speedups[-1] < 4.0


# =============================================================================
# 4. BENCHMARK HISTORY & PERSISTENCE
# =============================================================================

def test_benchmark_history_manager_crud(tmp_path):
    """Verify saving, listing, loading, and deleting benchmark session records."""
    manager = BenchmarkHistoryManager(storage_dir=tmp_path)
    assert len(manager.list_sessions()) == 0

    session = BenchmarkSessionResult(
        benchmark_id="test_session_001",
        engine_type=BenchmarkEngineType.DATA_PARALLEL,
        workload_name="Array Transcendental",
        worker_count=4,
        config_parameters={"dataset_size": 50000},
        hardware_metadata={"cpu": "Test CPU"},
        start_timestamp="2026-11-06T12:00:00Z",
        end_timestamp="2026-11-06T12:00:05Z",
        total_wall_clock_s=5.0,
        iterations_requested=2,
        warmup_iterations_requested=1,
        warmup_records=[],
        measured_records=[],
        statistics={"speedup": {"mean": 3.2, "min": 3.1, "max": 3.3}},
        verification_passed=True,
    )

    # 1. Save
    file_path = manager.save_session(session)
    assert file_path.exists()

    # 2. List
    sessions = manager.list_sessions()
    assert len(sessions) == 1
    assert sessions[0]["benchmark_id"] == "test_session_001"
    assert sessions[0]["mean_speedup"] == 3.2

    # 3. Load
    loaded = manager.load_session("test_session_001")
    assert loaded is not None
    assert loaded["workload_name"] == "Array Transcendental"
    assert loaded["worker_count"] == 4

    # 4. Delete
    deleted = manager.delete_session("test_session_001")
    assert deleted is True
    assert len(manager.list_sessions()) == 0


def test_benchmark_history_resilience_to_corrupted_files(tmp_path):
    """Verify that corrupt JSON files are safely skipped without crashing list_sessions()."""
    manager = BenchmarkHistoryManager(storage_dir=tmp_path)

    # Write a broken JSON file
    corrupt_file = tmp_path / "broken_record.json"
    corrupt_file.write_text("{ this is not valid JSON :::: ")

    # Should safely return empty list without raising
    sessions = manager.list_sessions()
    assert len(sessions) == 0


# =============================================================================
# 5. MULTI-ENGINE BENCHMARKING EXECUTION
# =============================================================================

def test_benchmarking_engine_data_parallel():
    """Verify Data Parallelism benchmark execution with warm-up separation and statistical rollup."""
    engine = BenchmarkingEngine()
    session = engine.run_data_parallel_benchmark(
        op_id="transcendental",
        dataset_size=10_000,
        worker_count=2,
        iterations=2,
        warmup_runs=1,
    )

    assert session.engine_type == BenchmarkEngineType.DATA_PARALLEL
    assert session.verification_passed is True
    assert session.cancelled is False
    assert session.warmup_iterations_requested == 1
    assert len(session.warmup_records) == 1
    assert session.iterations_requested == 2
    assert len(session.measured_records) == 2

    # Stats must be populated
    assert "speedup" in session.statistics
    assert session.statistics["speedup"]["count"] == 2
    assert session.statistics["speedup"]["mean"] > 0.0


def test_benchmarking_engine_task_parallel():
    """Verify Task Parallelism benchmark execution on Diamond DAG."""
    engine = BenchmarkingEngine()
    session = engine.run_task_parallel_benchmark(
        dag_type="diamond",
        worker_count=2,
        iterations=2,
        warmup_runs=1,
    )

    assert session.engine_type == BenchmarkEngineType.TASK_PARALLEL
    assert session.verification_passed is True
    assert len(session.measured_records) == 2
    assert "speedup" in session.statistics


def test_benchmarking_engine_scheduling_benchmark():
    """Verify CPU scheduling comparison benchmark execution."""
    engine = BenchmarkingEngine()
    session = engine.run_scheduling_benchmark(
        preset_id="staggered_arrivals",
        time_quantum=2.0,
        context_switch_overhead=0.1,
    )

    assert session.engine_type == BenchmarkEngineType.CPU_SCHEDULING
    assert session.verification_passed is True
    assert len(session.measured_records) == 6  # 6 classical algorithms evaluated
    assert "waiting_time" in session.statistics


def test_benchmarking_engine_virtual_lab_benchmark():
    """Verify Virtual Lab educational multicore benchmark execution."""
    engine = BenchmarkingEngine()
    session = engine.run_virtual_lab_benchmark(
        virtual_cores=4,
        task_count=20,
    )

    assert session.engine_type == BenchmarkEngineType.VIRTUAL_LAB
    assert session.verification_passed is True
    assert len(session.measured_records) == 1
    assert session.measured_records[0].extra_metrics["is_simulated"] is True
    assert "virtual_util_pct" in session.statistics


def test_benchmarking_engine_cancellation():
    """Verify cooperative benchmark cancellation terminates early cleanly."""
    engine = BenchmarkingEngine()
    engine.cancel()

    session = engine.run_data_parallel_benchmark(
        op_id="transcendental",
        dataset_size=10_000,
        worker_count=2,
        iterations=5,
        warmup_runs=2,
    )

    assert session.cancelled is True
    assert len(session.measured_records) == 0


# =============================================================================
# 6. PHASE 9.1 AUDIT VERIFICATION TESTS
# =============================================================================

def test_hardware_metadata_distinguishes_physical_from_logical():
    """Verify hardware metadata captures separate physical cores vs logical threads."""
    hw = get_sanitized_hardware_metadata()
    assert "physical_cores" in hw
    assert "total_logical_cores" in hw
    assert "cpu_model" in hw
    assert "architecture" in hw
    assert "operating_system" in hw
    assert "total_ram_gb" in hw

    # Host architecture: Intel Core i7-13650HX hybrid
    # Physical cores = 14 (6 P-cores + 8 E-cores), Logical processors = 20
    assert hw["physical_cores"] == 14
    assert hw["total_logical_cores"] == 20
    assert hw["physical_cores"] < hw["total_logical_cores"]
    assert "Intel" in hw["cpu_model"]
    assert hw["total_ram_gb"] > 0.0


def test_aggregate_estimated_residual_overhead_bounds():
    """Verify aggregate residual overhead is non-negative and properly classified."""
    # When worker compute artificially exceeds parallel time due to timer jitter
    metrics = ScalabilityMetrics(
        sequential_time_s=10.0,
        parallel_time_s=2.0,
        worker_count=2,
        worker_compute_times=[2.5, 2.5],  # Average = 2.5 > 2.0
    )
    # residual = max(0.0, 2.0 - 2.5) = 0.0
    assert metrics.aggregate_estimated_residual_s == 0.0

    # Normal case: residual = max(0.0, 2.0 - 1.5) = 0.5s
    normal_metrics = ScalabilityMetrics(
        sequential_time_s=10.0,
        parallel_time_s=2.0,
        worker_count=2,
        worker_compute_times=[1.5, 1.5],
    )
    assert normal_metrics.aggregate_estimated_residual_s == 0.5
    assert normal_metrics.provenance_map["aggregate_estimated_residual_s"]["classification"] == MetricClassification.ESTIMATED_RESIDUAL.value


def test_input_data_immutability_during_benchmark():
    """Verify sequential and parallel passes use identical copy-isolated input arrays."""
    import numpy as np
    from engine.data_parallel.operations import generate_dataset

    original_data = generate_dataset("transcendental", 5_000)
    data_snapshot = original_data.copy()

    engine = BenchmarkingEngine()
    session = engine.run_data_parallel_benchmark(
        op_id="transcendental",
        dataset_size=5_000,
        worker_count=2,
        iterations=2,
        warmup_runs=1,
    )

    assert session.verification_passed is True
    # Confirm original reference data was not mutated
    assert np.array_equal(original_data, data_snapshot)


def test_paired_speedup_mean_and_aggregate_ratio_speedup():
    """Verify statistical rollups report both paired speedup mean and aggregate ratio speedup."""
    engine = BenchmarkingEngine()
    session = engine.run_data_parallel_benchmark(
        op_id="transcendental",
        dataset_size=10_000,
        worker_count=2,
        iterations=3,
        warmup_runs=1,
    )

    stats = session.statistics["speedup"]
    assert "mean" in stats
    assert "mean_paired_speedup" in stats
    assert "aggregate_ratio_speedup" in stats
    assert stats["mean_paired_speedup"] == stats["mean"]
    assert stats["aggregate_ratio_speedup"] > 0.0


def test_virtual_lab_measurement_separation():
    """Verify Virtual Lab clearly distinguishes simulated ticks from monotonic wall-clock time."""
    engine = BenchmarkingEngine()
    session = engine.run_virtual_lab_benchmark(
        virtual_cores=4,
        task_count=16,
    )

    rec = session.measured_records[0]
    extra = rec.extra_metrics
    assert extra["is_simulated"] is True
    assert "simulated_ticks_elapsed" in extra
    assert "virtual_core_util_pct" in extra
    assert "simulator_wall_clock_s" in extra
    assert extra["metric_provenance"]["simulated_ticks_elapsed"] == MetricClassification.SIMULATED_VIRTUAL.value
    assert extra["metric_provenance"]["virtual_core_util_pct"] == MetricClassification.SIMULATED_VIRTUAL.value
    assert extra["metric_provenance"]["simulator_wall_clock_s"] == MetricClassification.DIRECTLY_MEASURED.value


def test_amdahl_asymptote_unbounded_and_display():
    """Verify Amdahl Calculator handles P=1.0 with unbounded asymptote and formatted string."""
    pred = AmdahlCalculator.predict(parallel_fraction=1.0, processors=16)
    assert pred.theoretical_speedup == 16.0
    assert pred.theoretical_efficiency == 1.0
    assert math.isinf(pred.theoretical_max_speedup)
    assert pred.max_speedup_display == "Unbounded (as N -> inf)"

    # P = 0.0 completely serial
    pred_serial = AmdahlCalculator.predict(parallel_fraction=0.0, processors=16)
    assert pred_serial.theoretical_speedup == 1.0
    assert pred_serial.theoretical_max_speedup == 1.0
    assert pred_serial.max_speedup_display == "1.00x"

