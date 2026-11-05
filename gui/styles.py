"""Modern dark theme stylesheet and color palette constants for CoreSync."""

from utils.config import (
    COLOR_BG_DARK,
    COLOR_BG_CARD,
    COLOR_BG_HOVER,
    COLOR_BORDER,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
)

DARK_STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
}}

QWidget {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Inter', 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 13px;
}}

/* Sidebar & Navigation */
#sidebar {{
    background-color: {COLOR_BG_CARD};
    border-right: 1px solid {COLOR_BORDER};
    min-width: 220px;
    max-width: 240px;
}}

#appTitle {{
    font-size: 18px;
    font-weight: bold;
    color: {COLOR_ACCENT};
    padding: 16px 12px 4px 12px;
}}

#appSubtitle {{
    font-size: 11px;
    color: {COLOR_TEXT_MUTED};
    padding: 0px 12px 16px 12px;
}}

/* Navigation Buttons */
QPushButton.nav-button {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    border: none;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 500;
}}

QPushButton.nav-button:hover {{
    background-color: {COLOR_BG_HOVER};
    color: {COLOR_ACCENT_HOVER};
}}

QPushButton.nav-button:checked {{
    background-color: #1f2937;
    color: {COLOR_ACCENT};
    border-left: 3px solid {COLOR_ACCENT};
}}

/* Cards & Content Containers */
QFrame.card {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 16px;
}}

/* Headings */
QLabel.heading {{
    font-size: 16px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel.muted {{
    color: {COLOR_TEXT_MUTED};
    font-size: 12px;
}}

/* Primary & Action Buttons */
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

QPushButton.btn-danger {{
    background-color: {COLOR_DANGER};
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}}

/* Status Badges */
QLabel.badge-success {{
    color: {COLOR_SUCCESS};
    background-color: rgba(63, 185, 80, 0.15);
    border: 1px solid {COLOR_SUCCESS};
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 11px;
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_MUTED};
    border-top: 1px solid {COLOR_BORDER};
    font-size: 11px;
}}
"""

