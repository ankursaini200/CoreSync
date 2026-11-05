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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from utils.config import APP_NAME
from utils.logging_config import setup_logging
from gui.main_window import MainWindow


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

    # 2. Setup Logging
    logger = setup_logging()
    logger.info("Initializing CoreSync Desktop Workstation...")

    # 3. Parse command-line flags
    args = parse_args()

    # 4. Handle Linux Wayland/X11 environment gracefully
    if "QT_QPA_PLATFORM" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and "DISPLAY" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        logger.info("Headless environment detected; using offscreen Qt platform plugin.")

    # 5. Initialize QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 6. Instantiate and display main window
    window = MainWindow()
    window.show()
    logger.info("CoreSync Main Window rendered successfully.")

    # 7. Automated startup verification mode (for tests and headless CI)
    if args.test_startup:
        logger.info("Test startup mode active: scheduling shutdown in 1000ms...")
        QTimer.singleShot(1000, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

