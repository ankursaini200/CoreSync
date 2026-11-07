"""Reusable Metric Card widget for CoreSync."""

from typing import Optional, Set
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.config import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)

# Unnecessary decorative or promotional labels to suppress across metric cards
DECORATIVE_STATUS_LABELS: Set[str] = {
    "loaded", "idle", "pending", "none", "baseline", "parallel", "total work",
    "optimal", "overhead bound", "calculated", "peak", "sub-linear", "no baseline",
    "verified", "verified math", "verified match", "live sampler", "psutil",
    "amdahl model", "amdahl limit", "serial constraint", "clean", "cleaned",
    "config active", "engine active", "speedup achieved",
}


class _MetricStatusProxy:
    """Subtle text proxy preserving the .set_status() interface without decorative badge pills."""

    def __init__(self, label: QLabel):
        self._label = label

    @property
    def label(self) -> QLabel:
        return self._label

    def set_status(self, text: str, theme: str = "neutral") -> None:
        if not text or text.strip().lower() in DECORATIVE_STATUS_LABELS:
            self._label.setText("")
            self._label.setVisible(False)
            return

        self._label.setText(text)
        self._label.setVisible(True)

    def setVisible(self, visible: bool) -> None:
        self._label.setVisible(visible)

    def isVisible(self) -> bool:
        return self._label.isVisible()


class MetricCard(QFrame):
    """Clean, professional metric card with title, primary numerical value, and context subtitle."""

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str = "",
        status_text: Optional[str] = None,
        status_theme: str = "neutral",
        show_progress: bool = False,
        progress_val: int = 0,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumWidth(110)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header: Title & Optional Subtle Status Label
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self.title_label = QLabel(title, self)
        self.title_label.setProperty("class", "heading-3")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("color: #9AA5B4; font-size: 11px; font-weight: 500;")
        header_layout.addWidget(self.status_label)

        self.badge = _MetricStatusProxy(self.status_label)
        if status_text:
            self.badge.set_status(status_text, status_theme)
        else:
            self.status_label.setVisible(False)

        layout.addLayout(header_layout)

        # Main Metric Value
        self.value_label = QLabel(value, self)
        self.value_label.setProperty("class", "metric-value")
        layout.addWidget(self.value_label)

        # Optional Progress Bar
        self.progress_bar: Optional[QProgressBar] = None
        if show_progress:
            self.progress_bar = QProgressBar(self)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(progress_val)
            layout.addWidget(self.progress_bar)

        # Subtitle / Context description
        self.subtitle_label = QLabel(subtitle, self)
        self.subtitle_label.setProperty("class", "muted")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

    def set_value(
        self,
        value: str,
        subtitle: Optional[str] = None,
        theme: Optional[str] = None,
        status_text: Optional[str] = None,
    ) -> None:
        """Update the primary metric string and optionally subtitle and status."""
        self.value_label.setText(value)
        if subtitle is not None:
            self.set_subtitle(subtitle)
        if status_text is not None:
            self.set_status(status_text, theme or "neutral")

    def set_subtitle(self, subtitle: str) -> None:
        """Update the context subtitle."""
        self.subtitle_label.setText(subtitle)

    def set_status(self, text: str, theme: str = "neutral") -> None:
        """Update or set the subtle status text."""
        self.badge.set_status(text, theme)
