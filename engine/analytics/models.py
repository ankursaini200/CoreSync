"""Core Performance Analytics Models and Metric Classification for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides mathematically rigorous, validated data models for execution performance,
Amdahl scalability analysis, and statistical evaluation.
"""

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Dict, List, Optional


class MetricClassification(str, Enum):
    """Categorization of metric provenance and mathematical foundation.

    Distinguishes empirical measurements from derived ratios, estimated residuals,
    and simulated virtual environments.
    """
    DIRECTLY_MEASURED = "directly_measured"
    MATHEMATICALLY_DERIVED = "mathematically_derived"
    ESTIMATED_RESIDUAL = "estimated_residual"
    SIMULATED_VIRTUAL = "simulated_virtual"

    @property
    def display_label(self) -> str:
        labels = {
            MetricClassification.DIRECTLY_MEASURED: "Directly Measured",
            MetricClassification.MATHEMATICALLY_DERIVED: "Mathematically Derived",
            MetricClassification.ESTIMATED_RESIDUAL: "Estimated Residual",
            MetricClassification.SIMULATED_VIRTUAL: "Simulated Virtual",
        }
        return labels.get(self, self.value)

    @property
    def badge_theme(self) -> str:
        themes = {
            MetricClassification.DIRECTLY_MEASURED: "success",
            MetricClassification.MATHEMATICALLY_DERIVED: "info",
            MetricClassification.ESTIMATED_RESIDUAL: "warning",
            MetricClassification.SIMULATED_VIRTUAL: "neutral",
        }
        return themes.get(self, "neutral")


def calculate_sample_statistics(values: List[float]) -> Dict[str, float]:
    """Compute standard descriptive statistics on a numerical sample.

    Args:
        values: List of empirical observations.

    Returns:
        Dictionary with count, mean, min, max, median, and std_dev.
    """
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "std_dev": 0.0,
        }

    n = len(values)
    v_sorted = sorted(values)
    mean_val = sum(values) / n
    min_val = v_sorted[0]
    max_val = v_sorted[-1]

    # Median calculation
    if n % 2 == 1:
        median_val = v_sorted[n // 2]
    else:
        median_val = (v_sorted[n // 2 - 1] + v_sorted[n // 2]) / 2.0

    # Sample standard deviation (Bessel's correction N-1 for N > 1)
    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        std_dev = math.sqrt(max(0.0, variance))
    else:
        std_dev = 0.0

    return {
        "count": n,
        "mean": round(mean_val, 6),
        "min": round(min_val, 6),
        "max": round(max_val, 6),
        "median": round(median_val, 6),
        "std_dev": round(std_dev, 6),
    }


@dataclass
class ScalabilityMetrics:
    """Consolidated performance analytics parcel for an empirical execution run.

    Provides rigorous formulas for Speedup, Parallel Efficiency, Throughput,
    Worker Utilization, and Load Imbalance.
    """
    sequential_time_s: float
    parallel_time_s: float
    worker_count: int
    work_units: int = 0
    startup_s: float = 0.0
    dispatch_s: float = 0.0
    collection_s: float = 0.0
    merge_s: float = 0.0
    worker_compute_times: List[float] = field(default_factory=list)

    @property
    def speedup(self) -> float:
        """Amdahl Speedup: S = T_sequential / T_parallel.

        Classification: MATHEMATICALLY_DERIVED.
        Returns 0.0 if parallel time is zero or negative.
        """
        if self.parallel_time_s <= 0.0 or self.sequential_time_s < 0.0:
            return 0.0
        return self.sequential_time_s / self.parallel_time_s

    @property
    def parallel_efficiency(self) -> float:
        """Parallel Efficiency: E = Speedup / WorkerCount.

        Classification: MATHEMATICALLY_DERIVED.
        Returns 0.0 if worker count is zero or negative.
        """
        if self.worker_count <= 0 or self.speedup <= 0.0:
            return 0.0
        return self.speedup / self.worker_count

    @property
    def efficiency_pct(self) -> float:
        """Percentage Efficiency: E% = (Speedup / WorkerCount) * 100%."""
        return self.parallel_efficiency * 100.0

    @property
    def throughput_items_per_s(self) -> float:
        """Throughput: Completed Work Units / Total Parallel Execution Time.

        Classification: MATHEMATICALLY_DERIVED.
        """
        if self.parallel_time_s <= 0.0 or self.work_units <= 0:
            return 0.0
        return self.work_units / self.parallel_time_s

    @property
    def total_computation_time_s(self) -> float:
        """Cumulative CPU computation time across all worker processes.

        Classification: DIRECTLY_MEASURED (sum of worker CPU timers).
        """
        return sum(self.worker_compute_times)

    @property
    def max_worker_compute_s(self) -> float:
        """Computation duration of the slowest worker (critical execution path)."""
        return max(self.worker_compute_times) if self.worker_compute_times else 0.0

    @property
    def avg_worker_compute_s(self) -> float:
        """Average computation duration across all workers."""
        if not self.worker_compute_times:
            return 0.0
        return sum(self.worker_compute_times) / len(self.worker_compute_times)

    @property
    def min_worker_compute_s(self) -> float:
        """Computation duration of the fastest worker."""
        return min(self.worker_compute_times) if self.worker_compute_times else 0.0

    @property
    def worker_utilization_pct(self) -> float:
        """Worker Utilization: U = (Cumulative Compute / (WorkerCount * Makespan)) * 100%.

        Classification: MATHEMATICALLY_DERIVED.
        Bounded strictly between 0% and 100%.
        """
        if self.worker_count <= 0 or self.parallel_time_s <= 0.0:
            return 0.0
        theoretical_capacity = self.worker_count * self.parallel_time_s
        u = (self.total_computation_time_s / theoretical_capacity) * 100.0
        return max(0.0, min(100.0, u))

    @property
    def load_imbalance(self) -> float:
        """Load Imbalance: (Max Worker Time - Avg Worker Time) / Avg Worker Time.

        Classification: MATHEMATICALLY_DERIVED.
        Quantifies workload skew across worker processes.
        A perfectly balanced workload yields 0.0 (0%).
        """
        avg_w = self.avg_worker_compute_s
        if avg_w <= 0.0:
            return 0.0
        return max(0.0, (self.max_worker_compute_s - avg_w) / avg_w)

    @property
    def load_imbalance_pct(self) -> float:
        """Percentage Load Imbalance."""
        return self.load_imbalance * 100.0

    @property
    def estimated_distribution_overhead_s(self) -> float:
        """Estimated Distribution and Collection Overhead.

        Formula: T_dispatch + max(0, T_collection - max_worker_compute).
        Classification: ESTIMATED_RESIDUAL (derived residual estimate).
        """
        residual = max(0.0, self.collection_s - self.max_worker_compute_s)
        return self.dispatch_s + residual

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary with classified values."""
        return {
            "sequential_time_s": round(self.sequential_time_s, 6),
            "parallel_time_s": round(self.parallel_time_s, 6),
            "worker_count": self.worker_count,
            "work_units": self.work_units,
            "speedup": round(self.speedup, 4),
            "parallel_efficiency": round(self.parallel_efficiency, 4),
            "efficiency_pct": round(self.efficiency_pct, 2),
            "throughput_items_per_s": round(self.throughput_items_per_s, 2),
            "total_computation_time_s": round(self.total_computation_time_s, 6),
            "startup_overhead_s": round(self.startup_s, 6),
            "dispatch_overhead_s": round(self.dispatch_s, 6),
            "collection_window_s": round(self.collection_s, 6),
            "merge_overhead_s": round(self.merge_s, 6),
            "estimated_distribution_overhead_s": round(self.estimated_distribution_overhead_s, 6),
            "max_worker_compute_s": round(self.max_worker_compute_s, 6),
            "avg_worker_compute_s": round(self.avg_worker_compute_s, 6),
            "min_worker_compute_s": round(self.min_worker_compute_s, 6),
            "worker_utilization_pct": round(self.worker_utilization_pct, 2),
            "load_imbalance": round(self.load_imbalance, 4),
            "load_imbalance_pct": round(self.load_imbalance_pct, 2),
            "worker_compute_times": [round(t, 6) for t in self.worker_compute_times],
        }

