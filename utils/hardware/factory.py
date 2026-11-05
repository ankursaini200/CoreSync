"""Hardware Provider Factory detecting platform and instantiating appropriate provider."""

import platform
from typing import Optional

from utils.hardware.base import BaseHardwareProvider
from utils.hardware.linux import LinuxHardwareProvider
from utils.hardware.windows import WindowsHardwareProvider
from utils.hardware.darwin import DarwinHardwareProvider

_PROVIDER_INSTANCE: Optional[BaseHardwareProvider] = None


def get_hardware_provider(force_new: bool = False) -> BaseHardwareProvider:
    """Return platform-specific hardware provider instance.

    Auto-detects OS:
    - Linux -> LinuxHardwareProvider
    - Windows -> WindowsHardwareProvider
    - Darwin (macOS) -> DarwinHardwareProvider
    - Other -> LinuxHardwareProvider fallback
    """
    global _PROVIDER_INSTANCE
    if _PROVIDER_INSTANCE is not None and not force_new:
        return _PROVIDER_INSTANCE

    system = platform.system()
    if system == "Linux":
        provider = LinuxHardwareProvider()
    elif system == "Windows":
        provider = WindowsHardwareProvider()
    elif system == "Darwin":
        provider = DarwinHardwareProvider()
    else:
        # Generic fallback
        provider = LinuxHardwareProvider()

    _PROVIDER_INSTANCE = provider
    return provider

