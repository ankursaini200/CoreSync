"""Modern dark theme stylesheet and color constants for CoreSync."""

from utils.config import (
    COLOR_BG_DARK,
    COLOR_BG_SIDEBAR,
    COLOR_BG_CARD,
    COLOR_BG_CARD_ALT,
    COLOR_BG_HOVER,
    COLOR_BORDER,
    COLOR_BORDER_LIGHT,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_TEXT_PRIMARY,
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
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* Scroll Area & Bars */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 24px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_BORDER_LIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Top Application Header Bar */
#topHeaderBar {{
    background-color: {COLOR_BG_SIDEBAR};
    border-bottom: 1px solid {COLOR_BORDER};
    min-height: 52px;
    max-height: 52px;
}}

#pageTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

#pageBreadcrumb {{
    font-size: 12px;
    color: {COLOR_TEXT_MUTED};
}}

/* Sidebar Navigation */
#sidebar {{
    background-color: {COLOR_BG_SIDEBAR};
    border-right: 1px solid {COLOR_BORDER};
    min-width: 230px;
    max-width: 250px;
}}

#appBrand {{
    font-size: 19px;
    font-weight: 800;
    color: {COLOR_ACCENT};
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
    letter-spacing: 1px;
    padding: 12px 14px 4px 14px;
}}

QPushButton.nav-button {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 9px 12px;
    text-align: left;
    font-weight: 500;
    margin: 1px 6px;
}}

QPushButton.nav-button:hover {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_ACCENT_HOVER};
}}

QPushButton.nav-button:checked {{
    background-color: #1a2233;
    color: {COLOR_ACCENT};
    font-weight: 600;
    border-left: 3px solid {COLOR_ACCENT};
}}

/* Content Container & Cards */
QFrame.card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 16px;
}}

QFrame.card:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QFrame.card-alt {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    padding: 16px;
}}

/* Typography Hierarchy */
QLabel.heading-1 {{
    font-size: 20px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.heading-2 {{
    font-size: 15px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.heading-3 {{
    font-size: 13px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.muted {{
    color: {COLOR_TEXT_MUTED};
    font-size: 12px;
}}

QLabel.metric-value {{
    font-size: 22px;
    font-weight: 700;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.tag-pill {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_ACCENT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}}

/* Form Controls & Inputs */
QComboBox {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLOR_TEXT_PRIMARY};
    min-width: 140px;
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

QSpinBox, QLineEdit {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    color: {COLOR_TEXT_PRIMARY};
}}

QSpinBox:focus, QLineEdit:focus {{
    border: 1px solid {COLOR_ACCENT};
}}

/* Buttons */
QPushButton.btn-primary {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton.btn-primary:hover {{
    background-color: {COLOR_ACCENT_HOVER};
}}

QPushButton.btn-primary:pressed {{
    background-color: #1f6feb;
}}

QPushButton.btn-secondary {{
    background-color: {COLOR_BG_CARD_ALT};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
}}

QPushButton.btn-secondary:hover {{
    background-color: {COLOR_BG_HOVER};
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QPushButton.btn-danger {{
    background-color: {COLOR_DANGER};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

/* Progress Bars */
QProgressBar {{
    background-color: {COLOR_BG_CARD_ALT};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    text-align: center;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    max-height: 12px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 3px;
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
