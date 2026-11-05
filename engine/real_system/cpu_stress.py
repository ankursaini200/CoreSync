"""Real CPU Stress Generator for CoreSync.

Spawns genuine CPU-bound worker processes under the 'spawn' context with strict
safety limits, configurable worker counts, duration caps, and immediate cancellation.
"""

from dataclasses import dataclass
import logging
import math
import multiprocessing as mp
from multiprocessing.process import BaseProcess
from multiprocessing.synchronize import Event as EventType
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger("CoreSync.CPUStress")

# Maximum permitted stress duration for safety (seconds)
MAX_STRESS_DURATION_S = 30.0
DEFAULT_STRESS_DURATION_S = 5.0


def stress_worker_loop(
    worker_id: int,
    stop_event: EventType,
    duration_s: float,
    intensity_pct: float,
) -> None:
    """CPU-bound stress loop executing mathematical floating-point operations.

    CRITICAL: Strictly isolated from PySide6 and Qt!
    """
    start_time = time.time()
    duty_cycle = max(0.1, min(intensity_pct / 100.0, 1.0))
    chunk_window = 0.1  # 100ms window
    work_time = chunk_window * duty_cycle
    sleep_time = chunk_window * (1.0 - duty_cycle)

    while not stop_event.is_set():
        if time.time() - start_time >= duration_s:
            break

        # Busy compute phase
        w_start = time.time()
        while time.time() - w_start < work_time and not stop_event.is_set():
            # Heavy mathematical loop (trig and floating-point square root)
            for x in range(1, 1000):
                _ = math.sin(x) * math.cos(x) + math.sqrt(x)

        # Rest phase if intensity < 100%
        if sleep_time > 0 and not stop_event.is_set():
            time.sleep(sleep_time)


@dataclass
class StressStatus:
    """Current state of real CPU stress generation."""
    is_running: bool
    workers_active: int
    elapsed_s: float
    target_duration_s: float
    intensity_pct: float
    worker_pids: List[int]


class RealCPUStressGenerator:
    """Manages spawning, monitoring, and guaranteed termination of real CPU stress workers."""

    def __init__(self):
        self._ctx = mp.get_context("spawn")
        self._stop_event = self._ctx.Event()
        self._workers: Dict[int, BaseProcess] = {}
        self._start_time: float = 0.0
        self._duration_s: float = DEFAULT_STRESS_DURATION_S
        self._intensity_pct: float = 100.0

    def is_running(self) -> bool:
        """Return True if any stress worker process is still alive."""
        return any(w.is_alive() for w in self._workers.values())

    def start_stress(
        self,
        worker_count: int,
        duration_s: float = DEFAULT_STRESS_DURATION_S,
        intensity_pct: float = 100.0,
    ) -> bool:
        """Start genuine CPU-bound worker processes.

        Args:
            worker_count: Number of processes to spawn (clamped to 1..64).
            duration_s: Runtime in seconds (clamped to 1.0..MAX_STRESS_DURATION_S).
            intensity_pct: Workload intensity percentage (10% to 100%).

        Returns:
            True if stress successfully started, False if already running.
        """
        if self.is_running():
            logger.warning("CPU stress already running.")
            return False

        self.stop_stress()  # Clean up any lingering process handles

        # Apply conservative safety limits
        worker_count = max(1, min(worker_count, 64))
        self._duration_s = max(1.0, min(duration_s, MAX_STRESS_DURATION_S))
        self._intensity_pct = max(10.0, min(intensity_pct, 100.0))

        self._stop_event.clear()
        self._start_time = time.time()
        self._workers.clear()

        logger.info(f"Starting Real CPU Stress: {worker_count} workers, {self._duration_s}s, {self._intensity_pct}% intensity")

        for i in range(worker_count):
            p = self._ctx.Process(
                target=stress_worker_loop,
                args=(i, self._stop_event, self._duration_s, self._intensity_pct),
                name=f"CoreSync-Stress-{i}",
            )
            p.daemon = True
            p.start()
            self._workers[i] = p

        return True

    def stop_stress(self, timeout_s: float = 1.5) -> None:
        """Immediately cancel and terminate all stress worker processes."""
        if not self._workers:
            return

        logger.info(f"Stopping {len(self._workers)} CPU stress workers...")

        # Stage 1: Cooperative cancellation signal
        self._stop_event.set()
        deadline = time.time() + min(0.5, timeout_s)
        for p in self._workers.values():
            rem = max(0.01, deadline - time.time())
            p.join(timeout=rem)

        # Stage 2: SIGTERM for any still alive
        alive = [p for p in self._workers.values() if p.is_alive()]
        if alive:
            logger.warning(f"Terminating {len(alive)} uncooperative stress workers...")
            for p in alive:
                try:
                    p.terminate()
                except Exception:
                    pass
            for p in alive:
                p.join(timeout=0.3)

        # Stage 3: Forceful SIGKILL fallback
        alive = [p for p in self._workers.values() if p.is_alive()]
        if alive:
            logger.error(f"Killing {len(alive)} unresponsive stress workers...")
            for p in alive:
                try:
                    p.kill()
                except Exception:
                    pass
            for p in alive:
                p.join(timeout=0.2)

        self._workers.clear()
        logger.info("All CPU stress workers cleaned up.")

    def get_status(self) -> StressStatus:
        """Return current status snapshot of CPU stress generation."""
        alive_workers = [p for p in self._workers.values() if p.is_alive()]
        elapsed = time.time() - self._start_time if self._start_time > 0 else 0.0

        # Auto-detect completion
        if self._workers and not alive_workers:
            self._workers.clear()

        return StressStatus(
            is_running=bool(alive_workers),
            workers_active=len(alive_workers),
            elapsed_s=min(elapsed, self._duration_s),
            target_duration_s=self._duration_s,
            intensity_pct=self._intensity_pct,
            worker_pids=[p.pid for p in alive_workers if p.pid is not None],
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_stress()

