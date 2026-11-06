"""CPU Affinity Management Subsystem for CoreSync.

Provides cross-platform CPU affinity assignment, inspection, validation,
and worker allocation policies (Automatic, Round Robin, One-to-One, Manual,
and Hybrid P-core/E-core filtering).
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import os
import platform
import sys
from typing import Dict, List, Optional, Set, Tuple, Union

import psutil

from utils.cpu_topology import CoreType, CPUTopology

logger = logging.getLogger("CoreSync.Affinity")


class AffinityPolicy(str, Enum):
    """CPU affinity allocation policies for worker processes."""
    AUTOMATIC = "automatic"          # Unpinned, OS scheduler decides across all available CPUs
    ROUND_ROBIN = "round_robin"      # Workers distributed round-robin across selected/available CPUs
    ONE_TO_ONE = "one_to_one"        # Each worker pinned to a distinct logical CPU (modulo total available)
    P_CORE_ONLY = "p_core_only"      # Workers pinned exclusively to Performance cores (hybrid processors only)
    E_CORE_ONLY = "e_core_only"      # Workers pinned exclusively to Efficient cores (hybrid processors only)
    CUSTOM = "custom"                # Workers distributed round-robin across a user-selected list of CPUs
    MANUAL = "manual"                # Explicit worker-to-CPU mapping provided by caller


@dataclass
class AffinityResult:
    """Outcome of an affinity assignment attempt."""
    success: bool
    applied_cpus: List[int]
    requested_cpus: List[int]
    platform_name: str
    message: Optional[str] = None

    def __bool__(self) -> bool:
        return self.success


def get_available_system_cpus() -> List[int]:
    """Return sorted list of logical CPU IDs available to the current process."""
    # 1. Linux os.sched_getaffinity
    if hasattr(os, "sched_getaffinity"):
        try:
            return sorted(list(os.sched_getaffinity(0)))
        except Exception as e:
            logger.debug(f"sched_getaffinity failed: {e}")

    # 2. psutil process affinity
    try:
        proc = psutil.Process(os.getpid())
        if hasattr(proc, "cpu_affinity"):
            aff = proc.cpu_affinity()
            if aff:
                return sorted(list(aff))
    except Exception as e:
        logger.debug(f"psutil cpu_affinity failed: {e}")

    # 3. Fallback: all logical CPUs
    logical = psutil.cpu_count(logical=True) or 1
    return list(range(logical))


def get_process_affinity(pid: Optional[int] = None) -> List[int]:
    """Retrieve current CPU affinity mask for specified PID or current process."""
    target_pid = pid if (pid is not None and pid > 0) else os.getpid()

    # Linux native sched_getaffinity
    if hasattr(os, "sched_getaffinity"):
        try:
            return sorted(list(os.sched_getaffinity(target_pid)))
        except (ProcessLookupError, PermissionError) as e:
            logger.warning(f"sched_getaffinity failed for PID {target_pid}: {e}")
            return []
        except Exception:
            pass

    # psutil fallback
    try:
        proc = psutil.Process(target_pid)
        if hasattr(proc, "cpu_affinity"):
            aff = proc.cpu_affinity()
            if aff:
                return sorted(list(aff))
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.warning(f"psutil cpu_affinity failed for PID {target_pid}: {e}")
        return []
    except Exception:
        pass

    # Fallback for platforms without hard affinity (e.g. Darwin)
    return get_available_system_cpus()


def set_process_affinity(pid: int, cpu_ids: List[int]) -> AffinityResult:
    """Assign CPU affinity mask to a specific process PID.

    Args:
        pid: Operating system Process ID.
        cpu_ids: List of logical CPU IDs to assign.

    Returns:
        AffinityResult indicating whether assignment succeeded and the actual applied affinity.
    """
    plat = platform.system()
    total_logical = psutil.cpu_count(logical=True) or 1
    available_system_cpus = get_available_system_cpus()

    # 1. Input validation
    if not cpu_ids:
        curr = get_process_affinity(pid)
        return AffinityResult(
            success=False,
            applied_cpus=curr,
            requested_cpus=[],
            platform_name=plat,
            message="Requested CPU list is empty.",
        )

    # Check for invalid CPU IDs
    invalid_ids = [c for c in cpu_ids if not isinstance(c, int) or c < 0 or c >= total_logical]
    if invalid_ids:
        curr = get_process_affinity(pid)
        return AffinityResult(
            success=False,
            applied_cpus=curr,
            requested_cpus=cpu_ids,
            platform_name=plat,
            message=f"Invalid logical CPU IDs {invalid_ids}. Valid range is 0 to {total_logical - 1}.",
        )

    # 2. Platform-specific execution
    if plat == "Darwin":
        # macOS kernel (XNU) does not support hard thread/process affinity pinning
        curr = get_process_affinity(pid)
        return AffinityResult(
            success=False,
            applied_cpus=curr,
            requested_cpus=cpu_ids,
            platform_name=plat,
            message="macOS does not support hard CPU affinity pinning; tasks run across all available cores.",
        )

    target_set = sorted(list(set(cpu_ids)))

    # Linux: Try os.sched_setaffinity first
    if plat == "Linux" and hasattr(os, "sched_setaffinity"):
        try:
            os.sched_setaffinity(pid, set(target_set))
            actual = get_process_affinity(pid)
            if set(actual) == set(target_set):
                return AffinityResult(
                    success=True,
                    applied_cpus=actual,
                    requested_cpus=target_set,
                    platform_name=plat,
                    message="CPU affinity applied successfully via os.sched_setaffinity.",
                )
        except PermissionError as e:
            curr = get_process_affinity(pid)
            return AffinityResult(
                success=False,
                applied_cpus=curr,
                requested_cpus=target_set,
                platform_name=plat,
                message=f"Permission denied setting CPU affinity on PID {pid}: {e}",
            )
        except ProcessLookupError as e:
            return AffinityResult(
                success=False,
                applied_cpus=[],
                requested_cpus=target_set,
                platform_name=plat,
                message=f"Process PID {pid} not found: {e}",
            )
        except Exception as e:
            logger.debug(f"os.sched_setaffinity error on PID {pid}: {e}, falling back to psutil")

    # Windows / Linux fallback via psutil
    try:
        proc = psutil.Process(pid)
        if hasattr(proc, "cpu_affinity"):
            proc.cpu_affinity(target_set)
            actual = get_process_affinity(pid)
            if set(actual) == set(target_set):
                return AffinityResult(
                    success=True,
                    applied_cpus=actual,
                    requested_cpus=target_set,
                    platform_name=plat,
                    message="CPU affinity applied successfully via psutil.",
                )
            else:
                return AffinityResult(
                    success=False,
                    applied_cpus=actual,
                    requested_cpus=target_set,
                    platform_name=plat,
                    message=f"CPU affinity mismatch: requested {target_set}, OS reported {actual}.",
                )
        else:
            curr = get_process_affinity(pid)
            return AffinityResult(
                success=False,
                applied_cpus=curr,
                requested_cpus=target_set,
                platform_name=plat,
                message=f"psutil on platform '{plat}' lacks cpu_affinity support.",
            )
    except psutil.AccessDenied as e:
        curr = get_process_affinity(pid)
        return AffinityResult(
            success=False,
            applied_cpus=curr,
            requested_cpus=target_set,
            platform_name=plat,
            message=f"Access denied setting CPU affinity on PID {pid}: {e}",
        )
    except psutil.NoSuchProcess as e:
        return AffinityResult(
            success=False,
            applied_cpus=[],
            requested_cpus=target_set,
            platform_name=plat,
            message=f"Process PID {pid} does not exist: {e}",
        )
    except Exception as e:
        curr = get_process_affinity(pid)
        return AffinityResult(
            success=False,
            applied_cpus=curr,
            requested_cpus=target_set,
            platform_name=plat,
            message=f"Failed to set CPU affinity on PID {pid}: {e}",
        )


def resolve_worker_affinities(
    worker_count: int,
    policy: AffinityPolicy = AffinityPolicy.AUTOMATIC,
    topology: Optional[CPUTopology] = None,
    manual_mapping: Optional[Dict[int, List[int]]] = None,
    custom_cpus: Optional[List[int]] = None,
) -> List[List[int]]:
    """Calculate assigned logical CPU lists for each worker index.

    Args:
        worker_count: Total number of worker processes.
        policy: Chosen allocation policy.
        topology: Verified system CPUTopology (used for hybrid core filtering).
        manual_mapping: Explicit worker_idx -> cpu_ids dictionary for MANUAL policy.
        custom_cpus: Explicit CPU subset for CUSTOM policy.

    Returns:
        List of CPU lists, where index i corresponds to worker i's assigned CPUs.
        An empty list indicates unpinned (AUTOMATIC).
    """
    if worker_count <= 0:
        return []

    available = get_available_system_cpus()
    if not available:
        available = list(range(psutil.cpu_count(logical=True) or 1))

    # 1. Automatic Policy: leave workers unpinned (all available CPUs)
    if policy == AffinityPolicy.AUTOMATIC:
        return [list(available) for _ in range(worker_count)]

    # 2. Manual Policy: user provides exact map
    if policy == AffinityPolicy.MANUAL:
        mapping = manual_mapping or {}
        affinities: List[List[int]] = []
        for i in range(worker_count):
            cpus = mapping.get(i)
            if cpus:
                valid = [c for c in cpus if c in available]
                affinities.append(valid if valid else list(available))
            else:
                affinities.append(list(available))
        return affinities

    # Determine target pool based on policy
    target_pool = list(available)

    if policy == AffinityPolicy.CUSTOM and custom_cpus:
        filtered = [c for c in custom_cpus if c in available]
        if filtered:
            target_pool = filtered
        else:
            logger.warning("Custom CPU list contains no available CPUs; falling back to all available.")

    elif policy == AffinityPolicy.P_CORE_ONLY:
        if topology and topology.is_hybrid and topology.p_cores:
            p_filtered = [c for c in topology.p_cores if c in available]
            if p_filtered:
                target_pool = p_filtered
            else:
                logger.warning("No P-cores are currently available; falling back to all available CPUs.")
        else:
            logger.warning("P-core filtering requested but system is not a verified hybrid processor; falling back.")

    elif policy == AffinityPolicy.E_CORE_ONLY:
        if topology and topology.is_hybrid and topology.e_cores:
            e_filtered = [c for c in topology.e_cores if c in available]
            if e_filtered:
                target_pool = e_filtered
            else:
                logger.warning("No E-cores are currently available; falling back to all available CPUs.")
        else:
            logger.warning("E-core filtering requested but system is not a verified hybrid processor; falling back.")

    # Apply distribution over target pool
    pool_size = len(target_pool)
    affinities = []

    for i in range(worker_count):
        if policy in (
            AffinityPolicy.ROUND_ROBIN,
            AffinityPolicy.P_CORE_ONLY,
            AffinityPolicy.E_CORE_ONLY,
            AffinityPolicy.CUSTOM,
        ):
            assigned_cpu = target_pool[i % pool_size]
            affinities.append([assigned_cpu])
        elif policy == AffinityPolicy.ONE_TO_ONE:
            assigned_cpu = target_pool[i % pool_size]
            affinities.append([assigned_cpu])
        else:
            affinities.append(list(target_pool))

    return affinities

