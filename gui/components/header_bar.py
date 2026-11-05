"""Top workstation application header bar for CoreSync."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from utils.config import APP_NAME
from gui.components.badge import StatusBadge


class HeaderBar(QFrame):
    """Header bar displaying dynamic breadcrumbs, section title, and system status tags."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("topHeaderBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(16)

        # Left: Breadcrumb & Title
        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        title_container.setAlignment(Qt.AlignVCenter)

        self.breadcrumb_label = QLabel(f"{APP_NAME} / Dashboard", self)
        self.breadcrumb_label.setObjectName("pageBreadcrumb")
        title_container.addWidget(self.breadcrumb_label)

        self.title_label = QLabel("Dashboard Overview", self)
        self.title_label.setObjectName("pageTitle")
        title_container.addWidget(self.title_label)

        layout.addLayout(title_container)
        layout.addStretch(1)

        # Right: System Status & Hardware Tag Pills
        self.hardware_pill = QLabel("14 Cores / 20 Threads", self)
        self.hardware_pill.setProperty("class", "tag-pill")
        layout.addWidget(self.hardware_pill)

        self.engine_status = StatusBadge("Engine Ready (spawn)", "success", self)
        layout.addWidget(self.engine_status)

    def update_header(self, section_name: str, subtitle: str = "") -> None:
        """Update header title and breadcrumb path."""
        self.breadcrumb_label.setText(f"{APP_NAME} / {section_name}")
        self.title_label.setText(subtitle or section_name)

