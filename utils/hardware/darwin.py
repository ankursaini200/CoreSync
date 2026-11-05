"""macOS (Darwin) platform hardware detection implementation using sysctl and psutil."""

import logging
import os
import platform
import subprocess
from typing import List

import psutil

from utils.cpu_topology import CoreType, CPUTopology, LogicalCPU
from utils.hardware.base import BaseHardwareProvider, HardwareInfo, ProcessInfo, RAMInfo

logger = logging.getLogger("CoreSync.Hardware.Darwin")


class DarwinHardwareProvider(BaseHardwareProvider):
    """Hardware provider for macOS / Darwin environments."""

    def get_platform_name(self) -> str:
        return "Darwin"

    def detect_hardware(self) -> HardwareInfo:
        cpu_model = self._get_mac_cpu_brand() or platform.processor() or "Apple Silicon / Intel Mac"
        cpu_vendor = "Apple" if "Apple" in cpu_model else ("GenuineIntel" if "Intel" in cpu_model else "Unknown Vendor")

        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False) or logical_cores

        # Attempt to detect Apple Silicon performance / efficiency core counts via sysctl
        p_cores, e_cores = self._get_apple_silicon_core_counts()
        logical_cpus = {}

        for i in range(logical_cores):
            core_type = CoreType.UNKNOWN
            if p_cores > 0 and e_cores > 0:
                # On Apple Silicon M-series, P-cores typically precede E-cores
                if i < p_cores:
                    core_type = CoreType.PERFORMANCE
                elif i < (p_cores + e_cores):
                    core_type = CoreType.EFFICIENCY

            logical_cpus[i] = LogicalCPU(
                cpu_id=i,
                package_id=0,
                core_id=i,
                thread_siblings=[i],
                core_type=core_type,
            )

        is_hybrid = bool(p_cores > 0 and e_cores > 0)
        topology = CPUTopology(
            logical_cpus=logical_cpus,
            physical_core_count=physical_cores,
            logical_cpu_count=logical_cores,
            package_count=1,
            is_hybrid=is_hybrid,
            source="darwin_sysctl",
        )

        affinity = list(range(logical_cores))
        os_name = f"macOS {platform.mac_ver()[0]}"
        os_kernel = f"Darwin {platform.release()}"
        arch = platform.machine() or "arm64"

        return HardwareInfo(
            cpu_model=cpu_model,
            cpu_vendor=cpu_vendor,
            architecture=arch,
            os_name=os_name,
            os_kernel=os_kernel,
            physical_cores=physical_cores,
            logical_cores=logical_cores,
            available_cpus=len(affinity),
            current_affinity=affinity,
            topology=topology,
            detection_status="Verified (sysctl)",
            platform_type="Darwin",
        )

    def get_ram_info(self) -> RAMInfo:
        try:
            vm = psutil.virtual_memory()
            return RAMInfo(
                total_bytes=vm.total,
                available_bytes=vm.available,
                used_bytes=vm.used,
                percent_used=vm.percent,
            )
        except Exception:
            return RAMInfo()

    def get_top_processes(self, limit: int = 10) -> List[ProcessInfo]:
        processes: List[ProcessInfo] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status"]):
            try:
                info = proc.info
                processes.append(
                    ProcessInfo(
                        pid=info.get("pid") or 0,
                        name=info.get("name") or "Unknown",
                        cpu_percent=info.get("cpu_percent") or 0.0,
                        memory_percent=info.get("memory_percent") or 0.0,
                        memory_rss_mb=((info.get("memory_info").rss / (1024 * 1024)) if info.get("memory_info") else 0.0),
                        status=info.get("status") or "running",
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return processes[:limit]

    def get_process_affinity(self) -> List[int]:
        # macOS doesn't support thread/process affinity masks; all cores are available
        logical = psutil.cpu_count(logical=True) or 1
        return list(range(logical))

    def _get_mac_cpu_brand(self) -> Optional[str]:
        try:
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
            return out.strip()
        except Exception:
            return None

    def _get_apple_silicon_core_counts(self) -> tuple[int, int]:
        p_cores = 0
        e_cores = 0
        try:
            p_val = subprocess.check_output(["sysctl", "-n", "hw.perflevel0.logicalcpu"], text=True)
            p_cores = int(p_val.strip())
        except Exception:
            pass

        try:
            e_val = subprocess.check_output(["sysctl", "-n", "hw.perflevel1.logicalcpu"], text=True)
            e_cores = int(e_val.strip())
        except Exception:
            pass

        return p_cores, e_cores

