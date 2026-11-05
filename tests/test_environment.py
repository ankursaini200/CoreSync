"""Baseline environment, dependency, and skeleton sanity tests."""

import multiprocessing as mp
import os
import subprocess
import sys
import numpy as np
import pytest

from utils.config import APP_NAME
from monitoring.metrics import ExecutionMetrics
from engine.process_manager import ProcessManager
from engine.worker import execute_data_chunk, dummy_sleep_worker


def _spawn_worker_target(queue, arr):
    """Top-level picklable target for multiprocessing spawn tests."""
    ctx = mp.get_context("spawn")
    ev = ctx.Event()
    res = execute_data_chunk(0, "square", arr, ev)
    queue.put(res)


def test_python_version():
    """Verify supported Python runtime."""
    assert sys.version_info >= (3, 11), "Python 3.11+ is required"


def test_core_dependencies_importable():
    """Verify that all core libraries can be imported and report version strings."""
    import PySide6
    import psutil
    import matplotlib

    assert hasattr(PySide6, "__version__")
    assert hasattr(np, "__version__")
    assert hasattr(psutil, "__version__")
    assert hasattr(matplotlib, "__version__")


def test_worker_isolation_from_qt():
    """Verify in a clean process that engine/worker.py does not import PySide6 or Qt."""
    script = (
        "import sys, engine.worker; "
        "assert 'PySide6' not in sys.modules, 'PySide6 was loaded by worker module!'; "
        "print('ISOLATED_OK')"
    )
    res = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "ISOLATED_OK" in res.stdout


def test_worker_pure_computation(sample_numeric_array):
    """Test worker computation logic in-process."""
    ctx = mp.get_context("spawn")
    cancel_event = ctx.Event()

    result_data = execute_data_chunk(
        chunk_id=1,
        func_name="square",
        data_chunk=sample_numeric_array[:10],
        cancel_event=cancel_event,
    )
    assert result_data["status"] == "completed"
    assert result_data["chunk_id"] == 1
    assert np.allclose(result_data["result"], np.arange(10) ** 2)
    assert result_data["compute_time_ms"] >= 0.0


def test_multiprocessing_spawn_execution():
    """Verify that a worker process can actually be spawned and communicate via Queue."""
    ctx = mp.get_context("spawn")
    assert ctx.get_start_method() == "spawn"

    q = ctx.Queue()
    test_arr = np.array([2.0, 4.0, 6.0])
    p = ctx.Process(target=_spawn_worker_target, args=(q, test_arr))
    p.start()

    # Verify child PID is distinct from parent
    assert p.pid != os.getpid()

    data = q.get(timeout=5.0)
    p.join(timeout=5.0)

    assert data["status"] == "completed"
    assert np.allclose(data["result"], np.array([4.0, 16.0, 36.0]))


def test_process_manager_lifecycle():
    """Verify ProcessManager registers and gracefully cleans up workers."""
    with ProcessManager(start_method="spawn") as pm:
        ctx = pm.ctx
        p = ctx.Process(target=dummy_sleep_worker, args=(10.0,))
        p.start()
        pm.register_worker(0, p)

        active_pids = pm.get_active_pids()
        assert len(active_pids) == 1
        assert p.pid in active_pids

    # Context manager exit should have terminated worker
    assert not p.is_alive()


def test_metrics_speedup_and_efficiency():
    """Verify speedup and parallel efficiency calculation formulas."""
    metrics = ExecutionMetrics(
        sequential_time_ms=100.0,
        parallel_total_time_ms=25.0,
        worker_count=4,
        compute_time_ms=20.0,
    )
    assert metrics.speedup == 4.0
    assert metrics.parallel_efficiency == 100.0
    assert metrics.compute_speedup == 5.0
    assert metrics.compute_efficiency == 125.0

    # Edge cases (zero / negative)
    zero_metrics = ExecutionMetrics(
        sequential_time_ms=100.0,
        parallel_total_time_ms=0.0,
        worker_count=0,
    )
    assert zero_metrics.speedup == 0.0
    assert zero_metrics.parallel_efficiency == 0.0


def test_main_window_instantiation(qapp):
    """Verify that MainWindow instantiates and renders without Qt exceptions."""
    from gui.main_window import MainWindow

    window = MainWindow()
    assert window.windowTitle().startswith(APP_NAME)
    assert window.pages.count() >= 1
    window.close()
