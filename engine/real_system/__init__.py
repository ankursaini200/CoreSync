"""Real system execution and stress testing modules."""

from engine.real_system.cpu_stress import (
    RealCPUStressGenerator,
    StressStatus,
    DEFAULT_STRESS_DURATION_S,
    MAX_STRESS_DURATION_S,
)

__all__ = [
    "RealCPUStressGenerator",
    "StressStatus",
    "DEFAULT_STRESS_DURATION_S",
    "MAX_STRESS_DURATION_S",
]

