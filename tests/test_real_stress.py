"""Unit and safety tests for Real CPU Stress Generator."""

import time
import psutil
import pytest

from engine.real_system.cpu_stress import (
    MAX_STRESS_DURATION_S,
    RealCPUStressGenerator,
    StressStatus,
)


def test_stress_safety_duration_clamping():
    """Verify that requests exceeding MAX_STRESS_DURATION_S are clamped to 30s."""
    generator = RealCPUStressGenerator()

    # Attempt to request 120 seconds
    started = generator.start_stress(worker_count=1, duration_s=120.0, intensity_pct=50.0)
    assert started is True

    status = generator.get_status()
    assert status.target_duration_s == MAX_STRESS_DURATION_S

    # Stop immediately
    generator.stop_stress()
    assert generator.is_running() is False


def test_stress_immediate_stop_and_zero_orphans():
    """Verify that stopping stress terminates all worker processes with zero orphans."""
    generator = RealCPUStressGenerator()
    started = generator.start_stress(worker_count=2, duration_s=10.0, intensity_pct=80.0)
    assert started is True

    status = generator.get_status()
    assert status.is_running is True
    assert status.workers_active == 2
    pids = list(status.worker_pids)
    assert len(pids) == 2

    # Verify processes exist in OS
    for pid in pids:
        assert psutil.pid_exists(pid)

    # Trigger immediate termination
    generator.stop_stress()

    # Wait brief moment for process reaping
    time.sleep(0.5)

    assert generator.is_running() is False
    # Verify no orphan processes remain
    for pid in pids:
        assert not psutil.pid_exists(pid)


def test_stress_auto_completion():
    """Verify that stress workload automatically completes when target duration elapses."""
    generator = RealCPUStressGenerator()
    started = generator.start_stress(worker_count=1, duration_s=1.0, intensity_pct=100.0)
    assert started is True

    # Sleep slightly past target duration (duration clamped to minimum 1.0s)
    time.sleep(1.4)

    status = generator.get_status()
    assert status.is_running is False
    assert status.workers_active == 0
