"""Background QThread execution coordinator for Performance Analytics Benchmarking."""

import logging
from typing import Any, Callable, Dict, Optional
from PySide6.QtCore import QThread, Signal

from engine.analytics.benchmarking import (
    BenchmarkingEngine,
    BenchmarkEngineType,
    BenchmarkSessionResult,
)

logger = logging.getLogger("CoreSync.GUI.AnalyticsRunner")


class AnalyticsBenchmarkRunnerThread(QThread):
    """Executes multi-run performance benchmarks off the UI thread to prevent interface freezing."""

    progress_updated = Signal(int, int, str)       # (current_pass, total_passes, status_message)
    benchmark_finished = Signal(object)           # BenchmarkSessionResult
    benchmark_failed = Signal(str)                # error_message

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._engine = BenchmarkingEngine()
        self._target_engine_type: Optional[BenchmarkEngineType] = None
        self._kwargs: Dict[str, Any] = {}

    def configure_data_parallel(
        self,
        op_id: str,
        dataset_size: int,
        worker_count: int,
        iterations: int = 3,
        warmup_runs: int = 1,
    ) -> None:
        self._target_engine_type = BenchmarkEngineType.DATA_PARALLEL
        self._kwargs = {
            "op_id": op_id,
            "dataset_size": dataset_size,
            "worker_count": worker_count,
            "iterations": iterations,
            "warmup_runs": warmup_runs,
        }
        self._engine.reset_cancellation()

    def configure_task_parallel(
        self,
        dag_type: str,
        worker_count: int,
        iterations: int = 3,
        warmup_runs: int = 1,
    ) -> None:
        self._target_engine_type = BenchmarkEngineType.TASK_PARALLEL
        self._kwargs = {
            "dag_type": dag_type,
            "worker_count": worker_count,
            "iterations": iterations,
            "warmup_runs": warmup_runs,
        }
        self._engine.reset_cancellation()

    def configure_scheduling(
        self,
        preset_id: str,
        time_quantum: float = 2.0,
        context_switch_overhead: float = 0.1,
    ) -> None:
        self._target_engine_type = BenchmarkEngineType.CPU_SCHEDULING
        self._kwargs = {
            "preset_id": preset_id,
            "time_quantum": time_quantum,
            "context_switch_overhead": context_switch_overhead,
        }
        self._engine.reset_cancellation()

    def configure_virtual_lab(
        self,
        virtual_cores: int,
        task_count: int,
        enable_hybrid: bool = False,
    ) -> None:
        self._target_engine_type = BenchmarkEngineType.VIRTUAL_LAB
        self._kwargs = {
            "virtual_cores": virtual_cores,
            "task_count": task_count,
            "enable_hybrid": enable_hybrid,
        }
        self._engine.reset_cancellation()

    def cancel(self) -> None:
        """Cooperatively cancel running benchmark."""
        self._engine.cancel()

    def run(self) -> None:
        """Run benchmark sweep in background thread."""
        if not self._target_engine_type:
            self.benchmark_failed.emit("No benchmark configured.")
            return

        def on_progress(cur: int, tot: int, msg: str):
            self.progress_updated.emit(cur, tot, msg)

        try:
            if self._target_engine_type == BenchmarkEngineType.DATA_PARALLEL:
                res = self._engine.run_data_parallel_benchmark(
                    op_id=self._kwargs["op_id"],
                    dataset_size=self._kwargs["dataset_size"],
                    worker_count=self._kwargs["worker_count"],
                    iterations=self._kwargs["iterations"],
                    warmup_runs=self._kwargs["warmup_runs"],
                    progress_cb=on_progress,
                )
            elif self._target_engine_type == BenchmarkEngineType.TASK_PARALLEL:
                res = self._engine.run_task_parallel_benchmark(
                    dag_type=self._kwargs["dag_type"],
                    worker_count=self._kwargs["worker_count"],
                    iterations=self._kwargs["iterations"],
                    warmup_runs=self._kwargs["warmup_runs"],
                    progress_cb=on_progress,
                )
            elif self._target_engine_type == BenchmarkEngineType.CPU_SCHEDULING:
                res = self._engine.run_scheduling_benchmark(
                    preset_id=self._kwargs["preset_id"],
                    time_quantum=self._kwargs["time_quantum"],
                    context_switch_overhead=self._kwargs["context_switch_overhead"],
                )
            elif self._target_engine_type == BenchmarkEngineType.VIRTUAL_LAB:
                res = self._engine.run_virtual_lab_benchmark(
                    virtual_cores=self._kwargs["virtual_cores"],
                    task_count=self._kwargs["task_count"],
                    enable_hybrid=self._kwargs["enable_hybrid"],
                )
            else:
                self.benchmark_failed.emit(f"Unknown engine type: {self._target_engine_type}")
                return

            self.benchmark_finished.emit(res)

        except Exception as e:
            logger.exception("Benchmark execution failed in background thread")
            self.benchmark_failed.emit(str(e))

