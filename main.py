"""CoreSync: Multicore Processing and Parallelism Simulator.

Master Application Entry Point.
"""

import os
import sys
import argparse
import multiprocessing as mp

# Configure Matplotlib writable directory before any imports
from pathlib import Path
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(LOGS_DIR / ".mplconfig"))

from utils.config import APP_NAME
from utils.logging_config import setup_logging


def parse_args():
    parser = argparse.ArgumentParser(description=f"{APP_NAME} Desktop Application")
    parser.add_argument(
        "--test-startup",
        action="store_true",
        help="Launch the application, verify rendering, and exit automatically after 1 second.",
    )
    return parser.parse_args()


def main() -> int:
    # 1. Enforce multiprocessing spawn context
    mp.set_start_method("spawn", force=True)

    # 2. Handle Linux Wayland/X11 environment gracefully before Qt initializes
    wayland_socket_valid = False
    if "WAYLAND_DISPLAY" in os.environ:
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        if xdg_runtime and (Path(xdg_runtime) / os.environ["WAYLAND_DISPLAY"]).exists():
            wayland_socket_valid = True

    display_valid = bool(os.environ.get("DISPLAY"))

    if not wayland_socket_valid and not display_valid:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QPA_PLATFORMTHEME"] = ""
        os.environ.pop("WAYLAND_DISPLAY", None)
        os.environ.pop("DISPLAY", None)

    # 3. Import Qt only after environment variables are configured
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    # 4. Setup Logging
    logger = setup_logging()
    logger.info("Initializing CoreSync Desktop Workstation...")

    # 5. Parse command-line flags
    args = parse_args()

    # 5. Initialize QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 6. Instantiate and display main window
    window = MainWindow()
    window.show()
    logger.info("CoreSync Main Window rendered successfully.")

    # 7. Automated startup verification mode (for tests and headless CI)
    if args.test_startup:
        logger.info("Test startup mode active: scheduling graceful shutdown in 1000ms...")
        QTimer.singleShot(1000, window.close)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

