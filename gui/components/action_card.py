"""Reusable Action & Navigation Card component for CoreSync."""

from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.config import COLOR_TEXT_MUTED
from gui.components.badge import StatusBadge


class ActionCard(QFrame):
    """Clickable workstation card for launching modules or viewing details."""

    clicked = Signal()

    def __init__(
        self,
        title: str,
        description: str,
        button_text: str = "Open →",
        badge_text: Optional[str] = None,
        badge_theme: str = "neutral",
        on_click: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setProperty("class", "card")
        self.setMinimumHeight(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title, self)
        self.title_label.setProperty("class", "heading-2")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)

        if badge_text:
            self.badge = StatusBadge(badge_text, badge_theme, self)
            header_layout.addWidget(self.badge)

        layout.addLayout(header_layout)

        # Description
        self.desc_label = QLabel(description, self)
        self.desc_label.setProperty("class", "muted")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        layout.addStretch(1)

        # Footer Button
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)

        self.btn = QPushButton(button_text, self)
        self.btn.setProperty("class", "btn-secondary")
        if on_click:
            self.btn.clicked.connect(on_click)
        self.btn.clicked.connect(self.clicked.emit)
        footer_layout.addWidget(self.btn)

        layout.addLayout(footer_layout)

