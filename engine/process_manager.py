"""Unified Process Manager for CoreSync.

Oversees worker process lifecycles across Data Parallelism, Task Parallelism,
CPU Stress Generation, and background services. Coordinates worker registration,
metadata tracking, CPU affinity binding, resource monitoring, graceful-to-forced
termination, orphan detection, and zombie reaping.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
import multiprocessing as mp
from multiprocessing.process import BaseProcess
import os
import signal
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

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
from engine.resource_guard import ResourceGuard, ResourceLimits
from utils.config import (
    COOPERATIVE_TIMEOUT,
    SIGTERM_TIMEOUT,
    SIGKILL_TIMEOUT,
)

logger = logging.getLogger("CoreSync.ProcessManager")


@dataclass
class ParentDeathProtectionResult:
    """Outcome and diagnostics of parent-death protection configuration."""
    enabled: bool
    mechanism: str
    target_parent_pid: int
    error: Optional[str] = None
    startup_race_checked: bool = True
    limitations: Optional[str] = None

    def __bool__(self) -> bool:
        return self.enabled


@dataclass
class PlatformProtectionCapability:
    """Detailed platform capabilities and limitations for parent-death protection."""
    platform_name: str
    has_kernel_pdeathsig: bool
    has_win32_handle_wait: bool
    has_kqueue_proc: bool
    watchdog_polling_supported: bool
    guarantee_level: str
    guarantee_description: str
    limitations: str


def get_platform_protection_capabilities() -> PlatformProtectionCapability:
    """Query the supported parent-death protection mechanisms and limitations for current OS."""
    plat = sys.platform
    if plat.startswith("linux"):
        return PlatformProtectionCapability(
            platform_name=plat,
            has_kernel_pdeathsig=True,
            has_win32_handle_wait=False,
            has_kqueue_proc=False,
            watchdog_polling_supported=True,
            guarantee_level="kernel_synchronous",
            guarantee_description="Kernel delivers SIGTERM immediately upon parent exit + startup race check + 100ms watchdog.",
            limitations="PR_SET_PDEATHSIG only delivers signal if parent dies while child is alive. Startup race check verifies getppid() immediately after prctl().",
        )
    elif plat == "win32":
        return PlatformProtectionCapability(
            platform_name=plat,
            has_kernel_pdeathsig=False,
            has_win32_handle_wait=True,
            has_kqueue_proc=False,
            watchdog_polling_supported=True,
            guarantee_level="handle_synchronous",
            guarantee_description="SYNCHRONIZE handle to parent process waits on signaled state in dedicated thread without polling.",
            limitations="Requires OpenProcess(SYNCHRONIZE) permission on parent process. If handle creation fails, falls back to bounded polling.",
        )
    elif plat == "darwin":
        return PlatformProtectionCapability(
            platform_name=plat,
            has_kernel_pdeathsig=False,
            has_win32_handle_wait=False,
            has_kqueue_proc=True,
            watchdog_polling_supported=True,
            guarantee_level="bounded_polling_or_kqueue",
            guarantee_description="Event-driven kqueue NOTE_EXIT when supported, backed by 100ms getppid() reparenting watchdog.",
            limitations="macOS kernel does NOT provide PR_SET_PDEATHSIG. Cannot guarantee zero-delay kernel-synchronous termination; bounded to <= 100ms polling.",
        )
    else:
        return PlatformProtectionCapability(
            platform_name=plat,
            has_kernel_pdeathsig=False,
            has_win32_handle_wait=False,
            has_kqueue_proc=False,
            watchdog_polling_supported=True,
            guarantee_level="bounded_polling",
            guarantee_description="Generic POSIX reparenting polling watchdog thread checking getppid() every 100ms.",
            limitations="Relies on periodic getppid() polling; bounded by 100ms sleep interval.",
        )


def _setup_win32_parent_handle_watchdog(
    expected_ppid: int,
    exit_callback: Callable = os._exit,
) -> Tuple[bool, Optional[str]]:
    """Configure Win32 waitable process handle monitoring for parent death."""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x00100000
        # Open waitable synchronization handle to parent process
        h_parent = kernel32.OpenProcess(SYNCHRONIZE, False, expected_ppid)
        if not h_parent:
            err_code = kernel32.GetLastError()
            if not psutil.pid_exists(expected_ppid):
                # Parent has already terminated
                exit_callback(0)
            return False, f"OpenProcess failed for parent PID {expected_ppid} (code {err_code})"

        def _win32_watchdog_worker(handle):
            INFINITE = 0xFFFFFFFF
            WAIT_OBJECT_0 = 0x00000000
            try:
                res = kernel32.WaitForSingleObject(handle, INFINITE)
                if res == WAIT_OBJECT_0:
                    exit_callback(0)
            finally:
                try:
                    kernel32.CloseHandle(handle)
                except Exception:
                    pass
                exit_callback(0)

        t = threading.Thread(
            target=_win32_watchdog_worker,
            args=(h_parent,),
            daemon=True,
            name="CoreSync-Win32ParentWatchdog",
        )
        t.start()
        return True, None
    except Exception as e:
        return False, f"Win32 handle monitoring setup error: {e}"


def _start_generic_watchdog_thread(
    expected_ppid: int,
    exit_callback: Callable = os._exit,
) -> threading.Thread:
    """Launch cross-platform watchdog polling thread monitoring parent PID and reparenting."""
    def _parent_watchdog_loop():
        while True:
            time.sleep(0.1)
            curr_ppid = os.getppid()
            if curr_ppid != expected_ppid:
                # Parent exited and child was reparented to init / subreaper
                exit_callback(0)
            try:
                if not psutil.pid_exists(expected_ppid):
                    exit_callback(0)
            except Exception:
                pass

    watchdog = threading.Thread(
        target=_parent_watchdog_loop,
        daemon=True,
        name="CoreSync-ParentDeathWatchdog",
    )
    watchdog.start()
    return watchdog


def enable_parent_death_protection(parent_pid: Optional[int] = None) -> ParentDeathProtectionResult:
    """Configure parent-death signaling and watchdog thread for worker child processes.

    Strict 5-step sequence eliminating startup race condition:
    1. Capture expected parent PID before enabling protection.
    2. Call prctl(PR_SET_PDEATHSIG, SIGTERM) on Linux.
    3. Immediately call os.getppid().
    4. If current parent PID differs from expected PID (or expected <= 1), terminate immediately.
    5. Start child-side watchdog for subsequent parent-death monitoring.

    Returns:
        ParentDeathProtectionResult indicating whether setup succeeded, mechanism, and errors.
    """
    # Step 1: Capture expected parent PID before enabling protection
    expected_ppid = int(parent_pid) if (parent_pid is not None and parent_pid > 0) else os.getppid()

    # Step 2: Call prctl(PR_SET_PDEATHSIG, SIGTERM) on Linux
    linux_pdeath_ok = False
    setup_error = None
    mechanism = "None"
    limitations = None

    if sys.platform.startswith("linux"):
        try:
            import ctypes
            libc = ctypes.CDLL(None, use_errno=True)
            # PR_SET_PDEATHSIG = 1, signal.SIGTERM = 15
            ret = libc.prctl(1, signal.SIGTERM, 0, 0, 0)
            if ret != 0:
                errno_val = ctypes.get_errno()
                setup_error = f"prctl(PR_SET_PDEATHSIG) failed with return code {ret}, errno {errno_val}"
                logger.error(setup_error)
            else:
                linux_pdeath_ok = True
                mechanism = "PR_SET_PDEATHSIG+Watchdog"
        except Exception as e:
            setup_error = f"Could not configure PR_SET_PDEATHSIG: {e}"
            logger.error(setup_error)

    # Step 3 & 4: Immediately call os.getppid() and check for startup race
    current_ppid = os.getppid()
    if current_ppid != expected_ppid:
        logger.critical(
            f"Parent-death startup race detected: expected parent PID {expected_ppid}, "
            f"but current getppid() is {current_ppid}. Self-terminating immediately."
        )
        os._exit(0)

    # Step 5: Start or retain child-side watchdog for subsequent parent-death detection
    if sys.platform == "win32":
        win_ok, win_err = _setup_win32_parent_handle_watchdog(expected_ppid)
        if win_ok:
            return ParentDeathProtectionResult(
                enabled=True,
                mechanism="Win32-ProcessHandle-Wait",
                target_parent_pid=expected_ppid,
                startup_race_checked=True,
            )
        else:
            setup_error = win_err
            # Fall back to generic watchdog thread below

    elif sys.platform == "darwin":
        limitations = (
            "macOS lacks PR_SET_PDEATHSIG kernel signaling. "
            "Protection operates via child-side 100ms watchdog polling; termination is bounded, not zero-delay."
        )
        mechanism = "Darwin-Watchdog-BoundedPolling"

    # Start generic polling watchdog thread (used on Linux alongside PR_SET_PDEATHSIG,
    # on Darwin, and as fallback on Windows)
    _start_generic_watchdog_thread(expected_ppid)

    if sys.platform.startswith("linux"):
        if linux_pdeath_ok:
            return ParentDeathProtectionResult(
                enabled=True,
                mechanism="PR_SET_PDEATHSIG+Watchdog",
                target_parent_pid=expected_ppid,
                startup_race_checked=True,
            )
        else:
            # prctl failed on Linux! Do NOT report protection as enabled when setup fails!
            return ParentDeathProtectionResult(
                enabled=False,
                mechanism="Failed",
                target_parent_pid=expected_ppid,
                error=setup_error,
                startup_race_checked=True,
                limitations="prctl setup failed; fallback watchdog running without kernel signal.",
            )

    return ParentDeathProtectionResult(
        enabled=(setup_error is None),
        mechanism=mechanism,
        target_parent_pid=expected_ppid,
        error=setup_error,
        startup_race_checked=True,
        limitations=limitations,
    )


class WorkerLifecycleStatus(str, Enum):
    """Lifecycle status states for worker processes."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    IDLE = "idle"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"


@dataclass
class WorkerMetadata:
    """Comprehensive tracking record for an individual worker process."""
    worker_id: Union[int, str]
    pid: Optional[int]
    parent_pid: int
    engine_name: str
    task_or_chunk_id: Optional[str] = None
    requested_cpu_affinity: List[int] = field(default_factory=list)
    assigned_cpu_affinity: List[int] = field(default_factory=list)
    actual_cpu_affinity: List[int] = field(default_factory=list)
    last_observed_cpu: Optional[int] = None
    status: WorkerLifecycleStatus = WorkerLifecycleStatus.INITIALIZING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    cpu_utilization: float = 0.0
    memory_rss_mb: float = 0.0
    exitcode: Optional[int] = None
    error_message: Optional[str] = None

    @property
    def is_alive(self) -> bool:
        return self.status in (WorkerLifecycleStatus.INITIALIZING, WorkerLifecycleStatus.RUNNING, WorkerLifecycleStatus.IDLE)

    @property
    def runtime_s(self) -> float:
        if self.end_time is not None:
            return max(0.0, self.end_time - self.start_time)
        return max(0.0, time.time() - self.start_time)


class ProcessManager:
    """Unified Process Manager coordinating worker lifecycle, affinity, and cleanup."""

    # Thread-safe global registry of all active workers across any ProcessManager instance
    _registry_lock = threading.Lock()
    _global_registry: Dict[int, WorkerMetadata] = {}  # PID -> WorkerMetadata

    def __init__(
        self,
        start_method: str = "spawn",
        resource_limits: Optional[ResourceLimits] = None,
    ):
        self.ctx = mp.get_context(start_method)
        self.resource_guard = ResourceGuard(limits=resource_limits)
        self.cancel_event = self.ctx.Event()

        # Local instance worker handles and metadata
        self._workers: Dict[Union[int, str], BaseProcess] = {}       # worker_id -> BaseProcess
        self._metadata: Dict[Union[int, str], WorkerMetadata] = {}   # worker_id -> WorkerMetadata
        self._pid_to_worker_id: Dict[int, Union[int, str]] = {}      # PID -> worker_id

    # -------------------------------------------------------------------------
    # Global Registry Access
    # -------------------------------------------------------------------------
    @classmethod
    def get_global_active_workers(cls) -> List[WorkerMetadata]:
        """Return a snapshot of all active CoreSync workers across all engines."""
        with cls._registry_lock:
            # Filter and verify alive
            active = []
            for meta in list(cls._global_registry.values()):
                if meta.pid and meta.is_alive:
                    try:
                        p = psutil.Process(meta.pid)
                        if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                            active.append(meta)
                        else:
                            meta.status = WorkerLifecycleStatus.COMPLETED
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        meta.status = WorkerLifecycleStatus.COMPLETED
            return active

    @classmethod
    def get_all_tracked_workers(cls) -> List[WorkerMetadata]:
        """Return all tracked workers (both active and recent terminal)."""
        with cls._registry_lock:
            return list(cls._global_registry.values())

    @classmethod
    def clear_global_registry(cls) -> None:
        """Clear the shared global registry (primarily for testing teardowns)."""
        with cls._registry_lock:
            cls._global_registry.clear()

    # -------------------------------------------------------------------------
    # Spawning & Registration
    # -------------------------------------------------------------------------
    def spawn_worker(
        self,
        target: Callable,
        args: tuple,
        name: str,
        engine_name: str,
        worker_id: Union[int, str],
        affinity_cpus: Optional[List[int]] = None,
        task_or_chunk_id: Optional[str] = None,
        daemon: bool = True,
    ) -> BaseProcess:
        """Spawn a child process under the 'spawn' context with affinity and registration."""
        assigned_aff = list(affinity_cpus) if affinity_cpus else []

        try:
            proc = self.ctx.Process(target=target, args=args, name=name)
            proc.daemon = daemon
            proc.start()
        except Exception as e:
            err = f"Worker process startup failure: {e}"
            logger.error(f"Failed to start worker '{worker_id}': {err}")
            fail_meta = WorkerMetadata(
                worker_id=worker_id,
                pid=None,
                parent_pid=os.getpid(),
                engine_name=engine_name,
                task_or_chunk_id=task_or_chunk_id,
                requested_cpu_affinity=list(assigned_aff),
                assigned_cpu_affinity=list(assigned_aff),
                status=WorkerLifecycleStatus.FAILED,
                error_message=err,
            )
            self._metadata[worker_id] = fail_meta
            raise

        # Apply CPU affinity before worker proceeds with computational workload
        actual_aff: List[int] = []
        observed_cpu: Optional[int] = None

        if assigned_aff and proc.pid:
            aff_res = set_process_affinity(proc.pid, assigned_aff)
            actual_aff = aff_res.applied_cpus
            observed_cpu = aff_res.actual_observed_cpu or get_process_actual_cpu(proc.pid)
            if not aff_res.success:
                logger.warning(f"Could not apply affinity {assigned_aff} to worker {worker_id} (PID {proc.pid}): {aff_res.message}")
        elif proc.pid:
            actual_aff = get_process_affinity(proc.pid)
            observed_cpu = get_process_actual_cpu(proc.pid)

        self.register_worker(
            worker_id=worker_id,
            process=proc,
            engine_name=engine_name,
            task_or_chunk_id=task_or_chunk_id,
            requested_affinity=assigned_aff,
            assigned_affinity=assigned_aff,
            actual_affinity=actual_aff,
            last_observed_cpu=observed_cpu,
        )

        return proc

    def register_worker(
        self,
        worker_id: Union[int, str],
        process: BaseProcess,
        engine_name: str = "Generic",
        task_or_chunk_id: Optional[str] = None,
        requested_affinity: Optional[List[int]] = None,
        assigned_affinity: Optional[List[int]] = None,
        actual_affinity: Optional[List[int]] = None,
        last_observed_cpu: Optional[int] = None,
    ) -> WorkerMetadata:
        """Register a worker process and record comprehensive metadata."""
        pid = process.pid
        parent_pid = os.getpid()

        meta = WorkerMetadata(
            worker_id=worker_id,
            pid=pid,
            parent_pid=parent_pid,
            engine_name=engine_name,
            task_or_chunk_id=task_or_chunk_id,
            requested_cpu_affinity=list(requested_affinity or assigned_affinity or []),
            assigned_cpu_affinity=list(assigned_affinity or []),
            actual_cpu_affinity=list(actual_affinity or (get_process_affinity(pid) if pid else [])),
            last_observed_cpu=last_observed_cpu or (get_process_actual_cpu(pid) if pid else None),
            status=WorkerLifecycleStatus.RUNNING,
            start_time=time.time(),
        )

        self._workers[worker_id] = process
        self._metadata[worker_id] = meta
        if pid:
            self._pid_to_worker_id[pid] = worker_id
            with self._registry_lock:
                self._global_registry[pid] = meta

        logger.debug(
            f"Registered worker '{worker_id}' (PID {pid}, Engine {engine_name}, "
            f"Affinity: {meta.assigned_cpu_affinity}, Core: {meta.last_observed_cpu})"
        )
        return meta

    # -------------------------------------------------------------------------
    # Backward Compatibility Aliases
    # -------------------------------------------------------------------------
    @property
    def workers(self) -> Dict[Union[int, str], BaseProcess]:
        """Backward-compatible access to worker processes dictionary."""
        return self._workers

    def get_active_pids(self) -> List[int]:
        """Return list of active worker process IDs."""
        return [p.pid for p in self._workers.values() if p.pid is not None and p.is_alive()]

    # -------------------------------------------------------------------------
    # Process Monitoring & Metric Updates
    # -------------------------------------------------------------------------
    def update_worker_status(
        self,
        worker_id_or_pid: Union[int, str],
        status: WorkerLifecycleStatus,
        task_or_chunk_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update a worker's lifecycle status and optional task context."""
        meta = self.get_worker_metadata(worker_id_or_pid)
        if not meta:
            return

        meta.status = status
        if task_or_chunk_id is not None:
            meta.task_or_chunk_id = task_or_chunk_id
        if error_message:
            meta.error_message = error_message
        if status in (WorkerLifecycleStatus.COMPLETED, WorkerLifecycleStatus.FAILED, WorkerLifecycleStatus.CANCELLED, WorkerLifecycleStatus.TERMINATED):
            if meta.end_time is None:
                meta.end_time = time.time()

    def update_worker_metrics(self, worker_id_or_pid: Union[int, str]) -> None:
        """Sample CPU%, Memory RSS (MB), and observed running CPU core for a registered worker."""
        meta = self.get_worker_metadata(worker_id_or_pid)
        if not meta or not meta.pid:
            return

        cpu_p, rss_mb = self.resource_guard.inspect_process_resources(meta.pid)
        meta.cpu_utilization = cpu_p
        meta.memory_rss_mb = rss_mb
        meta.last_observed_cpu = get_process_actual_cpu(meta.pid)

    def poll_workers(self) -> List[WorkerMetadata]:
        """Check all registered workers, update metrics, detect exitcodes, and return metadata."""
        for worker_id, proc in list(self._workers.items()):
            meta = self._metadata.get(worker_id)
            if not meta:
                continue

            if proc.pid:
                self.update_worker_metrics(worker_id)

            if not proc.is_alive():
                meta.exitcode = proc.exitcode
                if meta.end_time is None:
                    meta.end_time = time.time()
                if proc.exitcode == 0:
                    if meta.status not in (WorkerLifecycleStatus.CANCELLED, WorkerLifecycleStatus.TERMINATED):
                        meta.status = WorkerLifecycleStatus.COMPLETED
                else:
                    if meta.status not in (WorkerLifecycleStatus.CANCELLED, WorkerLifecycleStatus.TERMINATED):
                        meta.status = WorkerLifecycleStatus.FAILED
                        if not meta.error_message:
                            meta.error_message = f"Process exited with non-zero code {proc.exitcode}"

        return list(self._metadata.values())

    def get_worker_metadata(self, worker_id_or_pid: Union[int, str]) -> Optional[WorkerMetadata]:
        """Lookup WorkerMetadata by worker_id or PID."""
        if worker_id_or_pid in self._metadata:
            return self._metadata[worker_id_or_pid]
        if isinstance(worker_id_or_pid, int) and worker_id_or_pid in self._pid_to_worker_id:
            w_id = self._pid_to_worker_id[worker_id_or_pid]
            return self._metadata.get(w_id)
        # Search global registry fallback
        if isinstance(worker_id_or_pid, int):
            with self._registry_lock:
                return self._global_registry.get(worker_id_or_pid)
        return None

    def get_active_workers(self) -> List[WorkerMetadata]:
        """Return list of active workers for this manager instance."""
        self.poll_workers()
        return [m for m in self._metadata.values() if m.is_alive]

    # -------------------------------------------------------------------------
    # Termination Protocols (Cooperative -> SIGTERM -> SIGKILL -> Reap)
    # -------------------------------------------------------------------------
    def cancel_worker(self, worker_id_or_pid: Union[int, str]) -> None:
        """Mark a worker as cancelled."""
        self.update_worker_status(worker_id_or_pid, WorkerLifecycleStatus.CANCELLED)

    def terminate_worker(self, worker_id_or_pid: Union[int, str], timeout_s: float = 0.5) -> bool:
        """Gracefully terminate a single worker process."""
        meta = self.get_worker_metadata(worker_id_or_pid)
        if not meta or not meta.pid:
            return False

        proc = self._workers.get(meta.worker_id)
        if proc and proc.is_alive():
            try:
                proc.terminate()
                proc.join(timeout=timeout_s)
                meta.status = WorkerLifecycleStatus.TERMINATED
                meta.end_time = time.time()
                meta.exitcode = proc.exitcode
                return True
            except Exception as e:
                logger.error(f"Error terminating worker {meta.worker_id}: {e}")
                return False
        return True

    def kill_worker(self, worker_id_or_pid: Union[int, str], timeout_s: float = 0.3) -> bool:
        """Forcefully kill a single worker process (SIGKILL)."""
        meta = self.get_worker_metadata(worker_id_or_pid)
        if not meta or not meta.pid:
            return False

        proc = self._workers.get(meta.worker_id)
        if proc and proc.is_alive():
            try:
                proc.kill()
                proc.join(timeout=timeout_s)
                meta.status = WorkerLifecycleStatus.TERMINATED
                meta.end_time = time.time()
                meta.exitcode = proc.exitcode
                return True
            except Exception as e:
                logger.error(f"Error killing worker {meta.worker_id}: {e}")
                return False
        return True

    def terminate_all(
        self,
        coop_timeout: float = COOPERATIVE_TIMEOUT,
        term_timeout: float = SIGTERM_TIMEOUT,
        kill_timeout: float = SIGKILL_TIMEOUT,
    ) -> None:
        """Execute strict 4-stage graceful-to-forceful termination protocol across all workers.

        Protocol:
            1. Cooperative cancellation (signal Event)
            2. Graceful SIGTERM
            3. Forceful SIGKILL
            4. Join and reap zombies
        """
        if not self._workers:
            return

        logger.info(f"Terminating {len(self._workers)} workers...")

        # Stage 1: Cooperative cancellation
        self.cancel_event.set()
        deadline = time.time() + coop_timeout
        for worker in self._workers.values():
            remaining = max(0.02, deadline - time.time())
            worker.join(timeout=remaining)

        alive = [w for w in self._workers.values() if w.is_alive()]
        if not alive:
            logger.info("All workers terminated cooperatively.")
            self._finalize_terminated_workers()
            return

        # Stage 2: Process.terminate() (SIGTERM)
        logger.warning(f"{len(alive)} workers still alive. Escalating to SIGTERM...")
        for worker in alive:
            try:
                worker.terminate()
            except Exception as e:
                logger.error(f"Error terminating worker {worker.pid}: {e}")

        deadline = time.time() + term_timeout
        for worker in alive:
            remaining = max(0.02, deadline - time.time())
            worker.join(timeout=remaining)

        alive = [w for w in self._workers.values() if w.is_alive()]
        if not alive:
            logger.info("All remaining workers terminated via SIGTERM.")
            self._finalize_terminated_workers()
            return

        # Stage 3: Process.kill() (SIGKILL)
        logger.error(f"{len(alive)} workers unresponsive. Escalating to SIGKILL...")
        for worker in alive:
            try:
                worker.kill()
            except Exception as e:
                logger.critical(f"Failed to kill worker {worker.pid}: {e}")

        # Stage 4: Final join to reap zombies
        for worker in alive:
            worker.join(timeout=kill_timeout)

        self._finalize_terminated_workers()
        logger.info("Process pool cleaned up.")

    def _finalize_terminated_workers(self) -> None:
        """Mark terminated workers in local and global registries and clear process handles."""
        now = time.time()
        for worker_id, proc in self._workers.items():
            meta = self._metadata.get(worker_id)
            if meta:
                meta.status = WorkerLifecycleStatus.TERMINATED
                meta.exitcode = proc.exitcode
                if meta.end_time is None:
                    meta.end_time = now

        self._workers.clear()

    # -------------------------------------------------------------------------
    # Orphan Detection & Reaping
    # -------------------------------------------------------------------------
    @classmethod
    def detect_orphans(cls) -> List[int]:
        """Scan operating system for orphaned CoreSync worker processes.

        An orphan is a running process whose commandline or process name identifies it
        as a CoreSync worker ('CoreSync-DP-Worker', 'CoreSync-Task-', 'CoreSync-Stress-')
        but whose parent PID is no longer alive or is not the current application PID.

        CRITICAL: Never detects or flags unrelated user processes!
        """
        orphans: List[int] = []
        my_pid = os.getpid()

        for proc in psutil.process_iter(["pid", "name", "cmdline", "ppid"]):
            try:
                info = proc.info
                pid = info.get("pid")
                if not pid or pid == my_pid:
                    continue

                name = info.get("name") or ""
                cmdline = " ".join(info.get("cmdline") or [])
                ppid = info.get("ppid")

                # Match CoreSync worker signature
                is_coresync_worker = any(
                    sig in name or sig in cmdline
                    for sig in ("CoreSync-DP-Worker", "CoreSync-Task-", "CoreSync-Stress", "coresync_worker")
                )

                if is_coresync_worker:
                    # Check if parent is dead or not us
                    parent_alive = False
                    if ppid and ppid > 0:
                        try:
                            parent_alive = psutil.pid_exists(ppid)
                        except Exception:
                            parent_alive = False

                    if not parent_alive or ppid != my_pid:
                        orphans.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return orphans

    @classmethod
    def reap_orphans(cls, timeout_s: float = 1.0) -> int:
        """Safely terminate and reap any orphaned CoreSync worker processes.

        Returns:
            Number of orphaned processes cleaned up.
        """
        orphans = cls.detect_orphans()
        if not orphans:
            return 0

        logger.warning(f"Reaping {len(orphans)} orphaned CoreSync worker processes: {orphans}")
        reaped_count = 0

        for pid in orphans:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=0.3)
                    reaped_count += 1
                except psutil.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=0.2)
                    reaped_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            except Exception as e:
                logger.error(f"Error reaping orphan PID {pid}: {e}")

        return reaped_count

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate_all()
