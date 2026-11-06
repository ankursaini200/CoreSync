"""Reusable Metric Card widget for CoreSync."""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from utils.config import (
    COLOR_BG_CARD,
    COLOR_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
)
from gui.components.badge import StatusBadge


class MetricCard(QFrame):
    """Modern dark metric card with title, status pill, primary value, and subtitle."""

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
        self.setMinimumWidth(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header: Title & Optional Badge
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title, self)
        self.title_label.setProperty("class", "heading-3")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        self.badge: Optional[StatusBadge] = None
        if status_text:
            self.badge = StatusBadge(status_text, status_theme, self)
            header_layout.addWidget(self.badge)

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
        """Update or set the badge status."""
        if self.badge:
            self.badge.set_status(text, theme)

