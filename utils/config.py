"""Application configuration and constants for CoreSync."""

from dataclasses import dataclass
from pathlib import Path
import os

APP_NAME = "CoreSync"
APP_SUBTITLE = "Multicore Processing and Parallelism Simulator"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "AcademicOS"

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)

# Performance & Multiprocessing Defaults
DEFAULT_WARMUP_RUNS = 1
DEFAULT_BENCHMARK_RUNS = 3
DEFAULT_WORKER_TIMEOUT = 10.0  # seconds

# Process Termination Timeouts (Graceful Escalation)
COOPERATIVE_TIMEOUT = 2.0   # Wait for cancel_event
SIGTERM_TIMEOUT = 1.5       # Wait after process.terminate()
SIGKILL_TIMEOUT = 0.5       # Wait after process.kill()

# UI Theme Constants - Rich Data Visualization Palette
COLOR_BG_DARK = "#0B1020"        # Deep space navy background
COLOR_BG_SIDEBAR = "#0D1424"     # Sleek dark sidebar
COLOR_BG_CARD = "#151F30"        # Dark slate navy card
COLOR_BG_CARD_ALT = "#1C283E"    # Secondary card / container background
COLOR_BG_HOVER = "#22334D"       # Interactive hover state
COLOR_BORDER = "#293B54"         # Deep slate grid & borders
COLOR_BORDER_LIGHT = "#3A5173"   # Active / highlighted borders
COLOR_ACCENT = "#579BFF"         # Primary CPU Activity / Vibrant Blue
COLOR_ACCENT_HOVER = "#70ABFF"   # Hover Accent Blue
COLOR_ACCENT_SECONDARY = "#36C9E8" # Secondary CPU Activity / Bright Cyan
COLOR_PERFORMANCE = "#42B883"    # Performance / Verified Success Emerald
COLOR_SUCCESS = "#42B883"        # Emerald Green
COLOR_MEMORY = "#9B83F5"         # Memory / Lavender Purple
COLOR_TASK = "#E6B45C"           # Task Execution / Warm Amber Gold
COLOR_WARNING = "#E6B45C"        # Warm Amber
COLOR_DANGER = "#F07178"         # Error / Alert Coral Red
COLOR_TEXT_PRIMARY = "#E5EAF1"   # High contrast crisp text
COLOR_TEXT_MUTED = "#8FA0B8"     # Secondary descriptive text
COLOR_P_CORE = "#579BFF"         # Performance Core Blue
COLOR_E_CORE = "#9B83F5"         # Efficient Core Lavender Purple

