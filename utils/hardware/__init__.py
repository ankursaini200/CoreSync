"""Cross-platform hardware detection package."""

from utils.hardware.base import (
    BaseHardwareProvider,
    HardwareInfo,
    RAMInfo,
    ProcessInfo,
)
from utils.hardware.factory import get_hardware_provider

__all__ = [
    "BaseHardwareProvider",
    "HardwareInfo",
    "RAMInfo",
    "ProcessInfo",
    "get_hardware_provider",
]

