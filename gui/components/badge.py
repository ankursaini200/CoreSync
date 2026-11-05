"""Status badge and indicator pill component for CoreSync."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from utils.config import (
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_ACCENT,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
)


class StatusBadge(QFrame):
    """Sleek status pill with a colored circular dot and text label."""

    THEMES = {
        "success": (COLOR_SUCCESS, "rgba(63, 185, 80, 0.15)"),
        "warning": (COLOR_WARNING, "rgba(210, 153, 34, 0.15)"),
        "danger": (COLOR_DANGER, "rgba(248, 81, 73, 0.15)"),
        "info": (COLOR_ACCENT, "rgba(88, 166, 255, 0.15)"),
        "neutral": (COLOR_TEXT_MUTED, "rgba(139, 148, 158, 0.12)"),
    }

    def __init__(self, text: str, theme: str = "neutral", parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self._theme = theme

        dot_color, bg_color = self.THEMES.get(theme, self.THEMES["neutral"])

        self.setStyleSheet(f"""
            QFrame#statusBadge {{
                background-color: {bg_color};
                border: 1px solid {dot_color};
                border-radius: 11px;
                padding: 1px 8px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Dot indicator
        self.dot = QLabel("●", self)
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 8px; background: transparent;")
        layout.addWidget(self.dot)

        # Text label
        self.label = QLabel(text, self)
        self.label.setStyleSheet(f"color: {dot_color}; font-size: 11px; font-weight: 600; background: transparent;")
        layout.addWidget(self.label)

    def set_status(self, text: str, theme: str = "neutral") -> None:
        """Update badge text and theme dynamically."""
        self._theme = theme
        dot_color, bg_color = self.THEMES.get(theme, self.THEMES["neutral"])
        self.setStyleSheet(f"""
            QFrame#statusBadge {{
                background-color: {bg_color};
                border: 1px solid {dot_color};
                border-radius: 11px;
                padding: 1px 8px;
            }}
        """)
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 8px; background: transparent;")
        self.label.setStyleSheet(f"color: {dot_color}; font-size: 11px; font-weight: 600; background: transparent;")
        self.label.setText(text)

