"""Comprehensive Windows 10/11 Native Compatibility and Subsystem Verification.

Tests all Windows-specific code paths, abstractions, Win32 handle monitoring,
registry hardware detection, CPU affinity management, and fallback mechanisms.
"""

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
import psutil

from utils.cpu_topology import CoreType, CPUTopology
from utils.hardware.base import HardwareInfo, ProcessInfo, RAMInfo
from utils.hardware.windows import (
    WindowsHardwareProvider,
    _query_windows_registry,
    _query_wmic_cpu_name,
)
from engine.affinity import (
    AffinityResult,
    get_process_actual_cpu,
    get_process_affinity,
    set_process_affinity,
)
from engine.process_manager import (
    _setup_win32_parent_handle_watchdog,
    enable_parent_death_protection,
    ParentDeathProtectionResult,
)
from engine.analytics.history import BenchmarkHistoryManager


def test_windows_hardware_provider_registry_success():
    """Verify Windows hardware provider parses registry brand, vendor, and nominal frequency."""
    mock_winreg = MagicMock()
    mock_key = MagicMock()
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
    mock_winreg.HKEY_LOCAL_MACHINE = 0x80000002

    def mock_query_value(key, val_name):
        if val_name == "ProcessorNameString":
            return ("13th Gen Intel(R) Core(TM) i7-13650HX", 1)
        elif val_name == "VendorIdentifier":
            return ("GenuineIntel", 1)
        elif val_name == "~MHz":
            return (2600, 4)
        raise FileNotFoundError()

    mock_winreg.QueryValueEx.side_effect = mock_query_value

    with patch.dict(sys.modules, {"winreg": mock_winreg}):
        model, vendor, mhz = _query_windows_registry()
        assert model == "13th Gen Intel(R) Core(TM) i7-13650HX"
        assert vendor == "GenuineIntel"
        assert mhz == 2600.0

        provider = WindowsHardwareProvider()
        with patch("platform.release", return_value="11"), \
             patch("platform.version", return_value="10.0.22631"), \
             patch("platform.machine", return_value="AMD64"), \
             patch("psutil.cpu_count", side_effect=lambda logical=True: 16 if logical else 8), \
             patch("psutil.cpu_freq", return_value=None):

            info = provider.detect_hardware()
            assert info.platform_type == "Windows"
            assert "Intel" in info.cpu_model
            assert info.cpu_vendor == "GenuineIntel"
            assert info.logical_cores == 16
            assert info.physical_cores == 8
            assert info.max_freq_mhz == 2600.0
            assert "Windows 11" in info.os_name
            assert "Verified (Windows Registry / Win32 API)" in info.detection_status


def test_windows_hardware_provider_wmic_and_platform_fallback():
    """Verify fallback when winreg fails: WMIC query or platform.processor()."""
    # 1. winreg fails, WMIC succeeds
    with patch("utils.hardware.windows._query_windows_registry", return_value=(None, None, None)):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Name\nAMD Ryzen 9 7950X 16-Core Processor\n"

        with patch("subprocess.run", return_value=mock_proc):
            wmic_name = _query_wmic_cpu_name()
            assert wmic_name == "AMD Ryzen 9 7950X 16-Core Processor"

            provider = WindowsHardwareProvider()
            with patch("platform.processor", return_value="AMD64 Family 25 Model 97 Stepping 2"), \
                 patch("platform.release", return_value="10"), \
                 patch("platform.version", return_value="10.0.19045"):
                info = provider.detect_hardware()
                assert "AMD Ryzen" in info.cpu_model
                assert info.cpu_vendor == "AuthenticAMD"
                assert "Windows 10" in info.os_name

    # 2. Both winreg and WMIC fail: fallback to platform.processor()
    with patch("utils.hardware.windows._query_windows_registry", return_value=(None, None, None)), \
         patch("utils.hardware.windows._query_wmic_cpu_name", return_value=None), \
         patch("platform.processor", return_value="Intel64 Family 6 Model 158 Stepping 10"):
        provider = WindowsHardwareProvider()
        info = provider.detect_hardware()
        assert "Intel64" in info.cpu_model
        assert info.cpu_vendor == "GenuineIntel"


def test_windows_hardware_provider_ram_and_process_tracking():
    """Verify RAM retrieval and worker process identification under Windows."""
    provider = WindowsHardwareProvider()

    # RAM test
    mock_vm = MagicMock(total=16 * (1024 ** 3), available=8 * (1024 ** 3), used=8 * (1024 ** 3), percent=50.0)
    with patch("psutil.virtual_memory", return_value=mock_vm):
        ram = provider.get_ram_info()
        assert isinstance(ram, RAMInfo)
        assert ram.total_gb == pytest.approx(16.0)
        assert ram.percent_used == 50.0

    # Process test
    mock_p1 = MagicMock()
    mock_p1.info = {
        "pid": 5001,
        "name": "python.exe",
        "cpu_percent": 15.5,
        "memory_percent": 2.1,
        "memory_info": MagicMock(rss=200 * 1024 * 1024),
        "status": "running",
        "cmdline": ["python.exe", "-c", "from engine.worker import dummy_sleep_worker", "CoreSync-DP-Worker-0"],
    }
    mock_p2 = MagicMock()
    mock_p2.info = {
        "pid": 5002,
        "name": "explorer.exe",
        "cpu_percent": 1.2,
        "memory_percent": 3.0,
        "memory_info": MagicMock(rss=300 * 1024 * 1024),
        "status": "running",
        "cmdline": ["C:\\Windows\\explorer.exe"],
    }

    with patch("psutil.process_iter", return_value=[mock_p1, mock_p2]):
        procs = provider.get_top_processes(limit=10)
        assert len(procs) == 2
        p1 = next(p for p in procs if p.pid == 5001)
        p2 = next(p for p in procs if p.pid == 5002)
        assert p1.is_coresync_worker is True
        assert p2.is_coresync_worker is False


def test_windows_cpu_affinity_assignment_and_error_handling():
    """Verify CPU affinity setting under Windows via psutil with exception handling."""
    with patch("platform.system", return_value="Windows"):
        # 1. Success case
        mock_proc = MagicMock()
        mock_proc.cpu_affinity.return_value = None

        with patch("psutil.Process", return_value=mock_proc), \
             patch("engine.affinity.get_process_affinity", return_value=[0, 1]):
            res = set_process_affinity(1234, [0, 1])
            assert res.success is True
            assert res.applied_cpus == [0, 1]
            mock_proc.cpu_affinity.assert_called_with([0, 1])

        # 2. Access Denied on Windows
        mock_proc_denied = MagicMock()
        mock_proc_denied.cpu_affinity.side_effect = psutil.AccessDenied(pid=1234)
        with patch("psutil.Process", return_value=mock_proc_denied), \
             patch("engine.affinity.get_process_affinity", return_value=[0, 1, 2, 3]):
            res = set_process_affinity(1234, [0])
            assert res.success is False
            assert "Access denied" in res.message

        # 3. Invalid CPU IDs out of range
        with patch("psutil.cpu_count", return_value=8):
            res = set_process_affinity(1234, [0, 99])
            assert res.success is False
            assert "Invalid logical CPU IDs" in res.message


def test_windows_get_process_actual_cpu_via_win32_api():
    """Verify get_process_actual_cpu uses GetCurrentProcessorNumber on Windows."""
    mock_kernel32 = MagicMock()
    mock_kernel32.GetCurrentProcessorNumber.return_value = 5
    mock_windll = MagicMock(kernel32=mock_kernel32)

    with patch("sys.platform", "win32"), \
         patch("ctypes.windll", mock_windll, create=True):
        observed = get_process_actual_cpu(os.getpid())
        assert observed == 5


def test_windows_parent_death_handle_watchdog():
    """Verify Win32 waitable process handle watchdog initialization."""
    mock_kernel32 = MagicMock()
    mock_kernel32.OpenProcess.return_value = 0x12345678  # Mock handle
    mock_windll = MagicMock(kernel32=mock_kernel32)
    mock_exit = MagicMock()

    with patch.dict(sys.modules, {"ctypes": MagicMock(windll=mock_windll)}):
        success, err = _setup_win32_parent_handle_watchdog(9999, exit_callback=mock_exit)
        assert success is True
        assert err is None
        # Verify SYNCHRONIZE (0x00100000) was requested
        mock_kernel32.OpenProcess.assert_called_with(0x00100000, False, 9999)


def test_windows_parent_death_startup_race_dead_parent():
    """Verify that if parent died before child initialization on Windows, worker self-terminates."""
    mock_exit = MagicMock()
    with patch("sys.platform", "win32"), \
         patch("os.getppid", return_value=1234), \
         patch("psutil.pid_exists", return_value=False), \
         patch("os._exit", mock_exit):
        # Even though os.getppid() returns 1234 (stale Windows parent ID), pid_exists(1234) is False!
        enable_parent_death_protection(parent_pid=1234)
        mock_exit.assert_called_once_with(0)


def test_no_proc_or_sysfs_accessed_on_windows():
    """Ensure Windows hardware provider never touches /proc or /sys Linux paths."""
    provider = WindowsHardwareProvider()
    original_open = open

    def guarded_open(file, *args, **kwargs):
        file_str = str(file)
        if file_str.startswith("/proc") or file_str.startswith("/sys"):
            raise AssertionError(f"Windows provider illegally attempted to open Linux path: {file_str}")
        return original_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=guarded_open), \
         patch("psutil.cpu_count", side_effect=lambda logical=True: 8 if logical else 4), \
         patch("psutil.cpu_freq", return_value=None), \
         patch("utils.hardware.windows._query_windows_registry", return_value=("Intel Core i7", "GenuineIntel", 2500.0)):
        info = provider.detect_hardware()
        assert info.platform_type == "Windows"


def test_benchmark_history_tempdir_fallback_cross_platform():
    """Verify BenchmarkHistoryManager uses tempfile.gettempdir() rather than hardcoded /tmp."""
    with patch.dict(os.environ, {}, clear=True), \
         patch("engine.analytics.history.DEFAULT_BENCHMARK_DIR", Path("/nonexistent/dir")):
        mgr = BenchmarkHistoryManager()
        # Storage dir must exist and must not be a hardcoded /tmp path on Windows
        assert mgr.storage_dir.exists()
        expected_temp = Path(tempfile.gettempdir())
        # The storage directory should either be local cwd or tempdir
        assert expected_temp in mgr.storage_dir.parents or mgr.storage_dir.parent == expected_temp or ".coresync" in str(mgr.storage_dir)


def test_main_freeze_support_invoked():
    """Verify main.py calls multiprocessing.freeze_support()."""
    with patch("multiprocessing.freeze_support") as mock_freeze, \
         patch("multiprocessing.set_start_method"), \
         patch("sys.platform", "win32"), \
         patch("argparse.ArgumentParser.parse_args", return_value=MagicMock(test_startup=False)), \
         patch("PySide6.QtWidgets.QApplication"), \
         patch("gui.main_window.MainWindow") as mock_win:
        import main
        try:
            main.main()
        except Exception:
            pass
        mock_freeze.assert_called_once()


def test_settings_page_windows_topology_combo():
    """Verify SettingsPage displays Windows-specific topology options on Windows."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from gui.settings import SettingsPage
    with patch("sys.platform", "win32"):
        page = SettingsPage()
        items = [page.combo_topo.itemText(i) for i in range(page.combo_topo.count())]
        assert any("Windows" in item for item in items)
        assert not any("Linux sysfs" in item for item in items)
