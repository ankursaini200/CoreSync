"""Modern dark theme stylesheet and color constants for CoreSync."""

from utils.config import (
    COLOR_BG_DARK,
    COLOR_BG_SIDEBAR,
    COLOR_SURFACE_SECONDARY,
    COLOR_SURFACE_ELEVATED,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BG_HOVER,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
)

DARK_STYLESHEET = f"""
/* Global Reset & Base Typography */
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
}}

QWidget {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* Scroll Area & Bars */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_BORDER_LIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {COLOR_BORDER};
    min-width: 24px;
    border-radius: 3px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_BORDER_LIGHT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Top Application Header Bar */
#topHeaderBar {{
    background-color: {COLOR_BG_SIDEBAR};
    border-bottom: 1px solid {COLOR_BORDER};
    min-height: 54px;
    max-height: 54px;
}}

#pageTitle {{
    font-size: 15px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

#pageBreadcrumb {{
    font-size: 11px;
    color: {COLOR_TEXT_MUTED};
}}

QLabel.tag-pill {{
    background-color: {COLOR_SURFACE_SECONDARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 4px 12px;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 11px;
    font-weight: 600;
}}

/* Sidebar Navigation */
#sidebar {{
    background-color: {COLOR_BG_SIDEBAR};
    border-right: 1px solid {COLOR_BORDER};
    min-width: 260px;
    max-width: 280px;
}}

#sidebarNavScroll {{
    background: transparent;
    border: none;
}}

#sidebarNavScroll QWidget {{
    background: transparent;
}}

#sidebarNavScroll QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 0px;
}}

#sidebarNavScroll QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 24px;
    border-radius: 2px;
}}

#sidebarNavScroll QScrollBar::handle:vertical:hover {{
    background: {COLOR_BORDER_LIGHT};
}}

#appBrand {{
    font-size: 18px;
    font-weight: 800;
    color: {COLOR_TEXT_PRIMARY};
    letter-spacing: 0.5px;
    padding: 16px 14px 2px 14px;
}}

#appSubtitle {{
    font-size: 11px;
    font-weight: 500;
    color: {COLOR_TEXT_MUTED};
    padding: 0px 14px 14px 14px;
}}

QLabel.nav-category {{
    font-size: 10px;
    font-weight: 700;
    color: {COLOR_TEXT_MUTED};
    text-transform: uppercase;
    letter-spacing: 1.2px;
    padding: 12px 14px 4px 14px;
}}

/* Workstation Status Card */
#sidebarStatusCard {{
    background-color: {COLOR_SURFACE_SECONDARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
}}

#sidebarStatusCard:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QPushButton.nav-button {{
    background-color: transparent;
    color: {COLOR_TEXT_MUTED};
    border: none;
    border-radius: 5px;
    padding: 8px 12px;
    text-align: left;
    font-weight: 500;
    margin: 1px 6px;
}}

QPushButton.nav-button:hover {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_TEXT_PRIMARY};
}}

QPushButton.nav-button:checked {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 600;
    border-left: 3px solid {COLOR_ACCENT};
}}

/* Content Container & Cards */
QFrame.card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
}}

QFrame.card:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QFrame.card-alt {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 14px 16px;
}}

/* Typography Hierarchy */
QLabel.heading-1 {{
    font-size: 18px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.heading-2 {{
    font-size: 14px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.heading-3 {{
    font-size: 12px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.muted {{
    color: {COLOR_TEXT_MUTED};
    font-size: 11px;
}}

QLabel.metric-value {{
    font-size: 20px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.metric-label {{
    color: {COLOR_TEXT_MUTED};
    font-size: 12px;
    font-weight: 500;
}}

QLabel.tag-pill {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_MUTED};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 500;
}}

/* Form Controls & Inputs */
QComboBox {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 5px 10px;
    color: {COLOR_TEXT_PRIMARY};
    min-width: 130px;
}}

QComboBox:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    selection-background-color: {COLOR_BG_HOVER};
    color: {COLOR_TEXT_PRIMARY};
    outline: none;
}}

QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 5px 8px;
    color: {COLOR_TEXT_PRIMARY};
}}

QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {{
    border: 1px solid {COLOR_ACCENT};
}}

/* Buttons */
QPushButton.btn-primary {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton.btn-primary:hover {{
    background-color: {COLOR_ACCENT_HOVER};
}}

QPushButton.btn-primary:pressed {{
    background-color: #3B7BB5;
}}

QPushButton.btn-secondary {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 500;
    font-size: 12px;
}}

QPushButton.btn-secondary:hover {{
    background-color: {COLOR_BG_HOVER};
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QPushButton.btn-danger {{
    background-color: {COLOR_DANGER};
    color: #ffffff;
    border: none;
    border-radius: 5px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}}

QPushButton.btn-danger:hover {{
    background-color: #D97373;
}}

/* Tables */
QTableWidget {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    gridline-color: {COLOR_BORDER};
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_BG_HOVER};
    selection-color: {COLOR_TEXT_PRIMARY};
}}

QHeaderView::section {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {COLOR_BORDER};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
}}

/* Progress Bars */
QProgressBar {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    text-align: center;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 500;
    max-height: 10px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 2px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLOR_BG_SIDEBAR};
    color: {COLOR_TEXT_MUTED};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 11px;
    padding: 4px 10px;
}}
"""
