"""Windows platform hardware detection implementation using Windows Registry, APIs, and psutil."""

import logging
import os
import platform
import subprocess
from typing import List, Optional, Tuple

import psutil

from utils.cpu_topology import CoreType, CPUTopology, LogicalCPU
from utils.hardware.base import BaseHardwareProvider, HardwareInfo, ProcessInfo, RAMInfo

logger = logging.getLogger("CoreSync.Hardware.Windows")


def _query_windows_registry() -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """Query Windows Registry for CPU brand string, vendor identifier, and nominal clock speed in MHz.

    Reads from HKEY_LOCAL_MACHINE\\HARDWARE\\DESCRIPTION\\System\\CentralProcessor\\0:
      - ProcessorNameString: e.g. "13th Gen Intel(R) Core(TM) i7-13650HX"
      - VendorIdentifier: e.g. "GenuineIntel" or "AuthenticAMD"
      - ~MHz: DWORD integer nominal frequency
    """
    try:
        import winreg  # Only available on Windows or mock environments

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            model_val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            vendor_val, _ = winreg.QueryValueEx(key, "VendorIdentifier")
            mhz_val, _ = winreg.QueryValueEx(key, "~MHz")
            return (
                str(model_val).strip() if model_val else None,
                str(vendor_val).strip() if vendor_val else None,
                float(mhz_val) if mhz_val else None,
            )
    except Exception as e:
        logger.debug(f"winreg hardware query failed: {e}")
        return None, None, None


def _query_wmic_cpu_name() -> Optional[str]:
    """Fallback query for CPU name via WMIC or PowerShell if winreg is unavailable."""
    try:
        res = subprocess.run(
            ["wmic", "cpu", "get", "name"],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        if res.returncode == 0:
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
    except Exception:
        pass
    return None


class WindowsHardwareProvider(BaseHardwareProvider):
    """Hardware provider for Windows environments using Windows Registry, Win32 APIs, and psutil."""

    def get_platform_name(self) -> str:
        return "Windows"

    def detect_hardware(self) -> HardwareInfo:
        # 1. Probe CPU Brand and Vendor
        reg_model, reg_vendor, reg_mhz = _query_windows_registry()

        cpu_model = reg_model or _query_wmic_cpu_name() or platform.processor() or "Windows Processor"

        # Vendor classification
        if reg_vendor:
            cpu_vendor = reg_vendor
        elif "Intel" in cpu_model:
            cpu_vendor = "GenuineIntel"
        elif "AMD" in cpu_model:
            cpu_vendor = "AuthenticAMD"
        else:
            cpu_vendor = "Unknown Vendor"

        # 2. Logical and Physical Core Counts
        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False) or logical_cores

        # 3. Topology Construction
        threads_per_core = max(1, logical_cores // physical_cores) if physical_cores > 0 else 1
        logical_cpus = {}
        for i in range(logical_cores):
            core_id = min(i // threads_per_core, physical_cores - 1) if physical_cores > 0 else i
            siblings = [
                c for c in range(logical_cores)
                if (min(c // threads_per_core, physical_cores - 1) if physical_cores > 0 else c) == core_id
            ]
            logical_cpus[i] = LogicalCPU(
                cpu_id=i,
                package_id=0,
                core_id=core_id,
                thread_siblings=siblings,
                core_type=CoreType.UNKNOWN,
            )

        topology = CPUTopology(
            logical_cpus=logical_cpus,
            physical_core_count=physical_cores,
            logical_cpu_count=logical_cores,
            package_count=1,
            source="windows_registry_and_psutil" if reg_model else "windows_psutil",
        )

        affinity = self.get_process_affinity()

        # 4. CPU Frequencies
        min_f, max_f = None, None
        try:
            freq = psutil.cpu_freq()
            if freq:
                min_f = freq.min if freq.min and freq.min > 0 else None
                max_f = freq.max if freq.max and freq.max > 0 else None
        except Exception:
            pass

        if max_f is None and reg_mhz and reg_mhz > 0:
            max_f = reg_mhz
        if min_f is None and reg_mhz and reg_mhz > 0:
            min_f = reg_mhz

        # 5. OS and Architecture
        os_release = platform.release()
        os_version = platform.version()
        os_name = f"Windows {os_release} (Build {os_version})"
        os_kernel = f"Windows NT {os_version}"
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
            detection_status="Verified (Windows Registry / Win32 API)" if reg_model else "Verified (Windows API)",
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
        except Exception as e:
            logger.warning(f"Failed to query Windows RAM info: {e}")
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
                is_worker = (
                    any(sig in name or sig in cmdline for sig in ("CoreSync-DP-Worker", "CoreSync-Task-", "CoreSync-Stress", "coresync_worker"))
                    and pid != my_pid
                )

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

        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        return processes[:limit]

    def get_process_affinity(self) -> List[int]:
        try:
            proc = psutil.Process(os.getpid())
            if hasattr(proc, "cpu_affinity"):
                aff = proc.cpu_affinity()
                if aff:
                    return sorted(list(aff))
        except Exception:
            pass

        logical = psutil.cpu_count(logical=True) or 1
        return list(range(logical))
