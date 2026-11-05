"""Integration and unit tests for asynchronous CPU monitoring service and GUI consumers."""

import time
import pytest
from PySide6.QtCore import QCoreApplication

from monitoring.cpu_monitor import CPUMetricsSnapshot, CPUMonitorService
from gui.dashboard import DashboardPage
from gui.core_monitor import CoreMonitorPage
from gui.main_window import MainWindow


def test_cpu_monitor_service_lifecycle(qapp):
    """Verify that CPUMonitorService starts and stops cleanly without orphan threads."""
    received_snapshots = []

    service = CPUMonitorService(refresh_interval_ms=200)

    def _on_metrics(snapshot: CPUMetricsSnapshot):
        received_snapshots.append(snapshot)

    service.metrics_updated.connect(_on_metrics)

    # Start service
    service.start()
    assert service.is_running() is True

    # Process events to allow timer to fire
    start_time = time.time()
    while len(received_snapshots) < 2 and time.time() - start_time < 3.0:
        QCoreApplication.processEvents()
        time.sleep(0.05)

    assert len(received_snapshots) >= 1
    snap = received_snapshots[0]
    assert isinstance(snap, CPUMetricsSnapshot)
    assert 0.0 <= snap.overall_percent <= 100.0
    assert len(snap.per_cpu_percent) >= 1
    assert all(0.0 <= p <= 100.0 for p in snap.per_cpu_percent)

    # Stop service cleanly
    service.stop(timeout_ms=1000)
    assert service.is_running() is False


def test_dashboard_metrics_update(qapp):
    """Verify that Dashboard updates its overall CPU load widget upon signal delivery."""
    page = DashboardPage()
    dummy_snapshot = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=42.6,
        per_cpu_percent=[40.0, 45.0],
    )
    page.update_metrics(dummy_snapshot)

    assert page.card_cpu_load.value_label.text() == "42.6 %"
    if page.card_cpu_load.progress_bar:
        assert page.card_cpu_load.progress_bar.value() == 43


def test_core_monitor_metrics_update(qapp):
    """Verify that CoreMonitor updates individual core widgets upon signal delivery."""
    page = CoreMonitorPage()
    cpu_count = len(page.core_widgets)

    dummy_per_cpu = [10.0 + i for i in range(cpu_count)]
    dummy_freqs = [2000.0 + (i * 50) for i in range(cpu_count)]

    dummy_snapshot = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=15.0,
        per_cpu_percent=dummy_per_cpu,
        per_cpu_freq_mhz=dummy_freqs,
    )
    page.update_metrics(dummy_snapshot)

    # Verify first core widget updated
    if 0 in page.core_widgets:
        w0 = page.core_widgets[0]
        assert w0.percent_lbl.text() == "10.0%"
        assert w0.progress_bar.value() == 10
        assert "2000 MHz" in w0.freq_lbl.text()


def test_main_window_monitoring_integration(qapp):
    """Verify MainWindow integrates and cleanly shuts down the CPU monitor."""
    window = MainWindow()
    assert hasattr(window, "cpu_monitor")
    assert window.cpu_monitor.is_running() is True

    # Process events to confirm no crashes or lockups
    for _ in range(5):
        QCoreApplication.processEvents()
        time.sleep(0.02)

    # Close window and verify clean monitoring shutdown
    window.close()
    assert window.cpu_monitor.is_running() is False
