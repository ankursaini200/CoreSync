"""CoreSync computation and multiprocessing engine."""

from engine.affinity import (
    AffinityPolicy,
    AffinityResult,
    get_available_system_cpus,
    get_process_affinity,
    resolve_worker_affinities,
    set_process_affinity,
)
from engine.process_manager import (
    ParentDeathProtectionResult,
    PlatformProtectionCapability,
    ProcessManager,
    WorkerLifecycleStatus,
    WorkerMetadata,
    enable_parent_death_protection,
    get_platform_protection_capabilities,
)
from engine.resource_guard import ResourceGuard, ResourceLimits
from engine.process_scheduler import (
    AlgorithmType,
    PriorityDirection,
    Process,
    ProcessSchedulerSimulator,
    SimulationResult,
)
from engine.analytics import (
    AmdahlCalculator,
    AmdahlPrediction,
    BenchmarkEngineType,
    BenchmarkHistoryManager,
    BenchmarkSessionResult,
    BenchmarkingEngine,
    MetricClassification,
    ScalabilityMetrics,
)

__all__ = [
    "ProcessManager",
    "WorkerLifecycleStatus",
    "WorkerMetadata",
    "ParentDeathProtectionResult",
    "PlatformProtectionCapability",
    "enable_parent_death_protection",
    "get_platform_protection_capabilities",
    "AffinityPolicy",
    "AffinityResult",
    "get_available_system_cpus",
    "get_process_affinity",
    "resolve_worker_affinities",
    "set_process_affinity",
    "ResourceGuard",
    "ResourceLimits",
    "ProcessSchedulerSimulator",
    "Process",
    "AlgorithmType",
    "PriorityDirection",
    "SimulationResult",
    "MetricClassification",
    "ScalabilityMetrics",
    "AmdahlCalculator",
    "AmdahlPrediction",
    "BenchmarkEngineType",
    "BenchmarkSessionResult",
    "BenchmarkingEngine",
    "BenchmarkHistoryManager",
]
