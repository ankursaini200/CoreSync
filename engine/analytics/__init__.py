"""CoreSync Performance Analytics Subsystem.

Strict Architectural Rule: This module and its submodules MUST NOT import PySide6 or any Qt modules.
Provides execution performance analytics, Amdahl's Law scalability modeling,
repeatable multi-engine benchmarking, and local benchmark history management.
"""

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

__all__ = [
    "MetricClassification",
    "ScalabilityMetrics",
    "calculate_sample_statistics",
    "AmdahlCalculator",
    "AmdahlPrediction",
    "BenchmarkEngineType",
    "BenchmarkIterationRecord",
    "BenchmarkSessionResult",
    "BenchmarkingEngine",
    "get_sanitized_hardware_metadata",
    "BenchmarkHistoryManager",
]

