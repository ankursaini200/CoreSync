"""Asynchronous CPU utilization and hardware metrics monitoring service for CoreSync."""

from dataclasses import dataclass, field
import logging
import os
import time
from typing import List, Optional

import psutil
from PySide6.QtCore import QMutex, QObject, QThread, QTimer, Signal, Slot

logger = logging.getLogger("CoreSync.CPUMonitor")


@dataclass
class CPUMetricsSnapshot:
    """Immutable snapshot of live system and per-core CPU metrics."""
    timestamp: float
    overall_percent: float
    per_cpu_percent: List[float]
    per_cpu_freq_mhz: Optional[List[float]] = None
    process_affinity: List[int] = field(default_factory=list)


class CPUMonitorWorker(QObject):
    """Worker running in a dedicated QThread to sample CPU metrics without blocking the UI."""

    metrics_updated = Signal(CPUMetricsSnapshot)
    error_occurred = Signal(str)
    sampling_stopped = Signal()

    def __init__(self, interval_ms: int = 1000):
        super().__init__()
        self._interval_ms = interval_ms
        self._timer: Optional[QTimer] = None
        self._is_running = False
        self._logical_count = psutil.cpu_count(logical=True) or 1
        self._mutex = QMutex()

        # Prime psutil first call so subsequent calls return non-blocking delta percentages
        try:
            psutil.cpu_percent(interval=None, percpu=True)
            psutil.cpu_percent(interval=None, percpu=False)
        except Exception as e:
            logger.debug(f"Initial psutil priming error: {e}")

    @Slot()
    def start_sampling(self) -> None:
        """Start the periodic sampling timer on the worker thread."""
        self._mutex.lock()
        try:
            if self._is_running:
                return
            self._is_running = True

            self._timer = QTimer()
            self._timer.setInterval(self._interval_ms)
            self._timer.timeout.connect(self._sample_metrics)
            self._timer.start()
            logger.debug(f"CPU monitoring timer started ({self._interval_ms}ms interval)")
        finally:
            self._mutex.unlock()

        # Emit an immediate sample
        self._sample_metrics()

    @Slot()
    def stop_sampling(self) -> None:
        """Stop the periodic sampling timer cleanly."""
        self._mutex.lock()
        try:
            self._is_running = False
            if self._timer is not None:
                if self._timer.isActive():
                    self._timer.stop()
                self._timer.deleteLater()
                self._timer = None
            logger.debug("CPU monitoring timer stopped")
        finally:
            self._mutex.unlock()

        self.sampling_stopped.emit()

    @Slot(int)
    def set_interval(self, interval_ms: int) -> None:
        """Update sampling refresh interval in milliseconds."""
        self._mutex.lock()
        try:
            self._interval_ms = max(200, min(interval_ms, 10000))
            if self._timer and self._timer.isActive():
                self._timer.setInterval(self._interval_ms)
        finally:
            self._mutex.unlock()

    @Slot()
    def _sample_metrics(self) -> None:
        """Query psutil metrics and emit snapshot signal."""
        if not self._is_running:
            return

        try:
            now = time.time()
            per_cpu = psutil.cpu_percent(interval=None, percpu=True)
            overall = psutil.cpu_percent(interval=None, percpu=False)

            # Query frequencies if available
            freq_list: Optional[List[float]] = None
            try:
                freqs = psutil.cpu_freq(percpu=True)
                if freqs:
                    freq_list = [f.current for f in freqs if f]
            except Exception:
                pass

            # Query current affinity
            affinity: List[int] = []
            try:
                proc = psutil.Process(os.getpid())
                if hasattr(proc, "cpu_affinity"):
                    affinity = proc.cpu_affinity()
            except Exception:
                pass

            snapshot = CPUMetricsSnapshot(
                timestamp=now,
                overall_percent=overall,
                per_cpu_percent=per_cpu,
                per_cpu_freq_mhz=freq_list,
                process_affinity=sorted(affinity) if affinity else list(range(len(per_cpu))),
            )
            self.metrics_updated.emit(snapshot)

        except Exception as e:
            logger.error(f"Error sampling CPU metrics: {e}")
            self.error_occurred.emit(str(e))


class CPUMonitorService(QObject):
    """Thread-safe coordinator managing the QThread lifecycle and worker instance."""

    metrics_updated = Signal(CPUMetricsSnapshot)
    error_occurred = Signal(str)
    _stop_worker = Signal()

    def __init__(self, refresh_interval_ms: int = 1000, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._refresh_interval_ms = refresh_interval_ms

        self._thread = QThread()
        self._worker = CPUMonitorWorker(interval_ms=self._refresh_interval_ms)
        self._worker.moveToThread(self._thread)

        # Connect internal worker signals to service public signals
        self._worker.metrics_updated.connect(self.metrics_updated)
        self._worker.error_occurred.connect(self.error_occurred)

        # Connect thread-safe stop signal
        self._stop_worker.connect(self._worker.stop_sampling)

        # Thread lifecycle
        self._thread.started.connect(self._worker.start_sampling)
        self._worker.sampling_stopped.connect(self._thread.quit)

    def start(self) -> None:
        """Start the background monitoring thread."""
        if not self._thread.isRunning():
            self._thread.start()
            logger.info("CPUMonitorService thread started")

    def stop(self, timeout_ms: int = 1000) -> None:
        """Request clean worker stop and wait for QThread to terminate."""
        if self._thread.isRunning():
            self._stop_worker.emit()
            self._thread.quit()
            if not self._thread.wait(timeout_ms):
                logger.warning("CPUMonitorService thread did not terminate cleanly; terminating...")
                self._thread.terminate()
                self._thread.wait(500)
            logger.info("CPUMonitorService thread stopped")

    def set_refresh_interval(self, interval_ms: int) -> None:
        """Change refresh interval dynamically."""
        self._refresh_interval_ms = interval_ms
        self._worker.set_interval(interval_ms)

    def is_running(self) -> bool:
        """Return True if background thread is active."""
        return self._thread.isRunning()
