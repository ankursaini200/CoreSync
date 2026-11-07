"""Comparison Execution Runner and Coordinator for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Coordinates sequential execution of Real System and Virtual Lab environments, guarantees
input isolation via deep cloning, handles cooperative cancellation, and packages results.
"""

from datetime import datetime, timezone
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from engine.analytics.benchmarking import get_sanitized_hardware_metadata
from engine.analytics.history import BenchmarkHistoryManager
from engine.comparison.comparison_metrics import compute_comparison_analysis
from engine.comparison.comparison_validator import (
    assert_valid_configuration,
    validate_result_isolation,
)
from engine.comparison.models import (
    ComparisonAnalysis,
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonSessionResult,
    RealExecutionResult,
    VirtualExecutionResult,
)
from engine.comparison.real_executor import RealComparisonExecutor
from engine.comparison.virtual_executor import VirtualComparisonExecutor
from engine.process_manager import ProcessManager

logger = logging.getLogger("CoreSync.Comparison.Runner")


class ComparisonRunner:
    """Coordinates comparative workload execution across Real System and Virtual Lab."""

    def __init__(self, history_manager: Optional[BenchmarkHistoryManager] = None):
        self._real_executor = RealComparisonExecutor()
        self._virtual_executor = VirtualComparisonExecutor()
        self._history_manager = history_manager or BenchmarkHistoryManager()
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._is_running = False

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def cancel(self) -> None:
        """Signal cooperative cancellation to running executors."""
        logger.info("Cancellation requested for ComparisonRunner.")
        self._cancel_event.set()
        # Cooperatively abort active real processes
        self._real_executor._dp_executor.cancel_active_execution()
        self._real_executor._tp_executor.cancel_active_execution()

    def run_comparison(
        self,
        config: ComparisonConfiguration,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        save_history: bool = True,
    ) -> ComparisonSessionResult:
        """Execute the comparison session according to the requested configuration.

        In Compare Both mode, executes sequentially (Real System first, then Virtual Lab)
        to prevent virtual simulation CPU overhead from distorting host measurements.

        Args:
            config: Validated comparison configuration.
            progress_callback: Optional progress reporter (completed, total, message).
            save_history: Whether to persist the session JSON record to disk.

        Returns:
            ComparisonSessionResult with all telemetry, analysis, and metadata.
        """
        assert_valid_configuration(config)

        with self._lock:
            if self._is_running:
                raise RuntimeError("ComparisonRunner is already executing an active session.")
            if self._cancel_event.is_set():
                self._cancel_event.clear()
                return ComparisonSessionResult(
                    comparison_id=config.comparison_id,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    configuration=config,
                    real_result=None,
                    virtual_result=None,
                    analysis=None,
                    hardware_metadata=get_sanitized_hardware_metadata(),
                    success=False,
                    cancelled=True,
                    error_message="Comparison was cancelled before execution started.",
                )
            self._is_running = True

        real_res: Optional[RealExecutionResult] = None
        virtual_res: Optional[VirtualExecutionResult] = None
        session_success = True
        session_error: Optional[str] = None

        try:
            mode = config.execution_mode

            # -------------------------------------------------------------
            # 1. Real System Execution Pass
            # -------------------------------------------------------------
            if mode in (ComparisonExecutionMode.REAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
                if progress_callback:
                    progress_callback(0, 100, "Starting Real System execution...")

                def _real_prog(c: int, t: int, m: str):
                    if progress_callback:
                        pct = int((c / max(1, t)) * 50) if mode == ComparisonExecutionMode.COMPARE_BOTH else int((c / max(1, t)) * 100)
                        progress_callback(pct, 100, f"[Real System] {m}")

                real_res = self._real_executor.execute(
                    workload_config=config.workload,
                    real_config=config.real_config,
                    progress_callback=_real_prog,
                    cancel_event=self._cancel_event,
                )

                if real_res.status == "failed":
                    session_success = False
                    session_error = f"Real System error: {real_res.error_message}"
                elif real_res.status == "cancelled":
                    session_error = "Real System was cancelled."

            # -------------------------------------------------------------
            # 2. Virtual Lab Simulation Pass
            # -------------------------------------------------------------
            if mode in (ComparisonExecutionMode.VIRTUAL_ONLY, ComparisonExecutionMode.COMPARE_BOTH):
                if self._cancel_event.is_set():
                    virtual_res = VirtualExecutionResult(
                        status="cancelled",
                        virtual_makespan_ticks=0,
                        simulated_clock_ticks=0,
                        virtual_core_utilization_pct=0.0,
                        virtual_core_count=config.virtual_config.virtual_core_count,
                        error_message="Simulation skipped due to cancellation.",
                    )
                else:
                    if progress_callback:
                        start_pct = 50 if mode == ComparisonExecutionMode.COMPARE_BOTH else 0
                        progress_callback(start_pct, 100, "Starting Virtual Lab simulation...")

                    def _virt_prog(c: int, t: int, m: str):
                        if progress_callback:
                            base = 50 if mode == ComparisonExecutionMode.COMPARE_BOTH else 0
                            span = 50 if mode == ComparisonExecutionMode.COMPARE_BOTH else 100
                            pct = base + int((c / max(1, t)) * span)
                            progress_callback(pct, 100, f"[Virtual Lab] {m}")

                    virtual_res = self._virtual_executor.execute(
                        workload_config=config.workload,
                        virtual_config=config.virtual_config,
                        progress_callback=_virt_prog,
                        cancel_event=self._cancel_event,
                    )

                    if virtual_res.status == "failed":
                        session_success = False
                        session_error = f"Virtual Lab error: {virtual_res.error_message}"

            # -------------------------------------------------------------
            # 3. Comparative Evaluation & Provenance Compilation
            # -------------------------------------------------------------
            analysis = compute_comparison_analysis(
                config=config,
                real_result=real_res,
                virtual_result=virtual_res,
            )

            # Audit isolation
            isolated, iso_msg = validate_result_isolation(real_res, virtual_res)
            if not isolated:
                logger.warning("Isolation check warning: %s", iso_msg)

            hw_metadata = get_sanitized_hardware_metadata()

            session = ComparisonSessionResult(
                comparison_id=config.comparison_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                configuration=config,
                real_result=real_res,
                virtual_result=virtual_res,
                analysis=analysis,
                hardware_metadata=hw_metadata,
                success=session_success,
                cancelled=self._cancel_event.is_set(),
                error_message=session_error,
            )

            # -------------------------------------------------------------
            # 4. History Persistence
            # -------------------------------------------------------------
            if save_history:
                try:
                    self._save_session_to_history(session)
                except Exception as hist_err:
                    logger.error("Failed to save comparison to history: %s", hist_err)

            if progress_callback:
                progress_callback(100, 100, "Comparison session complete.")

            return session

        finally:
            with self._lock:
                self._is_running = False
                self._cancel_event.clear()
            # Assure clean shutdown of any lingering processes
            self._real_executor.cleanup()

    def _save_session_to_history(self, session: ComparisonSessionResult) -> None:
        """Persist comparison record using BenchmarkHistoryManager storage."""
        storage_dir = self._history_manager.storage_dir
        storage_dir.mkdir(parents=True, exist_ok=True)

        target_file = storage_dir / f"{session.comparison_id}.json"
        import json
        payload = session.to_dict()
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("Saved comparison record: %s", target_file)
