"""Linux sysfs CPU topology parser and core architecture detector for CoreSync."""

from dataclasses import dataclass, field
from enum import Enum
import glob
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("CoreSync.CPUTopology")


class CoreType(Enum):
    """Core architecture classification."""
    PERFORMANCE = "Performance (P-Core)"
    EFFICIENCY = "Efficiency (E-Core)"
    UNKNOWN = "Standard / Unknown"


def parse_cpu_list(cpu_list_str: str) -> List[int]:
    """Parse standard Linux CPU list syntax (e.g., '0-3,8-11', '0,2,4', '12').

    Returns:
        Sorted list of unique logical CPU integer IDs.
    """
    if not cpu_list_str or not cpu_list_str.strip():
        return []

    cpus: Set[int] = set()
    cleaned = cpu_list_str.strip()

    for item in cleaned.split(","):
        part = item.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_str, end_str = part.split("-", 1)
                start, end = int(start_str), int(end_str)
                if start <= end:
                    cpus.update(range(start, end + 1))
            except ValueError:
                logger.warning(f"Malformed range in CPU list: '{part}'")
        else:
            try:
                cpus.add(int(part))
            except ValueError:
                logger.warning(f"Malformed CPU ID in CPU list: '{part}'")

    return sorted(cpus)


@dataclass
class LogicalCPU:
    """Represents a single addressable logical CPU thread."""
    cpu_id: int
    package_id: Optional[int] = None       # Physical CPU socket / package
    core_id: Optional[int] = None          # Physical core ID within package
    thread_siblings: List[int] = field(default_factory=list)  # Siblings sharing this physical core
    core_type: CoreType = CoreType.UNKNOWN # P-Core, E-Core, or Unknown
    max_freq_khz: Optional[int] = None     # Maximum frequency in kHz
    cur_freq_khz: Optional[int] = None     # Current frequency in kHz

    @property
    def is_smt(self) -> bool:
        """Return True if this logical CPU shares its physical core with siblings."""
        return len(self.thread_siblings) > 1

    @property
    def max_freq_mhz(self) -> Optional[float]:
        """Return maximum frequency converted to MHz."""
        return self.max_freq_khz / 1000.0 if self.max_freq_khz is not None else None

    @property
    def cur_freq_mhz(self) -> Optional[float]:
        """Return current frequency converted to MHz."""
        return self.cur_freq_khz / 1000.0 if self.cur_freq_khz is not None else None


@dataclass
class CPUTopology:
    """Complete system CPU hardware topology."""
    logical_cpus: Dict[int, LogicalCPU] = field(default_factory=dict)
    physical_core_count: int = 0
    logical_cpu_count: int = 0
    package_count: int = 0
    p_cores: List[int] = field(default_factory=list)
    e_cores: List[int] = field(default_factory=list)
    unknown_cores: List[int] = field(default_factory=list)
    is_hybrid: bool = False
    source: str = "sysfs"

    def get_core_ids(self) -> List[int]:
        """Return sorted list of logical CPU IDs."""
        return sorted(self.logical_cpus.keys())

    def get_physical_cores_map(self) -> Dict[Tuple[int, int], List[int]]:
        """Map (package_id, core_id) to list of logical CPU thread IDs."""
        mapping: Dict[Tuple[int, int], List[int]] = {}
        for cpu in self.logical_cpus.values():
            pkg = cpu.package_id if cpu.package_id is not None else 0
            cid = cpu.core_id if cpu.core_id is not None else cpu.cpu_id
            key = (pkg, cid)
            mapping.setdefault(key, []).append(cpu.cpu_id)
        return mapping


def _read_int_file(path: Path) -> Optional[int]:
    """Safely read a single integer from a sysfs file."""
    try:
        if path.is_file():
            content = path.read_text(encoding="utf-8").strip()
            return int(content)
    except (OSError, ValueError, PermissionError):
        pass
    return None


def _read_str_file(path: Path) -> Optional[str]:
    """Safely read string contents from a sysfs file."""
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except (OSError, PermissionError):
        pass
    return None


def detect_pmu_hybrid_cores(pmu_root: Path) -> Tuple[List[int], List[int]]:
    """Query Linux kernel PMU devices for authoritative Intel Hybrid core masks.

    On Linux 5.15+, hybrid architectures expose:
    - /sys/bus/event_source/devices/cpu_core/cpus (P-cores)
    - /sys/bus/event_source/devices/cpu_atom/cpus (E-cores)

    Returns:
        Tuple of (p_core_ids, e_core_ids). If either is missing, returns empty lists.
    """
    p_cores: List[int] = []
    e_cores: List[int] = []

    core_path = pmu_root / "cpu_core" / "cpus"
    atom_path = pmu_root / "cpu_atom" / "cpus"

    core_content = _read_str_file(core_path)
    atom_content = _read_str_file(atom_path)

    if core_content:
        p_cores = parse_cpu_list(core_content)
    if atom_content:
        e_cores = parse_cpu_list(atom_content)

    return p_cores, e_cores


def parse_sysfs_topology(
    sysfs_root: str = "/sys/devices/system/cpu",
    pmu_root: str = "/sys/bus/event_source/devices",
) -> CPUTopology:
    """Parse CPU hardware topology from the Linux sysfs tree.

    Args:
        sysfs_root: Base path to sysfs CPU directory (default '/sys/devices/system/cpu').
        pmu_root: Base path to sysfs PMU event source directory.

    Returns:
        CPUTopology instance populated with real hardware topology.
    """
    sysfs_path = Path(sysfs_root)
    pmu_path = Path(pmu_root)

    topology = CPUTopology()
    logical_cpus: Dict[int, LogicalCPU] = {}

    # Query PMU hybrid definitions (authoritative kernel interface)
    p_core_ids, e_core_ids = detect_pmu_hybrid_cores(pmu_path)
    p_core_set = set(p_core_ids)
    e_core_set = set(e_core_ids)

    # Locate all logical cpu directories matching 'cpu[0-9]+'
    cpu_dirs = []
    if sysfs_path.is_dir():
        for item in sysfs_path.iterdir():
            if item.is_dir() and item.name.startswith("cpu") and item.name[3:].isdigit():
                cpu_dirs.append(item)

    # Sort numerically by CPU ID
    cpu_dirs.sort(key=lambda p: int(p.name[3:]))

    unique_physical_cores: Set[Tuple[int, int]] = set()
    unique_packages: Set[int] = set()

    for cpu_dir in cpu_dirs:
        cpu_id = int(cpu_dir.name[3:])
        topo_dir = cpu_dir / "topology"
        cpufreq_dir = cpu_dir / "cpufreq"

        # 1. Physical package ID
        package_id = _read_int_file(topo_dir / "physical_package_id")
        if package_id is not None:
            unique_packages.add(package_id)

        # 2. Physical core ID
        core_id = _read_int_file(topo_dir / "core_id")
        if core_id is not None and package_id is not None:
            unique_physical_cores.add((package_id, core_id))
        elif core_id is not None:
            unique_physical_cores.add((0, core_id))

        # 3. Thread siblings (SMT)
        siblings_str = _read_str_file(topo_dir / "thread_siblings_list")
        if siblings_str:
            siblings = parse_cpu_list(siblings_str)
        else:
            siblings = [cpu_id]

        # 4. CPU Frequencies
        max_freq = _read_int_file(cpufreq_dir / "cpuinfo_max_freq")
        cur_freq = _read_int_file(cpufreq_dir / "scaling_cur_freq")

        # 5. Core Type Classification (Strictly Authoritative)
        if cpu_id in p_core_set:
            core_type = CoreType.PERFORMANCE
        elif cpu_id in e_core_set:
            core_type = CoreType.EFFICIENCY
        else:
            core_type = CoreType.UNKNOWN

        logical_cpus[cpu_id] = LogicalCPU(
            cpu_id=cpu_id,
            package_id=package_id,
            core_id=core_id,
            thread_siblings=siblings,
            core_type=core_type,
            max_freq_khz=max_freq,
            cur_freq_khz=cur_freq,
        )

    topology.logical_cpus = logical_cpus
    topology.logical_cpu_count = len(logical_cpus)
    topology.physical_core_count = len(unique_physical_cores) if unique_physical_cores else len(logical_cpus)
    topology.package_count = len(unique_packages) if unique_packages else (1 if logical_cpus else 0)

    # Classify core groupings
    for cid, cpu in logical_cpus.items():
        if cpu.core_type == CoreType.PERFORMANCE:
            topology.p_cores.append(cid)
        elif cpu.core_type == CoreType.EFFICIENCY:
            topology.e_cores.append(cid)
        else:
            topology.unknown_cores.append(cid)

    # Hybrid flag is True ONLY when both P and E cores are reliably identified
    topology.is_hybrid = bool(topology.p_cores and topology.e_cores)
    topology.source = "sysfs"

    return topology

