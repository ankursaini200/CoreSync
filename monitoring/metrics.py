"""Performance metrics, speedup, and efficiency calculations for CoreSync."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionMetrics:
    """Detailed breakdown of parallel execution timings and efficiency."""
    sequential_time_ms: float
    parallel_total_time_ms: float
    worker_count: int
    startup_time_ms: float = 0.0
    transfer_time_ms: float = 0.0
    compute_time_ms: float = 0.0
    gather_time_ms: float = 0.0

    @property
    def speedup(self) -> float:
        """Calculate Amdahl Speedup: S = T_seq / T_par."""
        if self.parallel_total_time_ms <= 0:
            return 0.0
        return self.sequential_time_ms / self.parallel_total_time_ms

    @property
    def compute_speedup(self) -> float:
        """Calculate raw compute speedup ignoring IPC and spawn latency."""
        if self.compute_time_ms <= 0:
            return 0.0
        return self.sequential_time_ms / self.compute_time_ms

    @property
    def parallel_efficiency(self) -> float:
        """Calculate Parallel Efficiency: E = (Speedup / WorkerCount) * 100%."""
        if self.worker_count <= 0:
            return 0.0
        return (self.speedup / self.worker_count) * 100.0

    @property
    def compute_efficiency(self) -> float:
        """Calculate raw compute efficiency."""
        if self.worker_count <= 0:
            return 0.0
        return (self.compute_speedup / self.worker_count) * 100.0

