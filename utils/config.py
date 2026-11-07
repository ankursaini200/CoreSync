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

# UI Theme Constants
COLOR_BG_DARK = "#0d1117"
COLOR_BG_SIDEBAR = "#131822"
COLOR_BG_CARD = "#161b24"
COLOR_BG_CARD_ALT = "#1c2330"
COLOR_BG_HOVER = "#212836"
COLOR_BORDER = "#283344"
COLOR_BORDER_LIGHT = "#3b475c"
COLOR_ACCENT = "#58a6ff"
COLOR_ACCENT_HOVER = "#79c0ff"
COLOR_TEXT_PRIMARY = "#e6edf3"
COLOR_TEXT_MUTED = "#8b949e"
COLOR_SUCCESS = "#3fb950"
COLOR_WARNING = "#d29922"
COLOR_DANGER = "#f85149"
COLOR_P_CORE = "#388bfd"   # Performance Core Blue
COLOR_E_CORE = "#a371f7"   # Efficient Core Purple

