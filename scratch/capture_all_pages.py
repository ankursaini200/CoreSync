"""Offscreen Master Screenshot Generator for CoreSync Phase 11 Final Showcase."""

import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_PLATFORMTHEME"] = ""

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow(start_monitor=False)
    window.resize(1440, 960)
    window.show()
    app.processEvents()

    pages_to_capture = [
        (0, "00_dashboard.png", "Dashboard"),
        (1, "01_core_monitor.png", "Core Monitor"),
        (2, "02_process_monitor.png", "Process Monitor"),
        (3, "03_real_stress.png", "Real CPU Stress"),
        (4, "04_virtual_config.png", "Virtual CPU Config"),
        (5, "05_virtual_monitor.png", "Virtual Core Monitor"),
        (6, "06_virtual_scheduler.png", "Virtual Scheduler"),
        (7, "07_data_parallelism.png", "Data Parallelism"),
        (8, "08_task_parallelism.png", "Task Parallelism"),
        (9, "09_performance_analytics.png", "Performance Analytics"),
        (10, "10_settings.png", "Settings"),
        (11, "11_process_scheduler.png", "Process Scheduler"),
        (12, "12_real_vs_virtual_comparison.png", "Real vs Virtual Comparison"),
    ]

    for idx, filename, label in pages_to_capture:
        window.navigate_to_page(idx)
        app.processEvents()
        time.sleep(0.05)
        app.processEvents()

        dest = SCREENSHOTS_DIR / filename
        pixmap = window.grab()
        pixmap.save(str(dest), "PNG")
        print(f"[Captured] Page {idx} ({label}) -> {dest} ({dest.stat().st_size} bytes)")

    # Also copy to brain artifacts screenshots dir if defined in environment
    brain_dir = os.environ.get("CORESYNC_BRAIN_DIR")
    if brain_dir:
        brain_shots = Path(brain_dir) / "screenshots"
        if brain_shots.exists():
            import shutil
            for _, filename, _ in pages_to_capture:
                src = SCREENSHOTS_DIR / filename
                if src.exists():
                    shutil.copy2(src, brain_shots / filename)

    window.close()
    print("All 13 master workstation screenshots captured successfully!")
    os._exit(0)


if __name__ == "__main__":
    main()
