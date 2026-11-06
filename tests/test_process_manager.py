"""Automated Tests for CoreSync Phase 7: Unified Process Management & CPU Affinity."""

import os
import platform
import signal
import sys
import time
from unittest.mock import MagicMock, patch

import pytest
import psutil

from engine.affinity import (
    AffinityPolicy,
    AffinityResult,
    get_available_system_cpus,
    get_process_actual_cpu,
    get_process_affinity,
    resolve_worker_affinities,
    set_process_affinity,
)
from engine.process_manager import (
    ParentDeathProtectionResult,
    PlatformProtectionCapability,
    ProcessManager,
    WorkerLifecycleStatus,
    WorkerMetadata,
    _setup_win32_parent_handle_watchdog,
    enable_parent_death_protection,
    get_platform_protection_capabilities,
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


def _parent_death_worker(ready_event):
    """Child worker for testing parent-death self-termination."""
    enable_parent_death_protection(os.getppid())
    ready_event.set()
    while True:
        time.sleep(0.05)


def _parent_death_parent(child_pid_queue):
    """Parent process for testing parent-death self-termination."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    ready = ctx.Event()
    child = ctx.Process(target=_parent_death_worker, args=(ready,))
    child.daemon = True
    child.start()
    ready.wait(timeout=3.0)
    child_pid_queue.put(child.pid)
    while True:
        time.sleep(0.05)


def _startup_race_child(expected_ppid, entered_flag):
    """Child worker simulating delayed initialization to trigger parent-death startup race."""
    # Delay so parent process terminates before prctl setup is reached
    time.sleep(0.25)
    enable_parent_death_protection(expected_ppid)
    # If the startup race check works, os._exit(0) is called and this is never reached
    entered_flag.value = 1
    while True:
        time.sleep(0.05)


def _startup_race_parent(child_pid_q, entered_flag):
    """Parent process that spawns child and abruptly terminates."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    parent_pid = os.getpid()
    child = ctx.Process(target=_startup_race_child, args=(parent_pid, entered_flag))
    child.daemon = True
    child.start()
    child_pid_q.put(child.pid)
    time.sleep(0.05)
    os._exit(0)


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


# -----------------------------------------------------------------------------
# 10. Phase 7.1 Verification Audit Tests
# -----------------------------------------------------------------------------
def test_forced_parent_death_worker_self_termination():
    """Verify child worker self-terminates when parent process is killed with SIGKILL."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    parent = ctx.Process(target=_parent_death_parent, args=(q,))
    parent.start()

    child_pid = q.get(timeout=3.0)
    unrelated_pid = os.getpid()

    # Verify both are running initially
    assert psutil.pid_exists(parent.pid)
    assert psutil.pid_exists(child_pid)
    assert psutil.pid_exists(unrelated_pid)

    # Forcefully terminate parent with SIGKILL (kill -9) - no parent cleanup code runs
    os.kill(parent.pid, signal.SIGKILL)
    parent.join(timeout=1.0)

    # Verify child exits within 1.0 second (allowing up to 1.5s for scheduling jitter)
    deadline = time.time() + 1.5
    child_alive = True
    while time.time() < deadline:
        try:
            p = psutil.Process(child_pid)
            if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
                child_alive = False
                break
        except psutil.NoSuchProcess:
            child_alive = False
            break
        time.sleep(0.05)

    assert not child_alive, f"Child PID {child_pid} remained alive after parent death!"
    # Verify unrelated process is completely unaffected
    assert psutil.pid_exists(unrelated_pid)


def test_actual_cpu_execution_observation():
    """Verify that get_process_actual_cpu reports actual CPU core and distinguishes it from affinity."""
    current_cpu = get_process_actual_cpu(os.getpid())
    if sys.platform.startswith("linux"):
        assert current_cpu is not None
        assert isinstance(current_cpu, int)
        assert 0 <= current_cpu < os.cpu_count()

    pm = ProcessManager(start_method="spawn")
    proc = pm.spawn_worker(
        target=dummy_sleep_worker,
        args=(1.0,),
        name="test-actual-cpu",
        engine_name="TestEngine",
        worker_id="w-obs-cpu",
        affinity_cpus=[0],
    )

    try:
        meta = pm.get_worker_metadata("w-obs-cpu")
        assert meta is not None
        assert meta.assigned_cpu_affinity == [0]

        # Check observed execution core on Linux
        actual_cpu = get_process_actual_cpu(proc.pid)
        if sys.platform.startswith("linux"):
            assert actual_cpu is not None
            # Being pinned to core 0, if running it will report 0
            assert actual_cpu == 0
    finally:
        pm.terminate_all()


def test_worker_startup_failure_tracked_as_failed():
    """Verify that worker startup failures immediately register FAILED status with error details."""
    pm = ProcessManager(start_method="spawn")

    with patch.object(pm.ctx, "Process", side_effect=RuntimeError("Simulated fork/exec resource error")):
        with pytest.raises(RuntimeError, match="Simulated fork/exec resource error"):
            pm.spawn_worker(
                target=dummy_sleep_worker,
                args=(1.0,),
                name="failed-worker-proc",
                engine_name="TestEngine",
                worker_id="fail-w0",
            )

    meta = pm.get_worker_metadata("fail-w0")
    assert meta is not None
    assert meta.status == WorkerLifecycleStatus.FAILED
    assert meta.pid is None
    assert "Worker process startup failure" in meta.error_message


def test_repeated_shutdown_idempotency():
    """Verify that calling terminate_all repeatedly is completely safe and idempotent."""
    pm = ProcessManager(start_method="spawn")
    p1 = pm.spawn_worker(
        target=dummy_sleep_worker,
        args=(2.0,),
        name="idem-1",
        engine_name="TestEngine",
        worker_id="id-1",
    )
    p2 = pm.spawn_worker(
        target=dummy_sleep_worker,
        args=(2.0,),
        name="idem-2",
        engine_name="TestEngine",
        worker_id="id-2",
    )

    # Initial terminate
    pm.terminate_all(coop_timeout=0.2, term_timeout=0.2, kill_timeout=0.2)
    assert not p1.is_alive()
    assert not p2.is_alive()
    assert pm.get_worker_metadata("id-1").status == WorkerLifecycleStatus.TERMINATED
    assert pm.get_worker_metadata("id-2").status == WorkerLifecycleStatus.TERMINATED

    # Second terminate (idempotency check: should complete with no exceptions)
    pm.terminate_all(coop_timeout=0.1, term_timeout=0.1, kill_timeout=0.1)

    # Third terminate (idempotency check)
    pm.terminate_all(coop_timeout=0.1, term_timeout=0.1, kill_timeout=0.1)
    assert not pm.get_active_workers()


def test_resource_guard_worker_validation_explanations():
    """Verify ResourceGuard validates worker requests and produces explanatory clamp messages."""
    guard = ResourceGuard()

    # Negative count
    neg_count, neg_msg = guard.validate_worker_request(-4)
    assert neg_count == 1
    assert neg_msg is not None
    assert "must be >= 1" in neg_msg

    # Zero count
    zero_count, zero_msg = guard.validate_worker_request(0)
    assert zero_count == 1
    assert zero_msg is not None
    assert "must be >= 1" in zero_msg

    # Excessive count beyond hard cap
    excessive_count, excessive_msg = guard.validate_worker_request(9999)
    assert excessive_count <= guard.limits.max_workers
    assert excessive_msg is not None
    assert "exceeds safety limit" in excessive_msg

    # Valid count
    valid_count, valid_msg = guard.validate_worker_request(2)
    assert valid_count == 2
    assert valid_msg is None


def test_resource_guard_insufficient_memory_rejection():
    """Verify ResourceGuard rejects execution when memory headroom is insufficient."""
    guard = ResourceGuard()

    # Mock low available memory (only 50 MB available)
    mock_vm = MagicMock()
    mock_vm.available = 50 * 1024 * 1024  # 50 MB
    mock_vm.percent = 85.0

    with patch("psutil.virtual_memory", return_value=mock_vm):
        headroom, avail_mb, msg = guard.check_memory_headroom(
            required_mb=256.0, worker_count=8
        )
        assert headroom is False
        assert round(avail_mb, 1) == 50.0
        assert "Low system memory warning" in msg


# -----------------------------------------------------------------------------
# 11. Phase 7.2 Startup Race & Platform Reliability Tests
# -----------------------------------------------------------------------------
def test_parent_death_startup_race_prevention():
    """Verify child worker self-terminates immediately if parent dies before prctl is reached."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    entered_flag = ctx.Value("i", 0)

    parent = ctx.Process(target=_startup_race_parent, args=(q, entered_flag))
    parent.start()

    child_pid = q.get(timeout=3.0)
    parent.join(timeout=1.0)

    # Wait for child to initialize, detect that parent is already dead, and exit
    time.sleep(0.6)

    child_alive = False
    try:
        cp = psutil.Process(child_pid)
        if cp.is_running() and cp.status() != psutil.STATUS_ZOMBIE:
            child_alive = True
    except psutil.NoSuchProcess:
        child_alive = False

    assert not child_alive, f"Child PID {child_pid} survived startup race as an orphan!"
    # Crucial assertion: the child NEVER reached its main computational loop
    assert entered_flag.value == 0, "Child executed computational tasks despite parent dying before prctl!"


def test_prctl_error_handling_does_not_report_enabled():
    """Verify that prctl() failure on Linux returns enabled=False and records error details."""
    mock_libc = MagicMock()
    mock_libc.prctl.return_value = -1

    with patch("ctypes.CDLL", return_value=mock_libc), \
         patch("ctypes.get_errno", return_value=22):  # EINVAL = 22
        res = enable_parent_death_protection(parent_pid=os.getppid())

        if sys.platform.startswith("linux"):
            assert res.enabled is False
            assert res.mechanism == "Failed"
            assert "prctl(PR_SET_PDEATHSIG) failed" in res.error
            assert "errno 22" in res.error


def test_windows_parent_death_handle_monitoring_mocked():
    """Verify Win32 process handle wait mechanism (Mocked Windows platform on Linux)."""
    mock_kernel32 = MagicMock()
    mock_kernel32.OpenProcess.return_value = 12345  # valid handle
    mock_kernel32.WaitForSingleObject.return_value = 0  # WAIT_OBJECT_0
    mock_kernel32.CloseHandle.return_value = 1

    mock_ctypes = MagicMock()
    mock_ctypes.windll.kernel32 = mock_kernel32
    mock_exit = MagicMock()

    with patch.dict("sys.modules", {"ctypes": mock_ctypes}):
        with patch("sys.platform", "win32"):
            success, err = _setup_win32_parent_handle_watchdog(os.getpid(), exit_callback=mock_exit)
            assert success is True
            assert err is None
            mock_kernel32.OpenProcess.assert_called_once_with(0x00100000, False, os.getpid())
            # Allow thread to execute
            time.sleep(0.05)
            mock_kernel32.WaitForSingleObject.assert_called_once()
            mock_exit.assert_called_with(0)

    # Test OpenProcess failure (e.g. parent already terminated)
    mock_kernel32_fail = MagicMock()
    mock_kernel32_fail.OpenProcess.return_value = 0  # NULL handle
    mock_kernel32_fail.GetLastError.return_value = 87  # ERROR_INVALID_PARAMETER
    mock_ctypes_fail = MagicMock()
    mock_ctypes_fail.windll.kernel32 = mock_kernel32_fail

    with patch.dict("sys.modules", {"ctypes": mock_ctypes_fail}):
        with patch("sys.platform", "win32"), \
             patch("psutil.pid_exists", return_value=True):
            success, err = _setup_win32_parent_handle_watchdog(os.getpid(), exit_callback=mock_exit)
            assert success is False
            assert "OpenProcess failed" in err
            assert "87" in err


def test_platform_protection_capabilities_matrix():
    """Verify platform capabilities matrix accurately reports mechanisms and limitations."""
    # Current Linux environment
    cap_linux = get_platform_protection_capabilities()
    if sys.platform.startswith("linux"):
        assert cap_linux.has_kernel_pdeathsig is True
        assert cap_linux.guarantee_level == "kernel_synchronous"
        assert "SIGTERM" in cap_linux.guarantee_description

    # Windows simulation
    with patch("sys.platform", "win32"):
        cap_win = get_platform_protection_capabilities()
        assert cap_win.has_win32_handle_wait is True
        assert cap_win.has_kernel_pdeathsig is False
        assert cap_win.guarantee_level == "handle_synchronous"
        assert "SYNCHRONIZE" in cap_win.limitations

    # macOS Darwin simulation
    with patch("sys.platform", "darwin"):
        cap_mac = get_platform_protection_capabilities()
        assert cap_mac.has_kernel_pdeathsig is False
        assert cap_mac.has_kqueue_proc is True
        assert cap_mac.guarantee_level == "bounded_polling_or_kqueue"
        assert "macOS kernel does NOT provide PR_SET_PDEATHSIG" in cap_mac.limitations


def test_resource_guard_heavy_load_advisory_warning():
    """Verify that host heavy load (95%+) produces an advisory warning and is NOT an execution block."""
    guard = ResourceGuard()

    mock_vm = MagicMock()
    mock_vm.percent = 97.5  # Saturated RAM

    with patch("psutil.cpu_percent", return_value=98.2), \
         patch("psutil.virtual_memory", return_value=mock_vm):
        is_heavy, msg = guard.is_system_under_heavy_load()
        assert is_heavy is True
        # Explicitly must be documented as an advisory warning, NOT a block
        assert "Advisory Warning" in msg
        assert "Execution is not blocked" in msg
        assert "98.2%" in msg

    # Re-verify that while heavy load is advisory, worker clamping remains strictly enforced
    clamped, clamp_msg = guard.validate_worker_request(1000)
    assert clamped <= guard.limits.max_workers
    assert clamped == min(guard.limits.max_workers, guard._logical_cores * 2)
    assert clamp_msg is not None

    # Re-verify that insufficient memory remains strictly enforced
    mock_vm_low = MagicMock()
    mock_vm_low.available = 10 * 1024 * 1024  # 10 MB available
    with patch("psutil.virtual_memory", return_value=mock_vm_low):
        headroom, _, mem_msg = guard.check_memory_headroom(required_mb=512.0)
        assert headroom is False  # Enforced rejection
        assert "Low system memory warning" in mem_msg


