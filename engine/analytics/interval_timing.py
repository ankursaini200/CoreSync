"""Interval Timing and Non-Compute Idle Gap Analysis for CoreSync Workstations.

Distinguishes between:
1. aggregate_worker_compute_time_s: Sum of individual worker compute durations (worker-seconds, W*s).
2. parallel_makespan_s: Elapsed wall-clock execution time (W_end - W_start).
3. compute_interval_union_s: Elapsed wall-clock time during which at least one worker was computing.
4. idle_gap_time_s: Elapsed wall-clock time within the parallel execution window when zero workers were computing.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ExecutionIntervalMetrics:
    """Metrics parcel characterizing worker computation intervals and idle gaps."""

    parallel_makespan_s: float
    aggregate_worker_compute_time_s: float
    compute_interval_union_s: float
    idle_gap_time_s: float
    merged_compute_intervals: List[Tuple[float, float]] = field(default_factory=list)
    idle_gap_intervals: List[Tuple[float, float]] = field(default_factory=list)

    @property
    def concurrency_density(self) -> float:
        """Ratio of aggregate worker compute to compute interval union.

        Indicates average number of active workers during compute intervals.
        """
        if self.compute_interval_union_s <= 0.0:
            return 0.0
        return self.aggregate_worker_compute_time_s / self.compute_interval_union_s

    def to_dict(self) -> Dict[str, Any]:
        """Serialize interval metrics to dictionary."""
        return {
            "parallel_makespan_s": round(self.parallel_makespan_s, 6),
            "aggregate_worker_compute_time_s": round(self.aggregate_worker_compute_time_s, 6),
            "compute_interval_union_s": round(self.compute_interval_union_s, 6),
            "idle_gap_time_s": round(self.idle_gap_time_s, 6),
            "concurrency_density": round(self.concurrency_density, 3),
            "merged_interval_count": len(self.merged_compute_intervals),
            "idle_gap_count": len(self.idle_gap_intervals),
        }


def compute_interval_metrics(
    window_start: float,
    window_end: float,
    worker_intervals: List[Tuple[float, float]],
    raw_compute_durations: Optional[List[float]] = None,
) -> ExecutionIntervalMetrics:
    """Compute exact computation interval unions and elapsed idle gaps.

    Mathematical Invariants:
        1. All worker intervals are strictly clipped to the defined parallel window [window_start, window_end].
        2. Intervals with start >= end or invalid coordinates are discarded.
        3. compute_interval_union_s is the measure of the union of all clipped intervals:
           union = | \\bigcup [s_i, e_i] |
        4. Because union is a subset of [window_start, window_end], compute_interval_union_s <= parallel_makespan_s.
        5. idle_gap_time_s = parallel_makespan_s - compute_interval_union_s, guaranteed >= 0.0.
        6. aggregate_worker_compute_time_s is the sum of compute durations in worker-seconds,
           which may exceed parallel_makespan_s when multiple workers compute concurrently.

    Args:
        window_start: Monotonic start timestamp of the parallel execution window.
        window_end: Monotonic end timestamp of the parallel execution window.
        worker_intervals: List of (start_timestamp, finish_timestamp) tuples from worker telemetry.
        raw_compute_durations: Optional explicit compute durations per worker (worker-seconds).

    Returns:
        ExecutionIntervalMetrics with exact interval union, idle gaps, and aggregate worker compute.
    """
    parallel_makespan_s = max(0.0, float(window_end) - float(window_start))

    if raw_compute_durations is not None:
        agg_compute_s = sum(max(0.0, float(d)) for d in raw_compute_durations)
    else:
        agg_compute_s = sum(
            max(0.0, float(e) - float(s))
            for s, e in worker_intervals
            if s is not None and e is not None and e > s
        )

    # 1. Sanitize and clip intervals to the window [window_start, window_end]
    clipped: List[Tuple[float, float]] = []
    for item in worker_intervals:
        if not isinstance(item, (tuple, list)) or len(item) < 2:
            continue
        s, e = item[0], item[1]
        if s is None or e is None:
            continue
        try:
            s_val = float(s)
            e_val = float(e)
        except (ValueError, TypeError):
            continue

        if s_val >= e_val:
            # Zero or negative interval duration is invalid
            continue

        c_s = max(window_start, s_val)
        c_e = min(window_end, e_val)
        if c_e > c_s:
            clipped.append((c_s, c_e))

    if not clipped:
        # No valid computation occurred within the window
        idle_gaps = [(window_start, window_end)] if parallel_makespan_s > 0.0 else []
        return ExecutionIntervalMetrics(
            parallel_makespan_s=parallel_makespan_s,
            aggregate_worker_compute_time_s=agg_compute_s,
            compute_interval_union_s=0.0,
            idle_gap_time_s=parallel_makespan_s,
            merged_compute_intervals=[],
            idle_gap_intervals=idle_gaps,
        )

    # 2. Sort intervals by start time, then end time
    clipped.sort(key=lambda x: (x[0], x[1]))

    # 3. Merge overlapping or contiguous intervals
    merged: List[Tuple[float, float]] = []
    curr_s, curr_e = clipped[0]
    for n_s, n_e in clipped[1:]:
        if n_s <= curr_e:
            curr_e = max(curr_e, n_e)
        else:
            merged.append((curr_s, curr_e))
            curr_s, curr_e = n_s, n_e
    merged.append((curr_s, curr_e))

    # 4. Calculate union of compute intervals
    union_s = sum(e - s for s, e in merged)

    # 5. Calculate non-compute idle gaps (pre-gap, inter-compute gaps, post-gap)
    idle_gaps: List[Tuple[float, float]] = []
    cursor = window_start
    for m_s, m_e in merged:
        if m_s > cursor:
            idle_gaps.append((cursor, m_s))
        cursor = max(cursor, m_e)
    if cursor < window_end:
        idle_gaps.append((cursor, window_end))

    idle_s = max(0.0, parallel_makespan_s - union_s)

    return ExecutionIntervalMetrics(
        parallel_makespan_s=parallel_makespan_s,
        aggregate_worker_compute_time_s=agg_compute_s,
        compute_interval_union_s=union_s,
        idle_gap_time_s=idle_s,
        merged_compute_intervals=merged,
        idle_gap_intervals=idle_gaps,
    )

