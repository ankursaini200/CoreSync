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
]
