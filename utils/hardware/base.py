"""Platform-independent hardware detection interface and data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from utils.cpu_topology import CPUTopology


@dataclass
class RAMInfo:
    """System physical memory metrics."""
    total_bytes: int = 0
    available_bytes: int = 0
    used_bytes: int = 0
    percent_used: float = 0.0

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024 ** 3)

    @property
    def available_gb(self) -> float:
        return self.available_bytes / (1024 ** 3)

    @property
    def used_gb(self) -> float:
        return self.used_bytes / (1024 ** 3)

    @property
    def percent(self) -> float:
        return self.percent_used


@dataclass
class ProcessInfo:
    """Operating system process inspection data."""
    pid: int
    name: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_rss_mb: float = 0.0
    status: str = "running"
    is_coresync_worker: bool = False


@dataclass
class HardwareInfo:
    """Consolidated platform-independent hardware specification."""
    cpu_model: str = "Unknown CPU"
    cpu_vendor: str = "Unknown Vendor"
    architecture: str = "x86_64"
    os_name: str = "Unknown OS"
    os_kernel: str = "Unknown Kernel"
    physical_cores: int = 1
    logical_cores: int = 1
    available_cpus: int = 1
    current_affinity: List[int] = field(default_factory=list)
    topology: Optional[CPUTopology] = None
    min_freq_mhz: Optional[float] = None
    max_freq_mhz: Optional[float] = None
    detection_status: str = "Standard"
    platform_type: str = "Generic"


class BaseHardwareProvider(ABC):
    """Abstract base class defining the hardware detection interface across OS platforms."""

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return platform identifier (e.g., 'Linux', 'Windows', 'Darwin')."""
        pass

    @abstractmethod
    def detect_hardware(self) -> HardwareInfo:
        """Probe and return complete hardware information."""
        pass

    @abstractmethod
    def get_ram_info(self) -> RAMInfo:
        """Retrieve live RAM memory usage."""
        pass

    @abstractmethod
    def get_top_processes(self, limit: int = 10) -> List[ProcessInfo]:
        """Retrieve top running operating system processes by CPU usage."""
        pass

    @abstractmethod
    def get_process_affinity(self) -> List[int]:
        """Retrieve current process CPU affinity."""
        pass
