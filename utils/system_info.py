"""System hardware detection, CPU topology inspection, and OS information for CoreSync."""

from dataclasses import dataclass, field
import logging
import os
import platform
import re
from typing import Dict, List, Optional, Tuple

import psutil

from utils.cpu_topology import CPUTopology, parse_sysfs_topology

logger = logging.getLogger("CoreSync.SystemInfo")


@dataclass
class SystemSummary:
    """Consolidated hardware and system environment summary."""
    cpu_model: str
    cpu_vendor: str
    architecture: str
    os_name: str
    os_kernel: str
    physical_cores: int
    logical_cores: int
    available_cpus: int
    current_affinity: List[int]
    topology: CPUTopology
    min_freq_mhz: Optional[float] = None
    max_freq_mhz: Optional[float] = None
    detection_status: str = "Verified"


_CACHED_SUMMARY: Optional[SystemSummary] = None


def get_cpu_model_and_vendor() -> Tuple[str, str]:
    """Extract CPU model name and vendor identifier from /proc/cpuinfo or platform."""
    model = "Unknown CPU"
    vendor = "Unknown Vendor"

    # Primary Linux source: /proc/cpuinfo
    cpuinfo_path = "/proc/cpuinfo"
    if os.path.exists(cpuinfo_path):
        try:
            with open(cpuinfo_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if not line.strip():
                        continue
                    if ":" in line:
                        key, val = [p.strip() for p in line.split(":", 1)]
                        if key in ("model name", "Hardware", "Processor") and model == "Unknown CPU":
                            model = val
                        elif key == "vendor_id" and vendor == "Unknown Vendor":
                            vendor = val
                        if model != "Unknown CPU" and vendor != "Unknown Vendor":
                            break
        except Exception as e:
            logger.warning(f"Could not read {cpuinfo_path}: {e}")

    # Fallback to platform.processor()
    if model == "Unknown CPU":
        proc = platform.processor()
        if proc:
            model = proc

    # Standardize vendor if identifiable from model
    if vendor == "Unknown Vendor":
        if "Intel" in model:
            vendor = "GenuineIntel"
        elif "AMD" in model:
            vendor = "AuthenticAMD"

    return model, vendor


def get_process_affinity() -> List[int]:
    """Retrieve current process CPU affinity mask."""
    try:
        proc = psutil.Process(os.getpid())
        if hasattr(proc, "cpu_affinity"):
            return sorted(proc.cpu_affinity())
    except Exception as e:
        logger.debug(f"psutil.cpu_affinity failed: {e}")

    try:
        if hasattr(os, "sched_getaffinity"):
            return sorted(os.sched_getaffinity(0))
    except Exception as e:
        logger.debug(f"os.sched_getaffinity failed: {e}")

    # Safe fallback: all logical CPUs
    logical = psutil.cpu_count(logical=True) or 1
    return list(range(logical))


def get_cpu_frequency_range() -> Tuple[Optional[float], Optional[float]]:
    """Retrieve overall min and max CPU frequency in MHz."""
    try:
        freq = psutil.cpu_freq()
        if freq:
            min_f = freq.min if freq.min and freq.min > 0 else None
            max_f = freq.max if freq.max and freq.max > 0 else None
            return min_f, max_f
    except Exception as e:
        logger.debug(f"psutil.cpu_freq failed: {e}")

    return None, None


def get_system_summary(force_refresh: bool = False) -> SystemSummary:
    """Retrieve or compute cached hardware and system information.

    Args:
        force_refresh: If True, bypass cache and re-probe system.

    Returns:
        SystemSummary dataclass instance.
    """
    global _CACHED_SUMMARY
    if _CACHED_SUMMARY is not None and not force_refresh:
        return _CACHED_SUMMARY

    # 1. Parse sysfs topology
    try:
        topology = parse_sysfs_topology()
    except Exception as e:
        logger.error(f"Failed to parse sysfs topology: {e}")
        topology = CPUTopology(source="fallback")

    # 2. Query CPU model & vendor
    cpu_model, cpu_vendor = get_cpu_model_and_vendor()

    # 3. Counts
    logical_cores = topology.logical_cpu_count or (psutil.cpu_count(logical=True) or 1)
    physical_cores = topology.physical_core_count or (psutil.cpu_count(logical=False) or logical_cores)

    # 4. Process affinity
    affinity = get_process_affinity()
    available_cpus = len(affinity)

    # 5. OS & Architecture
    os_name = f"{platform.system()} ({platform.distro() if hasattr(platform, 'distro') else platform.system()})"
    # On Arch / Linux, read pretty name if available
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_name = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass

    os_kernel = f"Linux {platform.release()}"
    arch = platform.machine() or "x86_64"

    # 6. Frequency range
    min_freq, max_freq = get_cpu_frequency_range()

    # If psutil didn't report max_freq, check topology max_freq
    if max_freq is None and topology.logical_cpus:
        freqs = [c.max_freq_mhz for c in topology.logical_cpus.values() if c.max_freq_mhz is not None]
        if freqs:
            max_freq = max(freqs)

    status = "Verified (sysfs + PMU)" if topology.is_hybrid else "Verified (Standard)"

    summary = SystemSummary(
        cpu_model=cpu_model,
        cpu_vendor=cpu_vendor,
        architecture=arch,
        os_name=os_name,
        os_kernel=os_kernel,
        physical_cores=physical_cores,
        logical_cores=logical_cores,
        available_cpus=available_cpus,
        current_affinity=affinity,
        topology=topology,
        min_freq_mhz=min_freq,
        max_freq_mhz=max_freq,
        detection_status=status,
    )

    _CACHED_SUMMARY = summary
    return summary

