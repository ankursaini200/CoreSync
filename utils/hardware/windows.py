"""Windows platform hardware detection implementation using psutil and native APIs."""

import logging
import os
import platform
from typing import List

import psutil

from utils.cpu_topology import CoreType, CPUTopology, LogicalCPU
from utils.hardware.base import BaseHardwareProvider, HardwareInfo, ProcessInfo, RAMInfo

logger = logging.getLogger("CoreSync.Hardware.Windows")


class WindowsHardwareProvider(BaseHardwareProvider):
    """Hardware provider for Windows environments using psutil and Windows APIs."""

    def get_platform_name(self) -> str:
        return "Windows"

    def detect_hardware(self) -> HardwareInfo:
        cpu_model = platform.processor() or "Windows Processor"
        cpu_vendor = "GenuineIntel" if "Intel" in cpu_model else ("AuthenticAMD" if "AMD" in cpu_model else "Unknown Vendor")

        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False) or logical_cores

        # Create basic topology
        logical_cpus = {}
        for i in range(logical_cores):
            logical_cpus[i] = LogicalCPU(
                cpu_id=i,
                package_id=0,
                core_id=i // 2 if logical_cores > physical_cores else i,
                thread_siblings=[i] if logical_cores == physical_cores else [i - (i % 2), i - (i % 2) + 1],
                core_type=CoreType.UNKNOWN,
            )

        topology = CPUTopology(
            logical_cpus=logical_cpus,
            physical_core_count=physical_cores,
            logical_cpu_count=logical_cores,
            package_count=1,
            source="windows_psutil",
        )

        affinity = self.get_process_affinity()
        min_f, max_f = None, None
        try:
            freq = psutil.cpu_freq()
            if freq:
                min_f = freq.min if freq.min and freq.min > 0 else None
                max_f = freq.max if freq.max and freq.max > 0 else None
        except Exception:
            pass

        os_name = f"Windows {platform.release()} ({platform.version()})"
        os_kernel = f"Windows NT {platform.version()}"
        arch = platform.machine() or "x86_64"

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
            min_freq_mhz=min_f,
            max_freq_mhz=max_f,
            detection_status="Verified (Windows API)",
            platform_type="Windows",
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
        my_pid = os.getpid()

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status"]):
            try:
                info = proc.info
                pid = info.get("pid") or 0
                name = info.get("name") or "Unknown"
                cpu_p = info.get("cpu_percent") or 0.0
                mem_p = info.get("memory_percent") or 0.0
                mem_info = info.get("memory_info")
                rss_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                status = info.get("status") or "running"

                processes.append(
                    ProcessInfo(
                        pid=pid,
                        name=name,
                        cpu_percent=cpu_p,
                        memory_percent=mem_p,
                        memory_rss_mb=rss_mb,
                        status=status,
                        is_coresync_worker=False,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return processes[:limit]

    def get_process_affinity(self) -> List[int]:
        try:
            proc = psutil.Process(os.getpid())
            if hasattr(proc, "cpu_affinity"):
                return sorted(proc.cpu_affinity())
        except Exception:
            pass

        logical = psutil.cpu_count(logical=True) or 1
        return list(range(logical))

