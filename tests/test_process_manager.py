"""Automated Tests for CoreSync Phase 7: Unified Process Management & CPU Affinity."""

import os
import platform
import time
from unittest.mock import MagicMock, patch

import pytest
import psutil

from engine.affinity import (
    AffinityPolicy,
    AffinityResult,
    get_available_system_cpus,
    get_process_affinity,
    resolve_worker_affinities,
    set_process_affinity,
)
from engine.process_manager import (
    ProcessManager,
    WorkerLifecycleStatus,
    WorkerMetadata,
)
from engine.resource_guard import ResourceGuard, ResourceLimits
from engine.data_parallel.executor import DataParallelExecutor
from engine.data_parallel.operations import generate_dataset
from engine.task_parallel.executor import TaskParallelExecutor
from engine.task_parallel.presets import create_diamond_pipeline
from engine.real_system.cpu_stress import RealCPUStressGenerator
from gui.real_system.process_view import RealProcessPage
from gui.core_monitor import CoreMonitorPage
from monitoring.cpu_monitor import CPUMetricsSnapshot
from utils.cpu_topology import CoreType, CPUTopology, LogicalCPU
from utils.hardware.base import ProcessInfo


# Worker dummy targets
def dummy_sleep_worker(duration: float = 1.0):
    time.sleep(duration)


def dummy_compute_worker(n: int = 100_000):
    total = sum(i * i for i in range(n))
    return total


# -----------------------------------------------------------------------------
# 1. Registration, Identification & Metadata
# -----------------------------------------------------------------------------
def test_process_registration_and_metadata():
    pm = ProcessManager(start_method="spawn")
    p = pm.ctx.Process(target=dummy_sleep_worker, args=(0.5,))
    p.start()

    meta = pm.register_worker(
        worker_id="test-w0",
        process=p,
        engine_name="TestEngine",
        task_or_chunk_id="chunk-42",
        assigned_affinity=[0],
    )

    try:
        assert meta.worker_id == "test-w0"
        assert meta.pid == p.pid
        assert meta.parent_pid == os.getpid()
        assert meta.engine_name == "TestEngine"
        assert meta.task_or_chunk_id == "chunk-42"
        assert meta.assigned_cpu_affinity == [0]
        assert meta.status == WorkerLifecycleStatus.RUNNING
        assert meta.is_alive is True

        retrieved = pm.get_worker_metadata("test-w0")
        assert retrieved is not None
        assert retrieved.pid == p.pid

        by_pid = pm.get_worker_metadata(p.pid)
        assert by_pid is not None
        assert by_pid.worker_id == "test-w0"
    finally:
        pm.terminate_all()


def test_worker_lifecycle_tracking_states():
    pm = ProcessManager(start_method="spawn")
    p = pm.ctx.Process(target=dummy_sleep_worker, args=(0.1,))
    p.start()

    pm.register_worker(worker_id="test-w1", process=p, engine_name="TestEngine")
    meta = pm.get_worker_metadata("test-w1")
    assert meta.status == WorkerLifecycleStatus.RUNNING

    # Transition to IDLE
    pm.update_worker_status("test-w1", WorkerLifecycleStatus.IDLE)
    assert meta.status == WorkerLifecycleStatus.IDLE

    # Transition to COMPLETED
    pm.update_worker_status("test-w1", WorkerLifecycleStatus.COMPLETED)
    assert meta.status == WorkerLifecycleStatus.COMPLETED
    assert meta.end_time is not None
    assert meta.runtime_s >= 0.0

    # Transition to FAILED with error
    pm.update_worker_status("test-w1", WorkerLifecycleStatus.FAILED, error_message="Computation crashed")
    assert meta.status == WorkerLifecycleStatus.FAILED
    assert meta.error_message == "Computation crashed"

    pm.terminate_all()


# -----------------------------------------------------------------------------
# 2. CPU Affinity Retrieval, Assignment & Validation
# -----------------------------------------------------------------------------
def test_cpu_affinity_retrieval():
    available = get_available_system_cpus()
    assert isinstance(available, list)
    assert len(available) > 0
    assert all(isinstance(c, int) and c >= 0 for c in available)

    self_aff = get_process_affinity(os.getpid())
    assert isinstance(self_aff, list)
    assert len(self_aff) > 0


def test_cpu_affinity_assignment_valid():
    available = get_available_system_cpus()
    if len(available) < 1:
        pytest.skip("No available CPUs detected.")

    target_cpu = [available[0]]
    res = set_process_affinity(os.getpid(), target_cpu)

    if platform.system() == "Darwin":
        assert res.success is False
        assert "not supported on macOS" in res.message
    else:
        # On Linux and Windows, user processes can set affinity
        assert res.success is True
        assert target_cpu[0] in res.applied_cpus

    # Restore full affinity
    set_process_affinity(os.getpid(), available)


def test_cpu_affinity_invalid_cpu_id_handling():
    # Attempt assigning an invalid negative CPU ID
    res = set_process_affinity(os.getpid(), [-5, 999999])
    assert res.success is False
    assert "Invalid logical CPU IDs" in res.message


def test_cpu_affinity_permission_denied_fallback():
    with patch("os.sched_setaffinity", side_effect=PermissionError("Mock Permission Denied")):
        with patch.object(psutil.Process, "cpu_affinity", side_effect=psutil.AccessDenied()):
            res = set_process_affinity(os.getpid(), [0])
            assert res.success is False
            assert "Permission denied" in res.message or "Access denied" in res.message


def test_unsupported_platform_fallback_darwin():
    with patch("platform.system", return_value="Darwin"):
        res = set_process_affinity(os.getpid(), [0])
        assert res.success is False
        assert res.platform_name == "Darwin"
        assert "not support" in res.message.lower()


# -----------------------------------------------------------------------------
# 3. Worker Allocation Policies
# -----------------------------------------------------------------------------
def test_round_robin_allocation_policy():
    affinities = resolve_worker_affinities(worker_count=4, policy=AffinityPolicy.ROUND_ROBIN)
    assert len(affinities) == 4
    for aff in affinities:
        assert isinstance(aff, list)
        assert len(aff) == 1


def test_manual_worker_mapping_policy():
    mapping = {0: [0], 1: [1, 2], 2: [3]}
    affinities = resolve_worker_affinities(
        worker_count=3,
        policy=AffinityPolicy.MANUAL,
        manual_mapping=mapping,
    )
    assert len(affinities) == 3
    assert affinities[0] == [0]
    assert affinities[1] == [1, 2]
    assert affinities[2] == [3]


def test_hybrid_core_filtering_p_core_and_e_core():
    # Construct a mock hybrid topology
    logical_cpus = {
        0: LogicalCPU(cpu_id=0, package_id=0, core_id=0, thread_siblings=[0], core_type=CoreType.PERFORMANCE),
        1: LogicalCPU(cpu_id=1, package_id=0, core_id=1, thread_siblings=[1], core_type=CoreType.PERFORMANCE),
        2: LogicalCPU(cpu_id=2, package_id=0, core_id=2, thread_siblings=[2], core_type=CoreType.EFFICIENCY),
        3: LogicalCPU(cpu_id=3, package_id=0, core_id=3, thread_siblings=[3], core_type=CoreType.EFFICIENCY),
    }
    topo = CPUTopology(
        logical_cpus=logical_cpus,
        physical_core_count=4,
        logical_cpu_count=4,
        package_count=1,
        p_cores=[0, 1],
        e_cores=[2, 3],
        is_hybrid=True,
        source="mock_hybrid",
    )

    with patch("engine.affinity.get_available_system_cpus", return_value=[0, 1, 2, 3]):
        # P-Core Only
        p_affs = resolve_worker_affinities(worker_count=2, policy=AffinityPolicy.P_CORE_ONLY, topology=topo)
        assert len(p_affs) == 2
        for aff in p_affs:
            assert all(c in [0, 1] for c in aff)

        # E-Core Only
        e_affs = resolve_worker_affinities(worker_count=2, policy=AffinityPolicy.E_CORE_ONLY, topology=topo)
        assert len(e_affs) == 2
        for aff in e_affs:
            assert all(c in [2, 3] for c in aff)


def test_non_hybrid_topology_graceful_fallback():
    # Construct non-hybrid topology
    logical_cpus = {
        0: LogicalCPU(cpu_id=0, package_id=0, core_id=0, thread_siblings=[0], core_type=CoreType.UNKNOWN),
        1: LogicalCPU(cpu_id=1, package_id=0, core_id=1, thread_siblings=[1], core_type=CoreType.UNKNOWN),
    }
    topo = CPUTopology(
        logical_cpus=logical_cpus,
        physical_core_count=2,
        logical_cpu_count=2,
        package_count=1,
        is_hybrid=False,
        source="mock_standard",
    )

    with patch("engine.affinity.get_available_system_cpus", return_value=[0, 1]):
        affs = resolve_worker_affinities(worker_count=2, policy=AffinityPolicy.P_CORE_ONLY, topology=topo)
        assert len(affs) == 2
        # Falls back to all available
        assert affs[0] == [0]
        assert affs[1] == [1]


# -----------------------------------------------------------------------------
# 4. Worker Termination, Reaping & Orphan Detection
# -----------------------------------------------------------------------------
def test_worker_cooperative_cancellation_and_cleanup():
    pm = ProcessManager(start_method="spawn")
    p = pm.spawn_worker(
        target=dummy_sleep_worker,
        args=(5.0,),
        name="CoreSync-DP-Worker-CancelTest",
        engine_name="DataParallel",
        worker_id="cancel-test-0",
    )
    assert p.is_alive()
    p_pid = p.pid

    # Execute 4-stage termination
    pm.terminate_all(coop_timeout=0.1, term_timeout=0.2, kill_timeout=0.1)

    # Verify process terminated
    assert not p.is_alive()
    assert not psutil.pid_exists(p_pid) or psutil.Process(p_pid).status() == psutil.STATUS_ZOMBIE


def test_process_reaping_no_zombies():
    pm = ProcessManager(start_method="spawn")
    p = pm.spawn_worker(
        target=dummy_sleep_worker,
        args=(0.05,),
        name="CoreSync-Task-Worker-ReapTest",
        engine_name="TaskParallel",
        worker_id="reap-test-0",
    )
    p.join(timeout=0.5)
    pm.poll_workers()

    meta = pm.get_worker_metadata("reap-test-0")
    assert meta.status == WorkerLifecycleStatus.COMPLETED
    assert meta.exitcode == 0
    pm.terminate_all()


def test_orphan_detection_and_reaping():
    # Mock psutil.process_iter finding a CoreSync worker with dead parent
    mock_proc = MagicMock()
    mock_proc.info = {
        "pid": 99999,
        "name": "python",
        "cmdline": ["python", "CoreSync-DP-Worker-99"],
        "ppid": 88888,
    }

    with patch("psutil.process_iter", return_value=[mock_proc]):
        with patch("psutil.pid_exists", return_value=False):
            orphans = ProcessManager.detect_orphans()
            assert 99999 in orphans

    # Test reaping mock orphan
    with patch("psutil.Process") as mock_psutil_proc:
        mock_instance = MagicMock()
        mock_psutil_proc.return_value = mock_instance
        with patch.object(ProcessManager, "detect_orphans", return_value=[99999]):
            reaped = ProcessManager.reap_orphans()
            assert reaped == 1
            mock_instance.terminate.assert_called_once()


# -----------------------------------------------------------------------------
# 5. Resource Guard Bounds & Headroom
# -----------------------------------------------------------------------------
def test_resource_guard_limits_and_clamping():
    guard = ResourceGuard(limits=ResourceLimits(max_workers=32))
    assert guard.clamp_worker_count(0) == 1
    assert guard.clamp_worker_count(-5) == 1
    assert guard.clamp_worker_count(10) == 10
    assert guard.clamp_worker_count(500) <= 32


def test_resource_guard_memory_headroom():
    guard = ResourceGuard()
    is_safe, avail_mb, msg = guard.check_memory_headroom(required_mb=10.0)
    assert is_safe is True
    assert avail_mb > 0.0

    # Low memory condition simulation
    with patch("psutil.virtual_memory") as mock_vm:
        mock_vm.return_value.available = 50 * 1024 * 1024  # 50 MB
        is_safe, avail_mb, msg = guard.check_memory_headroom(required_mb=256.0)
        assert is_safe is False
        assert "Low system memory warning" in msg


# -----------------------------------------------------------------------------
# 6. Integration: Data Parallelism with CPU Affinity
# -----------------------------------------------------------------------------
def test_integration_data_parallel_with_affinity():
    executor = DataParallelExecutor()
    data = generate_dataset("transcendental", 10_000, seed=123)

    result = executor.run_parallel(
        op_id="transcendental",
        data=data,
        worker_count=2,
        affinity_policy=AffinityPolicy.ROUND_ROBIN,
    )
    assert result.success is True
    assert len(result.worker_results) == 2
    assert executor._active_workers == []  # Cleaned up


# -----------------------------------------------------------------------------
# 7. Integration: Task Parallelism with CPU Affinity
# -----------------------------------------------------------------------------
def test_integration_task_parallel_with_affinity():
    executor = TaskParallelExecutor()
    graph = create_diamond_pipeline()

    result = executor.run_dag(
        graph=graph,
        worker_count=2,
        affinity_policy=AffinityPolicy.ROUND_ROBIN,
    )
    assert result.success is True
    assert result.completed_tasks == len(graph.tasks)
    assert executor._active_workers == []  # Cleaned up


# -----------------------------------------------------------------------------
# 8. Integration: CPU Stress Generator with CPU Affinity
# -----------------------------------------------------------------------------
def test_integration_cpu_stress_with_affinity():
    gen = RealCPUStressGenerator()
    started = gen.start_stress(
        worker_count=2,
        duration_s=1.0,
        intensity_pct=50.0,
        affinity_policy=AffinityPolicy.ROUND_ROBIN,
    )
    assert started is True
    assert gen.is_running() is True
    status = gen.get_status()
    assert len(status.worker_pids) == 2

    # Clean stop
    gen.stop_stress()
    assert gen.is_running() is False


# -----------------------------------------------------------------------------
# 9. GUI Responsiveness & Metric Updating
# -----------------------------------------------------------------------------
def test_real_process_page_metrics_update(qtbot):
    page = RealProcessPage()
    qtbot.addWidget(page)

    mock_meta = WorkerMetadata(
        worker_id="DP-0",
        pid=12345,
        parent_pid=os.getpid(),
        engine_name="DataParallel",
        task_or_chunk_id="chunk-0",
        assigned_cpu_affinity=[0],
        actual_cpu_affinity=[0],
        status=WorkerLifecycleStatus.RUNNING,
        cpu_utilization=45.2,
        memory_rss_mb=28.4,
    )

    snapshot = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=12.5,
        per_cpu_percent=[10.0, 15.0],
        process_affinity=[0, 1],
        ram_used_gb=8.0,
        ram_total_gb=32.0,
        ram_percent=25.0,
        top_processes=[
            ProcessInfo(pid=100, name="systemd", cpu_percent=1.0, memory_rss_mb=12.0),
        ],
        coresync_workers_count=1,
        coresync_worker_pids=[12345],
        coresync_workers=[mock_meta],
    )

    page.update_metrics(snapshot)
    assert page.card_workers.value_label.text() == "1 Workers"
    assert page.table_workers.rowCount() == 1
    assert page.table.rowCount() == 1


def test_core_monitor_page_worker_pinning(qtbot):
    page = CoreMonitorPage()
    qtbot.addWidget(page)

    mock_meta = WorkerMetadata(
        worker_id="Stress-0",
        pid=54321,
        parent_pid=os.getpid(),
        engine_name="CPUStress",
        assigned_cpu_affinity=[0],
        actual_cpu_affinity=[0],
        status=WorkerLifecycleStatus.RUNNING,
    )

    snapshot = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=30.0,
        per_cpu_percent=[50.0] * page.summary.logical_cores,
        process_affinity=list(range(page.summary.logical_cores)),
        coresync_workers=[mock_meta],
    )

    page.update_metrics(snapshot)
    assert 0 in page.core_widgets
    assert "Stress-0" in page.core_widgets[0].worker_lbl.text()
