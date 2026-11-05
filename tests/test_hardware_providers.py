"""Tests for cross-platform hardware providers and factory abstraction."""

import platform
import pytest

from utils.hardware.base import BaseHardwareProvider, HardwareInfo, RAMInfo, ProcessInfo
from utils.hardware.factory import get_hardware_provider
from utils.hardware.linux import LinuxHardwareProvider
from utils.hardware.windows import WindowsHardwareProvider
from utils.hardware.darwin import DarwinHardwareProvider


def test_hardware_factory_returns_provider():
    """Verify factory returns appropriate provider instance."""
    provider = get_hardware_provider()
    assert isinstance(provider, BaseHardwareProvider)

    current_sys = platform.system()
    if current_sys == "Linux":
        assert isinstance(provider, LinuxHardwareProvider)
    elif current_sys == "Windows":
        assert isinstance(provider, WindowsHardwareProvider)
    elif current_sys == "Darwin":
        assert isinstance(provider, DarwinHardwareProvider)


def test_linux_hardware_provider_detection():
    """Verify Linux hardware provider detects genuine host information without crash."""
    provider = LinuxHardwareProvider()
    info = provider.detect_hardware()

    assert isinstance(info, HardwareInfo)
    assert len(info.cpu_model) > 0
    assert info.physical_cores >= 1
    assert info.logical_cores >= 1
    assert info.logical_cores >= info.physical_cores
    assert len(info.current_affinity) >= 1
    assert "Verified" in info.detection_status or "sysfs" in info.detection_status


def test_ram_info_detection():
    """Verify RAM memory probing returns valid numbers."""
    provider = get_hardware_provider()
    ram = provider.get_ram_info()

    assert isinstance(ram, RAMInfo)
    assert ram.total_gb > 0.0
    assert ram.used_gb >= 0.0
    assert 0.0 <= ram.percent <= 100.0


def test_top_processes_detection():
    """Verify top processes probing returns non-empty list of processes."""
    provider = get_hardware_provider()
    procs = provider.get_top_processes(limit=5)

    assert isinstance(procs, list)
    assert len(procs) > 0
    for p in procs:
        assert isinstance(p, ProcessInfo)
        assert p.pid >= 0
        assert len(p.name) > 0
        assert p.cpu_percent >= 0.0
        assert p.memory_rss_mb >= 0.0
        assert isinstance(p.is_coresync_worker, bool)


def test_windows_provider_graceful_fallback():
    """Verify Windows provider fallback functions safely even on non-Windows."""
    win_provider = WindowsHardwareProvider()
    info = win_provider.detect_hardware()
    assert isinstance(info, HardwareInfo)
    assert info.platform_type == "Windows"
    assert info.logical_cores >= 1


def test_darwin_provider_graceful_fallback():
    """Verify macOS Darwin provider fallback functions safely even on non-macOS."""
    mac_provider = DarwinHardwareProvider()
    info = mac_provider.detect_hardware()
    assert isinstance(info, HardwareInfo)
    assert info.platform_type == "Darwin"
    assert info.logical_cores >= 1
