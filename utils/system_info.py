"""System hardware detection, CPU topology inspection, and OS information for CoreSync.

Uses cross-platform hardware providers behind a unified interface.
"""

from dataclasses import dataclass, field
import logging
from typing import Dict, List, Optional, Tuple

from utils.cpu_topology import CPUTopology
from utils.hardware.base import HardwareInfo, RAMInfo, ProcessInfo
from utils.hardware.factory import get_hardware_provider

logger = logging.getLogger("CoreSync.SystemInfo")


@dataclass
class SystemSummary:
    """Consolidated hardware and system environment summary (compatible with HardwareInfo)."""
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
    platform_type: str = "Linux"


_CACHED_SUMMARY: Optional[SystemSummary] = None


def get_cpu_model_and_vendor() -> Tuple[str, str]:
    """Extract CPU model name and vendor identifier."""
    provider = get_hardware_provider()
    info = provider.detect_hardware()
    return info.cpu_model, info.cpu_vendor


def get_cpu_frequency_range() -> Tuple[Optional[float], Optional[float]]:
    """Retrieve minimum and maximum CPU frequency in MHz if available."""
    summary = get_system_summary()
    return summary.min_freq_mhz, summary.max_freq_mhz


def get_process_affinity() -> List[int]:
    """Retrieve current process CPU affinity mask."""
    provider = get_hardware_provider()
    return provider.get_process_affinity()


def get_ram_info() -> RAMInfo:
    """Retrieve current system RAM memory info."""
    provider = get_hardware_provider()
    return provider.get_ram_info()


def get_top_processes(limit: int = 10) -> List[ProcessInfo]:
    """Retrieve top running processes by CPU usage."""
    provider = get_hardware_provider()
    return provider.get_top_processes(limit=limit)


def get_system_summary(force_refresh: bool = False) -> SystemSummary:
    """Retrieve consolidated hardware and system information.

    Args:
        force_refresh: If True, bypass cache and re-probe system.

    Returns:
        SystemSummary dataclass instance.
    """
    global _CACHED_SUMMARY
    if _CACHED_SUMMARY is not None and not force_refresh:
        return _CACHED_SUMMARY

    provider = get_hardware_provider(force_new=force_refresh)
    info = provider.detect_hardware()

    summary = SystemSummary(
        cpu_model=info.cpu_model,
        cpu_vendor=info.cpu_vendor,
        architecture=info.architecture,
        os_name=info.os_name,
        os_kernel=info.os_kernel,
        physical_cores=info.physical_cores,
        logical_cores=info.logical_cores,
        available_cpus=info.available_cpus,
        current_affinity=info.current_affinity,
        topology=info.topology or CPUTopology(),
        min_freq_mhz=info.min_freq_mhz,
        max_freq_mhz=info.max_freq_mhz,
        detection_status=info.detection_status,
        platform_type=info.platform_type,
    )

    _CACHED_SUMMARY = summary
    return summary
