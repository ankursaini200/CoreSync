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

# UI Theme Constants - Professional Minimal Dark Theme
COLOR_BG_DARK = "#10141B"        # Main background
COLOR_BG_SIDEBAR = "#151B24"     # Sidebar
COLOR_BG_CARD = "#1A202B"        # Card background
COLOR_BG_CARD_ALT = "#202836"    # Secondary background / card-alt
COLOR_BG_HOVER = "#263040"       # Interactive hover state
COLOR_BORDER = "#303A49"         # Subtle borders
COLOR_BORDER_LIGHT = "#3E4C60"   # Active / hover borders
COLOR_ACCENT = "#4B91D1"         # Primary accent (restrained slate blue)
COLOR_ACCENT_HOVER = "#5EA3E3"   # Hover accent
COLOR_TEXT_PRIMARY = "#E5EAF1"   # Primary text
COLOR_TEXT_MUTED = "#9AA5B4"     # Secondary text
COLOR_SUCCESS = "#399B70"        # Restrained forest/sage success
COLOR_WARNING = "#C69A46"        # Restrained amber warning
COLOR_DANGER = "#CF6262"         # Subdued crimson error
COLOR_P_CORE = "#4B91D1"         # Performance Core Blue
COLOR_E_CORE = "#8E7CC3"         # Efficient Core Muted Purple

