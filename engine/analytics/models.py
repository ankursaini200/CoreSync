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

    Classification Standards:
        - DIRECTLY_MEASURED: Timed intervals captured via high-resolution monotonic
          elapsed time (time.perf_counter / time.perf_counter_ns), process CPU execution
          time (psutil.cpu_times: user + system), or process resident memory usage
          (psutil.Process.memory_info: RSS).
          * time.perf_counter() measures monotonic elapsed wall-clock time, NOT a hardware clock.
          * Process CPU time measures active CPU runtime and is distinct from wall-clock time.
          * RSS memory measures process RAM usage, NOT CPU telemetry.
        - MATHEMATICALLY_DERIVED: Deterministic mathematical formulas computed from
          verified measurements (e.g. Speedup S = T_seq / T_par, Parallel Efficiency E = S / W,
          Throughput = items / T_par, Load Imbalance). Each derived metric explicitly identifies
          the measured inputs used in its calculation.
        - ESTIMATED_RESIDUAL: Aggregate residual intervals derived by subtracting measured
          worker computation from total wall-clock makespan. Labeled strictly as aggregate
          residual estimates and not claimed to independently measure individual micro-phases
          (IPC transit, serialization, spawn) unless isolated timing boundaries exist.
        - SIMULATED_VIRTUAL: Discrete logical clock cycles ('ticks') and virtual core state
          allocations from the educational Virtual Lab simulator. Must never be presented
          as real host measurements or physical CPU throughput.
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


def calculate_sample_statistics(values: List[float]) -> Dict[str, Any]:
    """Compute standard descriptive sample statistics on a numerical sample.

    Mathematical Invariants:
        - Sample Standard Deviation s uses Bessel's correction with denominator (N - 1).
        - For N = 1, sample standard deviation is mathematically undefined because
          the denominator (N - 1) = 0. It is returned as None (displayed as 'N/A (insufficient samples)').
          It is NEVER claimed to be a measured zero variance.
        - For N = 0 (empty sample), std_dev is returned as None (displayed as 'N/A (empty sample)').

    Args:
        values: List of empirical observations.

    Returns:
        Dictionary with count, mean, min, max, median, variance, std_dev, and std_dev_display.
    """
    if not values:
        return {
            "count": 0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
            "variance": None,
            "std_dev": None,
            "std_dev_display": "N/A (empty sample)",
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

    # Sample standard deviation (Bessel's correction N - 1 for N > 1)
    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        std_dev = math.sqrt(max(0.0, variance))
        std_display = f"±{round(std_dev, 4)}"
        var_out: Optional[float] = round(variance, 6)
        std_out: Optional[float] = round(std_dev, 6)
    else:
        # N == 1: Sample variance/std_dev is mathematically undefined (division by 1 - 1 = 0)
        var_out = None
        std_out = None
        std_display = "N/A (insufficient samples, N=1)"

    return {
        "count": n,
        "mean": round(mean_val, 6),
        "min": round(min_val, 6),
        "max": round(max_val, 6),
        "median": round(median_val, 6),
        "variance": var_out,
        "std_dev": std_out,
        "std_dev_display": std_display,
    }


@dataclass
class ScalabilityMetrics:
    """Consolidated performance analytics parcel for an empirical execution run.

    Provides rigorous formulas for Speedup, Parallel Efficiency, Throughput,
    Worker Utilization, and Load Imbalance with clear provenance tracing.
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
        Measured Inputs: sequential_time_s (baseline wall-clock elapsed time),
                         parallel_time_s (parallel wall-clock makespan).
        Returns 0.0 if parallel time is zero or negative.
        """
        if self.parallel_time_s <= 0.0 or self.sequential_time_s < 0.0:
            return 0.0
        return self.sequential_time_s / self.parallel_time_s

    @property
    def parallel_efficiency(self) -> float:
        """Parallel Efficiency: E = Speedup / WorkerCount.

        Classification: MATHEMATICALLY_DERIVED.
        Measured/Configured Inputs: speedup (derived), worker_count (configured).
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
        Measured Inputs: work_units (counted output items),
                         parallel_time_s (wall-clock makespan).
        """
        if self.parallel_time_s <= 0.0 or self.work_units <= 0:
            return 0.0
        return self.work_units / self.parallel_time_s

    @property
    def total_computation_time_s(self) -> float:
        """Cumulative elapsed computation time across all worker processes.

        Classification: DIRECTLY_MEASURED (sum of worker monotonic compute timers).
        Measured Inputs: worker_compute_times list.
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
        Measured Inputs: total_computation_time_s, worker_count, parallel_time_s.
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
        Measured Inputs: max_worker_compute_s, avg_worker_compute_s.
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
    def aggregate_estimated_residual_s(self) -> float:
        """Aggregate Estimated Residual Overhead.

        Formula: max(0.0, parallel_time_s - max_worker_compute_s).
        Classification: ESTIMATED_RESIDUAL (derived aggregate residual estimate).

        Important: This measures the residual wall-clock difference between the critical-path
        worker computation and total makespan. It encompasses OS scheduling jitter, worker process
        wake-up, queue polling delays, and IPC serialization/transit collectively. It is NOT
        an independent measurement of each sub-stage, and is strictly clamped >= 0.0 to prevent
        negative residual values.
        """
        if self.parallel_time_s <= 0.0 or not self.worker_compute_times:
            return 0.0
        return max(0.0, self.parallel_time_s - self.max_worker_compute_s)

    @property
    def estimated_distribution_overhead_s(self) -> float:
        """Legacy compatibility alias for aggregate_estimated_residual_s."""
        return self.aggregate_estimated_residual_s

    @property
    def provenance_map(self) -> Dict[str, Dict[str, str]]:
        """Document metric classifications and measured inputs for accountability."""
        return {
            "sequential_time_s": {
                "classification": MetricClassification.DIRECTLY_MEASURED.value,
                "input_source": "Sequential baseline wall-clock monotonic timer",
            },
            "parallel_time_s": {
                "classification": MetricClassification.DIRECTLY_MEASURED.value,
                "input_source": "Parallel makespan wall-clock monotonic timer",
            },
            "total_computation_time_s": {
                "classification": MetricClassification.DIRECTLY_MEASURED.value,
                "input_source": "Sum of per-worker monotonic kernel compute timers",
            },
            "speedup": {
                "classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                "formula": "T_sequential / T_parallel",
                "measured_inputs": "sequential_time_s, parallel_time_s",
            },
            "parallel_efficiency": {
                "classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                "formula": "Speedup / WorkerCount",
                "measured_inputs": "speedup, worker_count",
            },
            "throughput_items_per_s": {
                "classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                "formula": "work_units / parallel_time_s",
                "measured_inputs": "work_units, parallel_time_s",
            },
            "worker_utilization_pct": {
                "classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                "formula": "(total_computation_time_s / (worker_count * parallel_time_s)) * 100",
                "measured_inputs": "total_computation_time_s, worker_count, parallel_time_s",
            },
            "load_imbalance": {
                "classification": MetricClassification.MATHEMATICALLY_DERIVED.value,
                "formula": "(max_worker_compute_s - avg_worker_compute_s) / avg_worker_compute_s",
                "measured_inputs": "max_worker_compute_s, avg_worker_compute_s",
            },
            "aggregate_estimated_residual_s": {
                "classification": MetricClassification.ESTIMATED_RESIDUAL.value,
                "formula": "max(0.0, parallel_time_s - max_worker_compute_s)",
                "measured_inputs": "parallel_time_s, max_worker_compute_s",
                "notes": "Aggregate residual difference; does not measure discrete micro-phases independently.",
            },
        }

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
            "aggregate_estimated_residual_s": round(self.aggregate_estimated_residual_s, 6),
            "estimated_distribution_overhead_s": round(self.estimated_distribution_overhead_s, 6),
            "max_worker_compute_s": round(self.max_worker_compute_s, 6),
            "avg_worker_compute_s": round(self.avg_worker_compute_s, 6),
            "min_worker_compute_s": round(self.min_worker_compute_s, 6),
            "worker_utilization_pct": round(self.worker_utilization_pct, 2),
            "load_imbalance": round(self.load_imbalance, 4),
            "load_imbalance_pct": round(self.load_imbalance_pct, 2),
            "worker_compute_times": [round(t, 6) for t in self.worker_compute_times],
            "provenance_map": self.provenance_map,
        }

