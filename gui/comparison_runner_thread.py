"""Background QThread execution coordinator for Real vs Virtual Comparison Workstation."""

import logging
from typing import Any, Callable, Dict, Optional
from PySide6.QtCore import QThread, Signal

from engine.comparison.comparison_runner import ComparisonRunner
from engine.comparison.models import ComparisonConfiguration, ComparisonSessionResult

logger = logging.getLogger("CoreSync.GUI.ComparisonRunnerThread")


class ComparisonRunnerThread(QThread):
    """Executes Real vs Virtual comparisons off the Qt UI thread to maintain full GUI responsiveness."""

    progress_updated = Signal(int, int, str)       # (completed_percent, total, status_message)
    comparison_finished = Signal(object)           # ComparisonSessionResult
    comparison_failed = Signal(str)                # error_message

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self._runner = ComparisonRunner()
        self._config: Optional[ComparisonConfiguration] = None

    def configure(self, config: ComparisonConfiguration) -> None:
        """Set the comparison configuration to be executed."""
        self._config = config

    def cancel_execution(self) -> None:
        """Forward cancellation to running comparison runner."""
        if self._runner:
            self._runner.cancel()

    def run(self) -> None:
        """Thread worker loop executing the comparison session."""
        if not self._config:
            self.comparison_failed.emit("No comparison configuration provided.")
            return

        def _on_progress(completed: int, total: int, msg: str):
            self.progress_updated.emit(completed, total, msg)

        try:
            result = self._runner.run_comparison(
                config=self._config,
                progress_callback=_on_progress,
                save_history=True,
            )
            self.comparison_finished.emit(result)
        except Exception as exc:
            logger.error("Comparison execution thread failed: %s", exc, exc_info=True)
            self.comparison_failed.emit(str(exc))

