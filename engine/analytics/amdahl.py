"""Theoretical Scalability and Amdahl's Law Calculator for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides pure mathematical modeling of Gene Amdahl's 1967 scalability law:
    Speedup(P, N) = 1 / ((1 - P) + P / N)

Clearly distinguishes theoretical mathematical upper bounds from empirical runtime measurements.
"""

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class AmdahlPrediction:
    """Theoretical prediction parcel derived from Amdahl's Law."""
    parallel_fraction: float           # P in [0.0, 1.0]
    serial_fraction: float             # 1.0 - P
    processors: int                    # N >= 1
    theoretical_speedup: float         # S(P, N)
    theoretical_efficiency: float      # E = S / N
    theoretical_efficiency_pct: float  # E% = (S / N) * 100%
    theoretical_max_speedup: float     # S_max as N -> inf (1 / (1 - P) or inf)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parallel_fraction": round(self.parallel_fraction, 4),
            "serial_fraction": round(self.serial_fraction, 4),
            "processors": self.processors,
            "theoretical_speedup": round(self.theoretical_speedup, 4),
            "theoretical_efficiency": round(self.theoretical_efficiency, 4),
            "theoretical_efficiency_pct": round(self.theoretical_efficiency_pct, 2),
            "theoretical_max_speedup": (
                round(self.theoretical_max_speedup, 4)
                if not math.isinf(self.theoretical_max_speedup)
                else "Infinity"
            ),
            "is_theoretical": True,
            "provenance": "Amdahl's Law (1967)",
        }


class AmdahlCalculator:
    """Mathematical engine computing theoretical speedup limits according to Amdahl's Law."""

    @staticmethod
    def calculate_speedup(parallel_fraction: float, processors: int) -> float:
        """Calculate theoretical Amdahl speedup: S = 1 / ((1 - P) + P / N).

        Args:
            parallel_fraction: Parallelizable fraction of the workload P in [0.0, 1.0].
            processors: Number of execution units N >= 1.

        Returns:
            Theoretical speedup factor S >= 1.0.

        Raises:
            ValueError: If P is not in [0.0, 1.0] or N < 1.
        """
        if not (0.0 <= parallel_fraction <= 1.0):
            raise ValueError(f"Parallel fraction P must be between 0.0 and 1.0, got: {parallel_fraction}")
        if processors < 1:
            raise ValueError(f"Processor count N must be at least 1, got: {processors}")

        # Edge case: N == 1 always yields Speedup = 1.0
        if processors == 1:
            return 1.0

        # Edge case: P == 0.0 (completely serial) yields Speedup = 1.0
        if parallel_fraction == 0.0:
            return 1.0

        # Edge case: P == 1.0 (completely parallel) yields Speedup = N (linear scaling)
        if parallel_fraction == 1.0:
            return float(processors)

        serial_fraction = round(1.0 - parallel_fraction, 10)
        denominator = serial_fraction + (parallel_fraction / processors)
        return 1.0 / denominator

    @staticmethod
    def calculate_efficiency(parallel_fraction: float, processors: int) -> float:
        """Calculate theoretical parallel efficiency: E = Speedup / N."""
        s = AmdahlCalculator.calculate_speedup(parallel_fraction, processors)
        return s / float(processors)

    @staticmethod
    def calculate_max_speedup(parallel_fraction: float) -> float:
        """Calculate theoretical maximum speedup as N approaches infinity: S_max = 1 / (1 - P)."""
        if not (0.0 <= parallel_fraction <= 1.0):
            raise ValueError(f"Parallel fraction P must be between 0.0 and 1.0, got: {parallel_fraction}")

        serial_fraction = round(1.0 - parallel_fraction, 10)
        if serial_fraction <= 1e-12:
            return math.inf
        return 1.0 / serial_fraction

    @staticmethod
    def predict(parallel_fraction: float, processors: int) -> AmdahlPrediction:
        """Generate a complete theoretical prediction parcel."""
        s = AmdahlCalculator.calculate_speedup(parallel_fraction, processors)
        e = s / float(processors)
        s_max = AmdahlCalculator.calculate_max_speedup(parallel_fraction)
        return AmdahlPrediction(
            parallel_fraction=parallel_fraction,
            serial_fraction=round(1.0 - parallel_fraction, 10),
            processors=processors,
            theoretical_speedup=s,
            theoretical_efficiency=e,
            theoretical_efficiency_pct=e * 100.0,
            theoretical_max_speedup=s_max,
        )

    @staticmethod
    def generate_scalability_curve(
        parallel_fraction: float,
        max_processors: int = 64,
    ) -> List[Tuple[int, float, float]]:
        """Generate curve data points across processor count sweep.

        Args:
            parallel_fraction: Fraction P in [0.0, 1.0].
            max_processors: Maximum core count to compute (default 64).

        Returns:
            List of tuples: (core_count, speedup, efficiency_pct).
        """
        curve = []
        for n in range(1, max_processors + 1):
            s = AmdahlCalculator.calculate_speedup(parallel_fraction, n)
            eff_pct = (s / n) * 100.0
            curve.append((n, round(s, 4), round(eff_pct, 2)))
        return curve

    @staticmethod
    def explain_limitations() -> Dict[str, str]:
        """Educational documentation on the fundamental assumptions and limitations of Amdahl's Law."""
        return {
            "fixed_problem_size": (
                "Amdahl's Law assumes a fixed problem size (strong scaling). In reality, users often solve "
                "larger problems as computing power increases (weak scaling, modeled by Gustafson's Law: S = N - (1-P)(N-1))."
            ),
            "zero_communication_overhead": (
                "The formula assumes inter-process communication (IPC), thread synchronization, mutex contention, "
                "and data serialization cost zero microseconds. In real multicore execution, communication overhead "
                "eventually dominates, causing speedup to degrade rather than asymptote."
            ),
            "homogeneous_hardware_assumption": (
                "Amdahl's classical formula assumes identical processors. On modern hybrid architectures (e.g. Intel Alder Lake "
                "or Apple Silicon), Performance cores and Efficiency cores exhibit asymmetric execution throughput."
            ),
            "memory_bus_and_cache_contention": (
                "Simultaneous memory accesses by multiple worker processes cause cache coherency traffic, L3 cache eviction, "
                "and DRAM bus bandwidth saturation not accounted for in theoretical math."
            ),
        }
