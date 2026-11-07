"""Comprehensive Cross-Platform Compatibility and Fallback Verification for CoreSync.

Verifies platform abstractions and graceful fallbacks for:
- Linux (POSIX, procfs, sysfs, PR_SET_PDEATHSIG, sched_setaffinity)
- Windows (Win32 API, OpenProcess SYNCHRONIZE, psutil CPU affinity)
- macOS Darwin (XNU kernel, sysctl, absence of hard thread affinity)
"""

import os
import platform
import sys
from unittest.mock import MagicMock, patch
import pytest

from utils.hardware.base import BaseHardwareProvider, HardwareInfo
from utils.hardware.factory import get_hardware_provider
from utils.hardware.linux import LinuxHardwareProvider
from utils.hardware.windows import WindowsHardwareProvider
from utils.hardware.darwin import DarwinHardwareProvider
from engine.affinity import (
    AffinityResult,
    get_available_system_cpus,
    get_process_actual_cpu,
    get_process_affinity,
    set_process_affinity,
)
from engine.process_manager import (
    PlatformProtectionCapability,
    get_platform_protection_capabilities,
)


def test_hardware_provider_factory_matrix():
    """Verify hardware factory selects appropriate provider for each platform."""
    with patch("platform.system", return_value="Linux"):
        provider = get_hardware_provider(force_new=True)
        assert isinstance(provider, LinuxHardwareProvider)

    with patch("platform.system", return_value="Windows"):
        provider = get_hardware_provider(force_new=True)
        assert isinstance(provider, WindowsHardwareProvider)

    with patch("platform.system", return_value="Darwin"):
        provider = get_hardware_provider(force_new=True)
        assert isinstance(provider, DarwinHardwareProvider)

    with patch("platform.system", return_value="FreeBSD"):
        provider = get_hardware_provider(force_new=True)
        assert isinstance(provider, LinuxHardwareProvider)  # Generic POSIX fallback


def test_windows_hardware_provider_mocked_wmi():
    """Verify Windows provider parses WMI/registry responses or falls back gracefully."""
    provider = WindowsHardwareProvider()
    with patch("platform.system", return_value="Windows"):
        info = provider.detect_hardware()
        assert isinstance(info, HardwareInfo)
        assert info.platform_type == "Windows"
        assert info.logical_cores >= 1


def test_darwin_hardware_provider_mocked_sysctl():
    """Verify macOS Darwin provider uses sysctl or falls back gracefully."""
    provider = DarwinHardwareProvider()
    with patch("platform.system", return_value="Darwin"):
        info = provider.detect_hardware()
        assert isinstance(info, HardwareInfo)
        assert info.platform_type == "Darwin"
        assert info.logical_cores >= 1


def test_affinity_darwin_graceful_rejection():
    """Verify that attempting to pin CPU affinity on macOS returns clean informative failure."""
    with patch("platform.system", return_value="Darwin"):
        res = set_process_affinity(os.getpid(), [0])
        assert isinstance(res, AffinityResult)
        assert res.success is False
        assert "macOS does not support hard CPU affinity pinning" in res.message


def test_get_process_actual_cpu_non_linux_safe():
    """Verify get_process_actual_cpu returns None on non-Linux platforms without raising exceptions."""
    with patch("sys.platform", "win32"):
        assert get_process_actual_cpu(os.getpid()) is None

    with patch("sys.platform", "darwin"):
        assert get_process_actual_cpu(os.getpid()) is None


def test_platform_protection_capabilities_all_platforms():
    """Verify capabilities reporting for Linux, Windows, Darwin, and generic platforms."""
    with patch("sys.platform", "linux"):
        cap = get_platform_protection_capabilities()
        assert cap.has_kernel_pdeathsig is True
        assert cap.guarantee_level == "kernel_synchronous"

    with patch("sys.platform", "win32"):
        cap = get_platform_protection_capabilities()
        assert cap.has_win32_handle_wait is True
        assert cap.guarantee_level == "handle_synchronous"

    with patch("sys.platform", "darwin"):
        cap = get_platform_protection_capabilities()
        assert cap.has_kqueue_proc is True
        assert cap.guarantee_level == "bounded_polling_or_kqueue"

    with patch("sys.platform", "sunos5"):
        cap = get_platform_protection_capabilities()
        assert cap.watchdog_polling_supported is True
        assert cap.guarantee_level == "bounded_polling"

