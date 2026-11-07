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

# UI Theme Constants - Black Gradient Visual Identity Palette
COLOR_BG_DARK = "#08090B"            # Main application deep black canvas
COLOR_BG_SECONDARY = "#0D0D10"       # Secondary dark background
COLOR_BG_SIDEBAR = "#0D0D10"         # Layered dark sidebar surface
COLOR_SIDEBAR_BG = "#0D0D10"         # Alias for sidebar background
COLOR_SURFACE_SECONDARY = "#111113"  # Deep card surface / toolbars
COLOR_SURFACE_ELEVATED = "#1C191D"   # Elevated card surface / chips
COLOR_BG_CARD = "#151416"            # Primary charcoal card surface
COLOR_BG_CARD_ALT = "#1C191D"        # Secondary elevated card container
COLOR_BG_HOVER = "#232025"           # Interactive hover state
COLOR_BORDER = "#302B32"             # Refined charcoal borders
COLOR_BORDER_LIGHT = "#47404B"       # Active / highlighted borders

# Core Gradients
GRADIENT_PRIMARY_START = "#7956C8"   # Violet start
GRADIENT_PRIMARY_END = "#A879F5"     # Violet end
GRADIENT_SECONDARY_START = "#7956C8" # Purple start
GRADIENT_SECONDARY_END = "#D17BE8"   # Magenta end
GRADIENT_TEAL_START = "#19C99A"      # Teal start
GRADIENT_TEAL_END = "#42D6A0"        # Emerald end
GRADIENT_WARM_START = "#E4AD69"      # Warm amber start
GRADIENT_WARM_END = "#F1BC70"        # Warm gold end

# Black Gradient Ambient Backgrounds
GRADIENT_BG_START = "#08090B"
GRADIENT_BG_MID = "#111013"
GRADIENT_BG_END = "#08090B"

GRADIENT_CARD_CHARCOAL_START = "#151416"
GRADIENT_CARD_CHARCOAL_END = "#211D22"

GRADIENT_TEAL_AMBIENT_START = "#101512"
GRADIENT_TEAL_AMBIENT_END = "#17201C"

GRADIENT_VIOLET_AMBIENT_START = "#100E13"
GRADIENT_VIOLET_AMBIENT_END = "#1D1721"

# Semantic Category Accents (Teal, Emerald, Violet, Purple, Amber, Red - No Blue)
COLOR_TEAL = "#19C99A"
COLOR_EMERALD = "#42D6A0"
COLOR_VIOLET = "#A879F5"
COLOR_PURPLE = "#7956C8"
COLOR_MAGENTA = "#D17BE8"
COLOR_AMBER = "#E4AD69"
COLOR_RED = "#EF737D"
COLOR_WHITE_HIGHLIGHT = "#F4F1F5"

COLOR_ACCENT = "#19C99A"             # Primary CPU Activity / Teal
COLOR_ACCENT_HOVER = "#42D6A0"       # Hover Accent / Emerald
COLOR_ACCENT_SECONDARY = "#42D6A0"   # Secondary CPU Activity / Emerald
COLOR_PERFORMANCE = "#42D6A0"        # Performance / Emerald
COLOR_SUCCESS = "#42D6A0"            # Emerald / Mint Green
COLOR_MEMORY = "#A879F5"             # Memory / Violet
COLOR_TASK = "#E4AD69"               # Task Execution / Amber
COLOR_WARNING = "#E4AD69"            # Warning Amber
COLOR_DANGER = "#EF737D"             # Error / Coral Red
COLOR_TEXT_PRIMARY = "#F2F0F3"       # High contrast crisp white
COLOR_TEXT_SECONDARY = "#AAA4AE"     # Secondary clear text
COLOR_TEXT_MUTED = "#77717C"         # Secondary descriptive & metadata text
COLOR_P_CORE = "#A879F5"             # Performance Core: Violet
COLOR_E_CORE = "#19C99A"             # Efficient Core: Teal

