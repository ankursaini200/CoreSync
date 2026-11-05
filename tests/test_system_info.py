"""Unit tests for system information detection and consolidation."""

import os
import platform
import pytest

from utils.system_info import (
    get_cpu_frequency_range,
    get_cpu_model_and_vendor,
    get_process_affinity,
    get_system_summary,
    SystemSummary,
)


def test_cpu_model_and_vendor_detection():
    """Verify that CPU model and vendor are non-empty strings."""
    model, vendor = get_cpu_model_and_vendor()
    assert isinstance(model, str)
    assert len(model) > 0
    assert model != ""
    assert isinstance(vendor, str)
    assert len(vendor) > 0


def test_process_affinity():
    """Verify that current process affinity is a non-empty list of valid integer CPU IDs."""
    affinity = get_process_affinity()
    assert isinstance(affinity, list)
    assert len(affinity) >= 1
    assert all(isinstance(c, int) and c >= 0 for c in affinity)


def test_frequency_range():
    """Verify CPU frequency range returns numeric values or None gracefully."""
    min_f, max_f = get_cpu_frequency_range()
    if min_f is not None:
        assert isinstance(min_f, (int, float))
        assert min_f > 0
    if max_f is not None:
        assert isinstance(max_f, (int, float))
        assert max_f > 0


def test_get_system_summary_structure():
    """Verify that get_system_summary returns a complete SystemSummary instance."""
    summary = get_system_summary()
    assert isinstance(summary, SystemSummary)
    assert summary.physical_cores >= 1
    assert summary.logical_cores >= summary.physical_cores or summary.logical_cores >= 1
    assert summary.available_cpus >= 1
    assert isinstance(summary.current_affinity, list)
    assert len(summary.current_affinity) > 0
    assert summary.os_kernel.startswith("Linux") or len(summary.os_kernel) > 0
    assert len(summary.architecture) > 0
    assert summary.topology is not None

