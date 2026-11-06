"""Background QThread execution coordinator for Data Parallelism benchmarks."""

import logging
import multiprocessing as mp
import time
from typing import Any, Optional
from PySide6.QtCore import QThread, Signal

from engine.affinity import AffinityPolicy
from engine.data_parallel.executor import (
    DataParallelBenchmarkResult,
    DataParallelExecutor,
)
from engine.data_parallel.operations import generate_dataset
from utils.cpu_topology import CPUTopology

logger = logging.getLogger("CoreSync.GUI.DataParallelRunner")


class DataParallelRunnerThread(QThread):
    """Executes CPU-bound data parallelism benchmarks in a background thread."""

    progress_updated = Signal(int, int, str)       # (completed_chunks, total_chunks, status_msg)
    benchmark_finished = Signal(object)           # DataParallelBenchmarkResult
    benchmark_failed = Signal(str)

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._op_id: str = "transcendental"
        self._dataset_size: int = 1_000_000
        self._worker_count: int = 4
        self._seed: int = 42
        self._warm_up: bool = False
        self._affinity_policy: AffinityPolicy = AffinityPolicy.AUTOMATIC
        self._custom_cpus: Optional[list] = None
        self._topology: Optional[CPUTopology] = None
        self._cancel_event = mp.get_context("spawn").Event()
        self._executor = DataParallelExecutor()

    def configure(
        self,
        op_id: str,
        dataset_size: int,
        worker_count: int,
        seed: int = 42,
        warm_up: bool = False,
        affinity_policy: AffinityPolicy = AffinityPolicy.AUTOMATIC,
        custom_cpus: Optional[list] = None,
        topology: Optional[CPUTopology] = None,
    ) -> None:
        """Set benchmark parameters before starting thread."""
        self._op_id = op_id
        self._dataset_size = dataset_size
        self._worker_count = worker_count
        self._seed = seed
        self._warm_up = warm_up
        self._affinity_policy = affinity_policy
        self._custom_cpus = custom_cpus
        self._topology = topology
        self._cancel_event.clear()

    def cancel(self) -> None:
        """Signal cooperative cancellation to running workers and executor."""
        self._cancel_event.set()
        self._executor.cancel_active_execution()

    def run(self) -> None:
        """Generate dataset and execute full benchmark in background thread."""
        try:
            self.progress_updated.emit(0, self._worker_count, f"Generating {self._dataset_size:,} item dataset...")
            data = generate_dataset(self._op_id, self._dataset_size, seed=self._seed)

            if self._cancel_event.is_set():
                self.benchmark_failed.emit("Benchmark cancelled before start.")
                return

            def on_progress(completed: int, total: int, msg: str):
                self.progress_updated.emit(completed, total, msg)

            result = self._executor.run_benchmark(
                op_id=self._op_id,
                data=data,
                worker_count=self._worker_count,
                progress_callback=on_progress,
                cancel_event=self._cancel_event,
                warm_up=self._warm_up,
                affinity_policy=self._affinity_policy,
                custom_cpus=self._custom_cpus,
                topology=self._topology,
            )

            if self._cancel_event.is_set():
                self.benchmark_failed.emit("Benchmark was cancelled.")
            else:
                self.benchmark_finished.emit(result)

        except Exception as e:
            logger.error(f"Error in data parallel runner thread: {e}", exc_info=True)
            self.benchmark_failed.emit(f"Execution Error: {str(e)}")

