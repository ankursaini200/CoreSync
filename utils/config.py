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

# UI Theme Constants - Premium Dark & Gradient Visual Identity Palette
COLOR_BG_DARK = "#0B1020"            # Deep space navy background
COLOR_BG_SIDEBAR = "#0D1220"         # Layered dark sidebar surface
COLOR_SIDEBAR_BG = "#0D1220"         # Alias for sidebar background
COLOR_SURFACE_SECONDARY = "#121B2B"  # Secondary surface for status cards & toolbars
COLOR_SURFACE_ELEVATED = "#19263A"   # Elevated surface for badges & chips
COLOR_BG_CARD = "#151F30"            # Dark slate navy card
COLOR_BG_CARD_ALT = "#1C283E"        # Secondary card / container background
COLOR_BG_HOVER = "#1E2C42"           # Interactive hover state
COLOR_BORDER = "#273750"             # Refined slate grid & borders
COLOR_BORDER_LIGHT = "#364C6E"       # Active / highlighted borders

# Core Gradients
GRADIENT_PRIMARY_START = "#4776E6"   # Primary Gradient Start (Vibrant Blue)
GRADIENT_PRIMARY_END = "#36C9E8"     # Primary Gradient End (Electric Cyan)
GRADIENT_SECONDARY_START = "#7657D5" # Secondary Gradient Start (Deep Violet)
GRADIENT_SECONDARY_END = "#A78BFA"   # Secondary Gradient End (Soft Lavender)
GRADIENT_TEAL_START = "#159D91"      # Teal Gradient Start
GRADIENT_TEAL_END = "#42D6B0"        # Teal Gradient End (Mint)
GRADIENT_WARM_START = "#D18B42"      # Warm Accent Start (Amber)
GRADIENT_WARM_END = "#F1BC70"        # Warm Accent End (Gold)

# Semantic Category Accents
COLOR_ACCENT = "#579BFF"             # Primary CPU Activity / Vibrant Blue
COLOR_ACCENT_HOVER = "#70ABFF"       # Hover Accent Blue
COLOR_ACCENT_SECONDARY = "#36C9E8"   # Secondary CPU Activity / Bright Cyan
COLOR_PERFORMANCE = "#42B883"        # Performance / Verified Success Emerald
COLOR_SUCCESS = "#42D6B0"            # Emerald / Teal Green
COLOR_MEMORY = "#9B83F5"             # Memory / Lavender Purple
COLOR_TASK = "#E6B45C"               # Task Execution / Warm Amber Gold
COLOR_WARNING = "#E6B45C"            # Warm Amber
COLOR_DANGER = "#F07178"             # Error / Alert Coral Red
COLOR_TEXT_PRIMARY = "#E8EEF8"       # High contrast crisp text
COLOR_TEXT_SECONDARY = "#96A8C2"     # Secondary clear text
COLOR_TEXT_MUTED = "#71839D"         # Secondary descriptive & metadata text
COLOR_P_CORE = "#579BFF"             # Performance Core Blue
COLOR_E_CORE = "#9B83F5"             # Efficient Core Lavender Purple

