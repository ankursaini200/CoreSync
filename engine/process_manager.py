"""Process Manager for CoreSync.

Oversees worker process lifecycles with a strict 4-stage shutdown protocol:
1. Cooperative cancellation (Event.set() / sentinel)
2. Process.terminate() (SIGTERM)
3. Process.kill() (SIGKILL)
4. Process.join() & zombie reclamation
"""

import logging
import multiprocessing as mp
from multiprocessing.process import BaseProcess
import os
import signal
import time
from typing import Dict, List, Optional

from utils.config import (
    COOPERATIVE_TIMEOUT,
    SIGTERM_TIMEOUT,
    SIGKILL_TIMEOUT,
)

logger = logging.getLogger("CoreSync.ProcessManager")


class ProcessManager:
    """Manages worker processes, tracking PIDs and guaranteeing clean termination."""

    def __init__(self, start_method: str = "spawn"):
        self.ctx = mp.get_context(start_method)
        self.workers: Dict[int, BaseProcess] = {}  # worker_id -> Process
        self.cancel_event = self.ctx.Event()

    def register_worker(self, worker_id: int, process: BaseProcess) -> None:
        """Register a spawned worker process."""
        self.workers[worker_id] = process
        logger.debug(f"Registered worker {worker_id} with PID {process.pid}")

    def get_active_pids(self) -> List[int]:
        """Return list of active worker process IDs."""
        return [p.pid for p in self.workers.values() if p.pid is not None and p.is_alive()]

    def terminate_all(
        self,
        coop_timeout: float = COOPERATIVE_TIMEOUT,
        term_timeout: float = SIGTERM_TIMEOUT,
        kill_timeout: float = SIGKILL_TIMEOUT,
    ) -> None:
        """Execute 4-stage graceful-to-forceful termination protocol."""
        if not self.workers:
            return

        logger.info(f"Terminating {len(self.workers)} workers...")

        # Stage 1: Cooperative cancellation
        self.cancel_event.set()
        deadline = time.time() + coop_timeout
        for worker in self.workers.values():
            remaining = max(0.05, deadline - time.time())
            worker.join(timeout=remaining)

        alive = [w for w in self.workers.values() if w.is_alive()]
        if not alive:
            logger.info("All workers terminated cooperatively.")
            self.workers.clear()
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
            remaining = max(0.05, deadline - time.time())
            worker.join(timeout=remaining)

        alive = [w for w in self.workers.values() if w.is_alive()]
        if not alive:
            logger.info("All remaining workers terminated via SIGTERM.")
            self.workers.clear()
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

        self.workers.clear()
        logger.info("Process pool cleaned up.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate_all()

