"""Linux platform hardware detection implementation using sysfs, /proc, and psutil."""

import logging
import os
import platform
from typing import List, Optional

import psutil

from utils.cpu_topology import parse_sysfs_topology
from utils.hardware.base import BaseHardwareProvider, HardwareInfo, ProcessInfo, RAMInfo

logger = logging.getLogger("CoreSync.Hardware.Linux")


class LinuxHardwareProvider(BaseHardwareProvider):
    """Hardware provider for Linux environments utilizing sysfs, /proc, and psutil."""

    def __init__(
        self,
        sysfs_root: str = "/sys/devices/system/cpu",
        pmu_root: str = "/sys/bus/event_source/devices",
    ):
        self._sysfs_root = sysfs_root
        self._pmu_root = pmu_root

    def get_platform_name(self) -> str:
        return "Linux"

    def detect_hardware(self) -> HardwareInfo:
        # 1. Parse sysfs topology & PMU hybrid cores
        try:
            topology = parse_sysfs_topology(
                sysfs_root=self._sysfs_root,
                pmu_root=self._pmu_root,
            )
        except Exception as e:
            logger.error(f"Error parsing Linux sysfs topology: {e}")
            from utils.cpu_topology import CPUTopology
            topology = CPUTopology(source="fallback")

        # 2. CPU Model & Vendor from /proc/cpuinfo
        cpu_model, cpu_vendor = self._get_cpu_model_vendor()

        # 3. Core Counts
        logical_cores = topology.logical_cpu_count or (psutil.cpu_count(logical=True) or 1)
        physical_cores = topology.physical_core_count or (psutil.cpu_count(logical=False) or logical_cores)

        # 4. Affinity & Available CPUs
        affinity = self.get_process_affinity()
        available_cpus = len(affinity)

        # 5. OS Name & Kernel Release
        os_name = self._get_linux_distro_name()
        os_kernel = f"Linux {platform.release()}"
        arch = platform.machine() or "x86_64"

        # 6. Frequency range
        min_f, max_f = None, None
        try:
            freq = psutil.cpu_freq()
            if freq:
                min_f = freq.min if freq.min and freq.min > 0 else None
                max_f = freq.max if freq.max and freq.max > 0 else None
        except Exception:
            pass

        if max_f is None and topology.logical_cpus:
            freqs = [c.max_freq_mhz for c in topology.logical_cpus.values() if c.max_freq_mhz is not None]
            if freqs:
                max_f = max(freqs)

        detection_status = "Verified (sysfs + PMU)" if topology.is_hybrid else "Verified (sysfs)"

        return HardwareInfo(
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
            min_freq_mhz=min_f,
            max_freq_mhz=max_f,
            detection_status=detection_status,
            platform_type="Linux",
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
        except Exception as e:
            logger.warning(f"Failed to query RAM info: {e}")
            return RAMInfo()

    def get_top_processes(self, limit: int = 10) -> List[ProcessInfo]:
        processes: List[ProcessInfo] = []
        my_pid = os.getpid()

        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status", "cmdline"]):
            try:
                info = proc.info
                pid = info.get("pid") or 0
                name = info.get("name") or "Unknown"
                cpu_p = info.get("cpu_percent") or 0.0
                mem_p = info.get("memory_percent") or 0.0
                mem_info = info.get("memory_info")
                rss_mb = (mem_info.rss / (1024 * 1024)) if mem_info else 0.0
                status = info.get("status") or "running"

                # Check if this process is a CoreSync worker
                cmdline = " ".join(info.get("cmdline") or [])
                is_worker = ("CoreSync" in cmdline or "coresync" in cmdline) and pid != my_pid

                processes.append(
                    ProcessInfo(
                        pid=pid,
                        name=name,
                        cpu_percent=cpu_p,
                        memory_percent=mem_p,
                        memory_rss_mb=rss_mb,
                        status=status,
                        is_coresync_worker=is_worker,
                    )
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU percent descending
        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return processes[:limit]

    def get_process_affinity(self) -> List[int]:
        try:
            proc = psutil.Process(os.getpid())
            if hasattr(proc, "cpu_affinity"):
                return sorted(proc.cpu_affinity())
        except Exception:
            pass

        try:
            if hasattr(os, "sched_getaffinity"):
                return sorted(os.sched_getaffinity(0))
        except Exception:
            pass

        logical = psutil.cpu_count(logical=True) or 1
        return list(range(logical))

    def _get_cpu_model_vendor(self) -> tuple[str, str]:
        model = "Unknown CPU"
        vendor = "Unknown Vendor"

        cpuinfo_path = "/proc/cpuinfo"
        if os.path.exists(cpuinfo_path):
            try:
                with open(cpuinfo_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if ":" in line:
                            k, v = [x.strip() for x in line.split(":", 1)]
                            if k in ("model name", "Hardware", "Processor") and model == "Unknown CPU":
                                model = v
                            elif k == "vendor_id" and vendor == "Unknown Vendor":
                                vendor = v
                            if model != "Unknown CPU" and vendor != "Unknown Vendor":
                                break
            except Exception:
                pass

        if model == "Unknown CPU":
            proc = platform.processor()
            if proc:
                model = proc

        if vendor == "Unknown Vendor":
            if "Intel" in model:
                vendor = "GenuineIntel"
            elif "AMD" in model:
                vendor = "AuthenticAMD"

        return model, vendor

    def _get_linux_distro_name(self) -> str:
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            return line.split("=", 1)[1].strip().strip('"')
            except Exception:
                pass
        return f"Linux ({platform.system()})"

