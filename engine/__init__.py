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
    ProcessManager,
    WorkerLifecycleStatus,
    WorkerMetadata,
)
from engine.resource_guard import ResourceGuard, ResourceLimits

__all__ = [
    "ProcessManager",
    "WorkerLifecycleStatus",
    "WorkerMetadata",
    "AffinityPolicy",
    "AffinityResult",
    "get_available_system_cpus",
    "get_process_affinity",
    "resolve_worker_affinities",
    "set_process_affinity",
    "ResourceGuard",
    "ResourceLimits",
]
