"""Comprehensive Unit and Integration Tests for Phase 5 Data Parallelism Engine."""

import multiprocessing as mp
import time
import numpy as np
import pytest

from engine.data_parallel.partitioner import Chunk, DataPartitioner
from engine.data_parallel.operations import (
    execute_chunk,
    generate_dataset,
    get_supported_operations,
)
from engine.data_parallel.result_collector import ResultCollector
from engine.data_parallel.verification import ResultVerifier, VerificationResult
from engine.data_parallel.executor import (
    DataParallelBenchmarkResult,
    DataParallelExecutor,
    ParallelExecutionResult,
)
from gui.data_parallelism import DataParallelismPage


# --- 1. Partitioning Tests ---

def test_partitioning_even_division():
    """Verify that an evenly divisible dataset creates equal-sized chunks."""
    chunks = DataPartitioner.partition_indices(total_items=100, num_chunks=4)
    assert len(chunks) == 4
    for i, c in enumerate(chunks):
        assert c.chunk_id == i
        assert c.size == 25
    assert chunks[0].start_idx == 0
    assert chunks[-1].end_idx == 100
    assert DataPartitioner.verify_partitions(100, chunks) is True


def test_partitioning_uneven_division():
    """Verify remainder distribution for unevenly divisible datasets."""
    # 103 items divided across 4 chunks: remainder = 3
    # First 3 chunks have size 26 (base 25 + 1), last chunk has size 25
    chunks = DataPartitioner.partition_indices(total_items=103, num_chunks=4)
    assert len(chunks) == 4
    assert [c.size for c in chunks] == [26, 26, 26, 25]
    assert DataPartitioner.verify_partitions(103, chunks) is True


def test_partitioning_empty_dataset():
    """Verify that partitioning an empty dataset returns an empty list cleanly."""
    chunks = DataPartitioner.partition_indices(total_items=0, num_chunks=4)
    assert chunks == []
    assert DataPartitioner.verify_partitions(0, chunks) is True


def test_partitioning_items_less_than_chunks():
    """Verify when num_chunks exceeds items, chunk count is clamped without empty chunks."""
    chunks = DataPartitioner.partition_indices(total_items=3, num_chunks=10)
    assert len(chunks) == 3
    for c in chunks:
        assert c.size == 1
    assert DataPartitioner.verify_partitions(3, chunks) is True


def test_partition_array_slices():
    """Verify numpy zero-copy slicing produces contiguous arrays."""
    arr = np.arange(10, dtype=np.float64)
    pairs = DataPartitioner.partition_array(arr, num_chunks=3)
    assert len(pairs) == 3
    recombined = np.concatenate([slice_arr for _, slice_arr in pairs])
    np.testing.assert_array_equal(arr, recombined)


# --- 2. Operations & Kernels Tests ---

def test_all_supported_operations_exist():
    """Verify operations catalog contains all five required CPU kernels."""
    ops = get_supported_operations()
    assert "transcendental" in ops
    assert "polynomial" in ops
    assert "matrix_norms" in ops
    assert "prime_count" in ops
    assert "sum_of_squares" in ops


def test_transcendental_kernel():
    """Verify element-wise transcendental kernel computation."""
    data = np.array([0.0, 1.0, 10.0], dtype=np.float64)
    out = execute_chunk("transcendental", data, {"iterations": 1})
    assert isinstance(out, np.ndarray)
    assert out.shape == data.shape
    assert np.all(np.isfinite(out))


def test_prime_count_kernel():
    """Verify prime counting kernel produces known prime counts."""
    # Primes in [10, 30): 11, 13, 17, 19, 23, 29 = 6 primes
    count = execute_chunk("prime_count", (10, 30))
    assert count == 6


def test_matrix_norms_kernel():
    """Verify matrix row norms kernel calculates L2 row lengths."""
    mat = np.array([
        [3.0, 4.0],   # norm = 5.0
        [1.0, 0.0],   # norm = 1.0
    ], dtype=np.float64)
    # The kernel adds mean(sin(matrix)) cross term
    out = execute_chunk("matrix_norms", mat)
    assert len(out) == 2
    assert out[0] > 4.5
    assert out[1] > 0.5


# --- 3. Verification Engine Tests ---

def test_verifier_array_exact_and_tolerance():
    """Verify that verifier validates arrays within tolerance."""
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([1.0000001, 2.0, 3.0])  # tiny diff
    v = ResultVerifier.verify(a, b, is_reduction=False, atol=1e-5)
    assert v.passed is True
    assert v.mismatch_count == 0

    # Failure with significant diff
    c = np.array([1.0, 5.0, 3.0])
    v_fail = ResultVerifier.verify(a, c, is_reduction=False)
    assert v_fail.passed is False
    assert v_fail.mismatch_count == 1
    assert v_fail.max_difference == 3.0


def test_verifier_scalar_reduction():
    """Verify that verifier handles integer and floating point reductions."""
    # Integer exact match
    v_int = ResultVerifier.verify(42, 42, is_reduction=True)
    assert v_int.passed is True

    # Integer mismatch
    v_int_bad = ResultVerifier.verify(42, 43, is_reduction=True)
    assert v_int_bad.passed is False
    assert v_int_bad.mismatch_count == 1

    # Float reduction with tolerance
    v_flt = ResultVerifier.verify(100.000001, 100.0, is_reduction=True, atol=1e-4)
    assert v_flt.passed is True


# --- 4. Executor & Multiprocessing Parallelism Tests ---

def test_executor_automatic_worker_selection():
    """Verify heuristic worker selection scales sensibly with dataset size."""
    # Small dataset -> few workers
    w_small = DataParallelExecutor.determine_automatic_workers(5_000, "transcendental")
    assert 1 <= w_small <= 2

    # Medium dataset -> moderate workers
    w_med = DataParallelExecutor.determine_automatic_workers(100_000, "transcendental")
    assert 1 <= w_med <= 8

    # Large dataset -> utilizes available capacity
    w_large = DataParallelExecutor.determine_automatic_workers(2_000_000, "transcendental")
    assert w_large >= 2


def test_single_worker_parallel_execution():
    """Verify single-worker execution (1 chunk) returns correct verified result."""
    executor = DataParallelExecutor()
    data = generate_dataset("polynomial", size=1_000, seed=123)

    result = executor.run_parallel(
        op_id="polynomial",
        data=data,
        worker_count=1,
    )

    assert result.success is True
    assert len(result.chunks) == 1
    assert len(result.data) == 1_000

    seq_data, _ = executor.run_sequential("polynomial", data)
    ver = ResultVerifier.verify(seq_data, result.data, is_reduction=False)
    assert ver.passed is True


def test_multi_worker_parallel_execution():
    """Verify multi-worker parallel execution matches sequential output."""
    executor = DataParallelExecutor()
    data = generate_dataset("transcendental", size=5_000, seed=42)

    benchmark = executor.run_benchmark(
        op_id="transcendental",
        data=data,
        worker_count=4,
        warm_up=False,
    )

    assert benchmark.success is True
    assert benchmark.verification.passed is True
    assert benchmark.verification.mismatch_count == 0
    assert benchmark.worker_count == 4
    assert len(benchmark.chunks) == 4
    assert len(benchmark.worker_results) == 4
    assert benchmark.timings.startup_s > 0.0
    assert benchmark.timings.compute_s > 0.0
    assert benchmark.timings.merge_s >= 0.0


def test_prime_count_parallel_benchmark():
    """Verify reduction operation across multi-worker parallel execution."""
    executor = DataParallelExecutor()
    data = (100_000, 110_000)  # range of 10,000 integers

    benchmark = executor.run_benchmark(
        op_id="prime_count",
        data=data,
        worker_count=3,  # uneven worker count
    )

    assert benchmark.success is True
    assert benchmark.verification.passed is True
    assert benchmark.verification.mismatch_count == 0
    assert isinstance(benchmark.verification.total_items, int)


def test_cooperative_cancellation_and_zero_orphans():
    """Verify cancelling parallel execution terminates workers with zero orphans."""
    executor = DataParallelExecutor()
    # Large workload that would take a long time if uninterrupted
    data = (1_000_000, 1_500_000)
    cancel_event = mp.get_context("spawn").Event()

    # Pre-set cancel event to abort immediately during execution
    cancel_event.set()

    result = executor.run_parallel(
        op_id="prime_count",
        data=data,
        worker_count=2,
        cancel_event=cancel_event,
    )

    assert result.success is False
    assert "cancelled" in result.error_message.lower()
    # Ensure all workers were cleaned up
    assert len(executor._active_workers) == 0


def test_worker_isolation_from_qt():
    """Verify that worker modules do not import PySide6."""
    import sys
    import subprocess
    cmd = [
        sys.executable,
        "-c",
        "import engine.data_parallel.worker; import sys; assert 'PySide6' not in sys.modules, 'PySide6 imported!'",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Worker isolation assertion failed: {res.stderr}"


# --- 5. Timing Breakdown & IPC Measurement Tests ---

def test_timing_breakdown_metrics_present_and_positive():
    """Verify all granular timing breakdown metrics are measured and positive."""
    executor = DataParallelExecutor()
    data = generate_dataset("polynomial", size=10_000, seed=42)

    benchmark = executor.run_benchmark(
        op_id="polynomial",
        data=data,
        worker_count=2,
    )

    tb = benchmark.timings
    assert tb.startup_s > 0.0, "Process startup must be measured"
    assert tb.dispatch_s > 0.0, "Input preparation & dispatch must be measured"
    assert tb.collection_s > 0.0, "Parallel collection window must be measured"
    assert tb.merge_s >= 0.0, "Result merge time must be measured"
    assert tb.total_s > 0.0, "Total time must be positive"

    assert tb.max_worker_compute_s > 0.0, "Worker critical path computation must be measured"
    assert tb.avg_worker_compute_s > 0.0, "Average worker compute must be measured"
    assert tb.sum_worker_compute_s >= tb.max_worker_compute_s, "Sum of worker compute must exceed max"
    assert tb.avg_input_ipc_s >= 0.0, "Average input IPC latency must be recorded"
    assert tb.ipc_overhead_s >= tb.dispatch_s, "Total IPC overhead must include input dispatch"


def test_timing_intervals_non_overlapping_and_consistent():
    """Verify master phases are sequential and non-overlapping, summing to total_s."""
    executor = DataParallelExecutor()
    data = generate_dataset("transcendental", size=15_000, seed=123)

    benchmark = executor.run_benchmark(
        op_id="transcendental",
        data=data,
        worker_count=3,
    )

    tb = benchmark.timings
    phase_sum = tb.startup_s + tb.dispatch_s + tb.collection_s + tb.merge_s

    # Phase sum must match total_s within small measurement jitter (< 15ms)
    diff = abs(phase_sum - tb.total_s)
    assert diff < 0.025, f"Phase sum ({phase_sum:.4f}s) diverged from total_s ({tb.total_s:.4f}s) by {diff:.4f}s"

    # Collection window must be at least as long as the slowest worker's computation
    assert tb.collection_s >= (tb.max_worker_compute_s * 0.90)


def test_worker_result_ipc_and_timestamps():
    """Verify individual worker results report valid PIDs, IPC latencies, and execution timestamps."""
    executor = DataParallelExecutor()
    data = (50_000, 60_000)

    result = executor.run_parallel(
        op_id="prime_count",
        data=data,
        worker_count=2,
    )

    assert result.success is True
    assert len(result.worker_results) == 2
    for r in result.worker_results:
        assert r.worker_pid > 0
        assert r.compute_time_s > 0.0
        assert r.input_ipc_latency_s >= 0.0
        assert r.worker_start_time > 0.0
        assert r.worker_finish_time >= r.worker_start_time
        assert abs((r.worker_finish_time - r.worker_start_time) - r.compute_time_s) < 0.005


# --- 6. GUI Integration Tests ---

def test_data_parallelism_page_initialization(qapp):
    """Verify DataParallelismPage initializes with all widgets and default parameters."""
    page = DataParallelismPage()
    assert page.combo_ops.count() == 5
    assert page.spin_size.value() >= 10_000
    assert page.spin_workers.value() >= 1
    assert page.btn_run_benchmark.isEnabled() is True
    assert page.btn_cancel.isEnabled() is False
    page.shutdown()


def test_data_parallelism_page_worker_mode_switch(qapp):
    """Verify switching between Automatic and Manual worker selection."""
    page = DataParallelismPage()
    # Default is Automatic (index 0)
    assert page.spin_workers.isEnabled() is False

    # Switch to Manual (index 1)
    page.combo_mode.setCurrentIndex(1)
    assert page.spin_workers.isEnabled() is True

    # Switch back to Automatic
    page.combo_mode.setCurrentIndex(0)
    assert page.spin_workers.isEnabled() is False
    page.shutdown()

