"""Resource Management and Safety Guard Subsystem for CoreSync.

Enforces strict bounds on worker concurrency, verifies system memory headroom before
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
DEFAULT_PER_WORKER_EST_MB = 32.0
DEFAULT_MAX_WORKER_RAM_MB = 2048.0
HEAVY_LOAD_CPU_THRESHOLD_PCT = 95.0
HEAVY_LOAD_MEM_THRESHOLD_PCT = 95.0


@dataclass
class ResourceLimits:
    """Configurable resource safety boundaries.

    Attributes:
        max_workers: Absolute ceiling for spawned worker processes (default 64, enforced via clamping).
        min_free_ram_mb: Minimum available RAM before spawning worker pools (default 256 MB, enforced rejection if insufficient).
        per_worker_est_mb: Estimated RAM footprint per spawned Python worker process (default 32 MB).
        max_worker_ram_mb: RSS memory ceiling per single worker before flagging (default 2048 MB / 2 GB, monitored).
        warn_on_heavy_load: Whether to log advisory warnings when host CPU/RAM exceed 95% saturation (advisory warning only; non-blocking).
    """
    max_workers: int = DEFAULT_HARD_WORKER_CAP
    min_free_ram_mb: float = DEFAULT_MIN_FREE_RAM_MB
    per_worker_est_mb: float = DEFAULT_PER_WORKER_EST_MB
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
        clamped, _ = self.validate_worker_request(requested)
        return clamped

    def validate_worker_request(self, requested: int) -> Tuple[int, Optional[str]]:
        """Validate and clamp requested worker count, returning an informative explanation if adjusted.

        Returns:
            Tuple of (clamped_worker_count, adjustment_reason_or_None).
        """
        # Dynamic upper bound: at least 4, up to 2x logical cores, clamped to max_workers hard cap
        dynamic_cap = min(self.limits.max_workers, max(4, self._logical_cores * 2))

        try:
            req_int = int(requested)
        except (ValueError, TypeError):
            msg = f"Invalid worker count '{requested}'; defaulted to 1."
            logger.warning(msg)
            return 1, msg

        if req_int <= 0:
            msg = f"Requested worker count {req_int} is invalid (must be >= 1); adjusted to 1."
            logger.warning(msg)
            return 1, msg

        if req_int > dynamic_cap:
            msg = (
                f"Requested worker count {req_int} exceeds safety limit ({dynamic_cap} = "
                f"min(cap={self.limits.max_workers}, 2x logical={self._logical_cores * 2})); "
                f"clamped to {dynamic_cap} to prevent system saturation."
            )
            logger.info(msg)
            return dynamic_cap, msg

        return req_int, None

    def check_memory_headroom(
        self,
        required_mb: Optional[float] = None,
        worker_count: int = 1,
    ) -> Tuple[bool, float, str]:
        """Verify whether sufficient system RAM is available before spawning workers.

        Accounts for base safety headroom plus the aggregate estimated worker footprint:
            Threshold = max(min_free_ram_mb, worker_count * per_worker_est_mb)

        Returns:
            Tuple of (is_safe, available_mb, message).
        """
        base_req = required_mb or self.limits.min_free_ram_mb
        worker_req = max(1, worker_count) * self.limits.per_worker_est_mb
        effective_req = max(base_req, worker_req)

        try:
            vm = psutil.virtual_memory()
            avail_mb = vm.available / (1024 * 1024)

            if avail_mb < effective_req:
                msg = (
                    f"Low system memory warning: {avail_mb:.1f} MB available, recommended minimum is "
                    f"{effective_req:.1f} MB for {worker_count} workers."
                )
                logger.warning(msg)
                return False, avail_mb, msg

            return True, avail_mb, f"Sufficient memory headroom: {avail_mb:.1f} MB available (required {effective_req:.1f} MB)."
        except Exception as e:
            logger.debug(f"Failed to query virtual memory: {e}")
            return True, 0.0, f"Could not query memory stats ({e}); proceeding with caution."

    def is_system_under_heavy_load(
        self,
        cpu_threshold: float = HEAVY_LOAD_CPU_THRESHOLD_PCT,
        mem_threshold: float = HEAVY_LOAD_MEM_THRESHOLD_PCT,
    ) -> Tuple[bool, str]:
        """Detect whether host CPU or RAM is saturated above advisory warning thresholds (non-blocking).

        Returns:
            Tuple of (is_heavy, advisory_message).
        """
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            mem_pct = vm.percent

            if cpu_pct >= cpu_threshold or mem_pct >= mem_threshold:
                msg = (
                    f"Advisory Warning: Host system is under heavy load (CPU: {cpu_pct:.1f}%, RAM: {mem_pct:.1f}%). "
                    f"Utilization exceeds advisory threshold of {cpu_threshold:.0f}%. "
                    f"Execution is not blocked, but performance may be degraded."
                )
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
        """Verify whether a single CoreSync worker has exceeded its memory threshold."""
        _, rss_mb = self.inspect_process_resources(pid)
        if rss_mb > self.limits.max_worker_ram_mb:
            msg = f"Worker PID {pid} exceeded memory threshold: {rss_mb:.1f} MB > {self.limits.max_worker_ram_mb} MB"
            logger.warning(msg)
            return True, msg
        return False, None
