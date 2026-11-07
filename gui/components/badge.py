"""Status badge and indicator component for CoreSync."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from utils.config import (
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_BG_CARD_ALT,
    COLOR_BORDER,
)


class StatusBadge(QFrame):
    """Restrained, professional status indicator with subtle dot and clear label."""

    THEMES = {
        "success": COLOR_SUCCESS,
        "warning": COLOR_WARNING,
        "danger": COLOR_DANGER,
        "info": COLOR_ACCENT,
        "neutral": COLOR_TEXT_MUTED,
    }

    def __init__(self, text: str, theme: str = "neutral", parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self._theme = theme

        dot_color = self.THEMES.get(theme, self.THEMES["neutral"])

        self.setStyleSheet(f"""
            QFrame#statusBadge {{
                background-color: {COLOR_BG_CARD_ALT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 1px 6px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(5)

        # Dot indicator
        self.dot = QLabel("●", self)
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 7px; background: transparent;")
        layout.addWidget(self.dot)

        # Text label
        self.label = QLabel(text, self)
        self.label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: 500; background: transparent;")
        layout.addWidget(self.label)

    def set_status(self, text: str, theme: str = "neutral") -> None:
        """Update badge text and theme dynamically."""
        self._theme = theme
        dot_color = self.THEMES.get(theme, self.THEMES["neutral"])
        self.setStyleSheet(f"""
            QFrame#statusBadge {{
                background-color: {COLOR_BG_CARD_ALT};
                border: 1px solid {COLOR_BORDER};
                border-radius: 4px;
                padding: 1px 6px;
            }}
        """)
        self.dot.setStyleSheet(f"color: {dot_color}; font-size: 7px; background: transparent;")
        self.label.setText(text)
