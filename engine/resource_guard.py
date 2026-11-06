"""Resource Management and Safety Guard Subsystem for CoreSync.

Enforces bounds on worker concurrency, verifies system memory headroom before
spawning, inspects process resource consumption, and detects high system load.
"""

from dataclasses import dataclass
import logging
import os
from typing import Optional, Tuple

import psutil

logger = logging.getLogger("CoreSync.ResourceGuard")

# System safety defaults
DEFAULT_HARD_WORKER_CAP = 64
DEFAULT_MIN_FREE_RAM_MB = 256.0
DEFAULT_MAX_WORKER_RAM_MB = 2048.0
HEAVY_LOAD_CPU_THRESHOLD_PCT = 95.0
HEAVY_LOAD_MEM_THRESHOLD_PCT = 95.0


@dataclass
class ResourceLimits:
    """Configurable resource safety boundaries."""
    max_workers: int = DEFAULT_HARD_WORKER_CAP
    min_free_ram_mb: float = DEFAULT_MIN_FREE_RAM_MB
    max_worker_ram_mb: float = DEFAULT_MAX_WORKER_RAM_MB
    warn_on_heavy_load: bool = True


class ResourceGuard:
    """Enforces resource limits, memory headroom, and worker process bounds."""

    def __init__(self, limits: Optional[ResourceLimits] = None):
        self.limits = limits or ResourceLimits()
        self._logical_cores = psutil.cpu_count(logical=True) or 1

    def clamp_worker_count(self, requested: int) -> int:
        """Clamp worker count to a safe, positive value within system capabilities.

        Prevents accidental negative, zero, or unconstrained worker proliferation.
        """
        # Dynamic upper bound: at least 4, up to 2x logical cores, clamped to max_workers cap
        dynamic_cap = min(self.limits.max_workers, max(4, self._logical_cores * 2))
        clamped = max(1, min(requested, dynamic_cap))

        if clamped != requested:
            logger.info(f"Requested worker count {requested} clamped to safety bound {clamped} (max cap: {dynamic_cap})")
        return clamped

    def check_memory_headroom(self, required_mb: Optional[float] = None) -> Tuple[bool, float, str]:
        """Verify whether sufficient system RAM is available before spawning workers.

        Returns:
            Tuple of (is_safe, available_mb, message).
        """
        req_mb = required_mb or self.limits.min_free_ram_mb
        try:
            vm = psutil.virtual_memory()
            avail_mb = vm.available / (1024 * 1024)

            if avail_mb < req_mb:
                msg = f"Low system memory warning: {avail_mb:.1f} MB available, recommended minimum is {req_mb:.1f} MB."
                logger.warning(msg)
                return False, avail_mb, msg

            return True, avail_mb, f"Sufficient memory headroom: {avail_mb:.1f} MB available."
        except Exception as e:
            logger.debug(f"Failed to query virtual memory: {e}")
            return True, 0.0, "Could not query memory stats; proceeding with caution."

    def is_system_under_heavy_load(self) -> Tuple[bool, str]:
        """Detect whether host CPU or RAM is under saturation."""
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            mem_pct = vm.percent

            if cpu_pct >= HEAVY_LOAD_CPU_THRESHOLD_PCT or mem_pct >= HEAVY_LOAD_MEM_THRESHOLD_PCT:
                msg = f"System under heavy load: CPU {cpu_pct:.1f}%, RAM {mem_pct:.1f}%."
                logger.warning(msg)
                return True, msg

            return False, f"System load nominal: CPU {cpu_pct:.1f}%, RAM {mem_pct:.1f}%."
        except Exception as e:
            return False, f"Load inspection unavailable: {e}"

    def inspect_process_resources(self, pid: int) -> Tuple[float, float]:
        """Safely sample live CPU% and RSS Memory (MB) for a process without raising exceptions.

        Returns:
            Tuple of (cpu_percent, memory_rss_mb).
        """
        try:
            proc = psutil.Process(pid)
            cpu = proc.cpu_percent(interval=None)
            mem_info = proc.memory_info()
            rss_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
            return cpu, rss_mb
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0, 0.0
        except Exception:
            return 0.0, 0.0

    def check_worker_limit_violation(self, pid: int) -> Tuple[bool, Optional[str]]:
        """Verify whether a single CoreSync worker has exceeded memory constraints."""
        _, rss_mb = self.inspect_process_resources(pid)
        if rss_mb > self.limits.max_worker_ram_mb:
            msg = f"Worker PID {pid} exceeded memory threshold: {rss_mb:.1f} MB > {self.limits.max_worker_ram_mb} MB"
            logger.warning(msg)
            return True, msg
        return False, None

