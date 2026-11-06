"""Unit tests for Interval Timing, Interval Union, and Non-Compute Window Analysis."""

import pytest
from engine.analytics.interval_timing import (
    ExecutionIntervalMetrics,
    compute_interval_metrics,
)


def _spawned_clock_worker(worker_id: int, duration_s: float, out_q) -> None:
    """Worker executed in an isolated spawned process to capture real monotonic clock timestamps."""
    import time
    t_start = time.perf_counter()
    end_target = t_start + duration_s
    acc = 0.0
    while time.perf_counter() < end_target:
        acc += 1.0001
    t_finish = time.perf_counter()
    out_q.put((worker_id, t_start, t_finish, acc))


def test_simultaneous_workers_worker_seconds_vs_interval_union():
    """Verify 4 workers computing simultaneously for 2.0s:
    - Aggregate worker compute: 8.0 worker-seconds (4 * 2.0s).
    - Interval union: 2.0s.
    - Parallel makespan: 3.0s.
    - No-worker-compute time: 1.0s (0.5s pre-gap + 0.5s post-gap).
    """
    window_start = 0.0
    window_end = 3.0
    # 4 workers all start at t=0.5s and finish at t=2.5s
    intervals = [(0.5, 2.5), (0.5, 2.5), (0.5, 2.5), (0.5, 2.5)]

    metrics = compute_interval_metrics(window_start, window_end, intervals)

    assert metrics.parallel_makespan_s == 3.0
    assert metrics.aggregate_worker_compute_time_s == 8.0
    assert metrics.compute_interval_union_s == 2.0
    assert metrics.no_worker_compute_time_s == 1.0
    assert metrics.idle_gap_time_s == 1.0  # backward compatibility alias
    assert metrics.concurrency_density == 4.0
    assert len(metrics.merged_compute_intervals) == 1
    assert metrics.merged_compute_intervals[0] == (0.5, 2.5)
    assert len(metrics.no_worker_compute_intervals) == 2
    assert metrics.no_worker_compute_intervals[0] == (0.0, 0.5)
    assert metrics.no_worker_compute_intervals[1] == (2.5, 3.0)


def test_partially_overlapping_worker_intervals():
    """Verify partially overlapping intervals are merged without double-counting."""
    window_start = 0.0
    window_end = 6.0
    # Worker 0: [1.0, 3.5] (2.5s)
    # Worker 1: [2.0, 4.5] (2.5s)
    # Overlap region: [2.0, 3.5]
    intervals = [(1.0, 3.5), (2.0, 4.5)]

    metrics = compute_interval_metrics(window_start, window_end, intervals)

    assert metrics.parallel_makespan_s == 6.0
    assert metrics.aggregate_worker_compute_time_s == 5.0
    assert metrics.compute_interval_union_s == 3.5  # [1.0, 4.5]
    assert metrics.no_worker_compute_time_s == 2.5  # [0.0, 1.0] (1.0s) + [4.5, 6.0] (1.5s)
    assert metrics.idle_gap_time_s == 2.5
    assert metrics.merged_compute_intervals == [(1.0, 4.5)]
    assert metrics.no_worker_compute_intervals == [(0.0, 1.0), (4.5, 6.0)]


def test_sequential_non_overlapping_intervals():
    """Verify multiple sequential disjoint worker computation intervals."""
    window_start = 0.0
    window_end = 8.0
    # Worker 0: [1.0, 2.5] (1.5s)
    # Worker 1: [4.0, 5.0] (1.0s)
    # Worker 2: [6.5, 7.5] (1.0s)
    intervals = [(1.0, 2.5), (4.0, 5.0), (6.5, 7.5)]

    metrics = compute_interval_metrics(window_start, window_end, intervals)

    assert metrics.parallel_makespan_s == 8.0
    assert metrics.aggregate_worker_compute_time_s == 3.5
    assert metrics.compute_interval_union_s == 3.5
    assert metrics.no_worker_compute_time_s == 4.5
    assert metrics.idle_gap_time_s == 4.5
    assert metrics.merged_compute_intervals == [(1.0, 2.5), (4.0, 5.0), (6.5, 7.5)]
    # No-worker-compute intervals: [0.0, 1.0], [2.5, 4.0], [5.0, 6.5], [7.5, 8.0]
    assert metrics.no_worker_compute_intervals == [(0.0, 1.0), (2.5, 4.0), (5.0, 6.5), (7.5, 8.0)]


def test_gaps_before_between_and_after_computation():
    """Verify explicit accounting of pre-compute, inter-compute, and post-compute windows."""
    window_start = 10.0
    window_end = 25.0  # 15.0s makespan
    # Pre-gap: 10.0 -> 12.0 (2.0s)
    # Work 1: 12.0 -> 15.0 (3.0s)
    # Mid-gap: 15.0 -> 18.0 (3.0s)
    # Work 2: 18.0 -> 21.0 (3.0s)
    # Post-gap: 21.0 -> 25.0 (4.0s)
    intervals = [(12.0, 15.0), (18.0, 21.0)]

    metrics = compute_interval_metrics(window_start, window_end, intervals)

    assert metrics.parallel_makespan_s == 15.0
    assert metrics.compute_interval_union_s == 6.0
    assert metrics.no_worker_compute_time_s == 9.0  # 2.0 + 3.0 + 4.0 = 9.0s
    assert metrics.idle_gap_time_s == 9.0
    assert metrics.no_worker_compute_intervals == [(10.0, 12.0), (15.0, 18.0), (21.0, 25.0)]


def test_invalid_and_out_of_window_intervals():
    """Verify handling of out-of-bounds, clipped, inverted, and malformed intervals."""
    window_start = 10.0
    window_end = 20.0  # 10.0s window
    intervals = [
        (2.0, 5.0),    # Fully before window -> discarded
        (22.0, 25.0),  # Fully after window -> discarded
        (8.0, 14.0),   # Crosses window start -> clipped to [10.0, 14.0] (4.0s)
        (17.0, 23.0),  # Crosses window end -> clipped to [17.0, 20.0] (3.0s)
        (16.0, 15.0),  # Inverted (start > end) -> discarded
        (15.0, 15.0),  # Zero length (start == end) -> discarded
        (None, 12.0),  # Malformed None -> discarded
    ]

    metrics = compute_interval_metrics(window_start, window_end, intervals)

    assert metrics.parallel_makespan_s == 10.0
    assert metrics.compute_interval_union_s == 7.0  # [10.0, 14.0] (4s) + [17.0, 20.0] (3s)
    assert metrics.no_worker_compute_time_s == 3.0  # [14.0, 17.0] (3s)
    assert metrics.idle_gap_time_s == 3.0
    assert metrics.merged_compute_intervals == [(10.0, 14.0), (17.0, 20.0)]
    assert metrics.no_worker_compute_intervals == [(14.0, 17.0)]


def test_empty_intervals_and_zero_duration_window():
    """Verify safety with empty intervals list and zero makespan window."""
    empty_res = compute_interval_metrics(5.0, 5.0, [])
    assert empty_res.parallel_makespan_s == 0.0
    assert empty_res.compute_interval_union_s == 0.0
    assert empty_res.no_worker_compute_time_s == 0.0
    assert empty_res.idle_gap_time_s == 0.0

    idle_window_res = compute_interval_metrics(0.0, 5.0, [])
    assert idle_window_res.parallel_makespan_s == 5.0
    assert idle_window_res.compute_interval_union_s == 0.0
    assert idle_window_res.no_worker_compute_time_s == 5.0
    assert idle_window_res.idle_gap_time_s == 5.0
    assert idle_window_res.no_worker_compute_intervals == [(0.0, 5.0)]


def test_spawn_worker_cross_process_monotonic_clock_sync():
    """Verify cross-process monotonic clock synchronization using real spawned workers on Linux.

    Requirements:
    1. Mandatory 'spawn' context.
    2. Coordinator records monotonic start timestamp.
    3. Multiple spawned workers independently capture monotonic start/finish timestamps.
    4. Workers return timestamps through multiprocessing Queue.
    5. Coordinator records monotonic finish timestamp and calculates interval metrics.
    6. Verifies s_i < e_i and w_start <= s_i <= e_i <= w_end.
    7. Operates without artificial timestamp offsets or manual synthetic intervals.
    """
    import multiprocessing
    import time

    ctx = multiprocessing.get_context("spawn")
    out_q = ctx.Queue()
    num_workers = 3
    work_duration = 0.03  # 30 ms compute per worker

    w_start = time.perf_counter()
    procs = [
        ctx.Process(target=_spawned_clock_worker, args=(i, work_duration, out_q))
        for i in range(num_workers)
    ]
    for p in procs:
        p.start()

    results = []
    for _ in range(num_workers):
        results.append(out_q.get(timeout=10.0))

    for p in procs:
        p.join(timeout=5.0)
    w_end = time.perf_counter()

    for p in procs:
        assert p.exitcode == 0

    worker_intervals = []
    for wid, s, e, acc in results:
        assert s < e, f"Worker {wid} start {s} >= finish {e}"
        assert w_start <= s, f"Worker {wid} start {s} was earlier than coordinator start {w_start}"
        assert e <= w_end, f"Worker {wid} finish {e} was later than coordinator finish {w_end}"
        worker_intervals.append((s, e))

    metrics = compute_interval_metrics(w_start, w_end, worker_intervals)

    assert metrics.parallel_makespan_s > 0.0
    assert metrics.parallel_makespan_s == pytest.approx(w_end - w_start, abs=1e-5)
    assert metrics.compute_interval_union_s > 0.0
    assert metrics.compute_interval_union_s <= metrics.parallel_makespan_s
    assert metrics.no_worker_compute_time_s >= 0.0
    assert metrics.no_worker_compute_time_s == pytest.approx(
        metrics.parallel_makespan_s - metrics.compute_interval_union_s, abs=1e-5
    )
    assert metrics.idle_gap_time_s == metrics.no_worker_compute_time_s
    assert len(metrics.merged_compute_intervals) >= 1
