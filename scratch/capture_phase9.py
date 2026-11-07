"""Offscreen screenshot generation script for Phase 9 Performance Analytics & Amdahl's Law."""

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
from gui.performance import PerformancePage
from engine.analytics.benchmarking import (
    BenchmarkEngineType,
    BenchmarkIterationRecord,
    BenchmarkSessionResult,
)
from engine.analytics.history import BenchmarkHistoryManager

SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow(start_monitor=False)
    window.resize(1440, 960)
    window.show()

    app.processEvents()

    # Navigate to Performance Analytics Page (index 9)
    window.navigate_to_page(9)
    app.processEvents()

    perf_page: PerformancePage = window.pages.widget(9)

    # 1. Populate History with representative benchmark runs
    hist_mgr = perf_page._history_mgr

    # DP session
    dp_session = BenchmarkSessionResult(
        benchmark_id="dp_transcendental_20261106_183000",
        engine_type=BenchmarkEngineType.DATA_PARALLEL,
        workload_name="Element-Wise Transcendental Math",
        worker_count=8,
        config_parameters={"op_id": "transcendental", "dataset_size": 200000, "worker_count": 8},
        hardware_metadata={
            "cpu_model": "13th Gen Intel(R) Core(TM) i7-13650HX",
            "physical_cores": 14,
            "total_logical_cores": 20,
            "architecture": "x86_64",
            "operating_system": "Arch Linux (Linux 7.2.14-arch1-1)",
        },
        start_timestamp="2026-11-06T18:30:00Z",
        end_timestamp="2026-11-06T18:30:01Z",
        total_wall_clock_s=0.24,
        iterations_requested=3,
        warmup_iterations_requested=1,
        warmup_records=[
            BenchmarkIterationRecord(
                iteration_idx=1,
                is_warmup=True,
                sequential_time_s=0.185,
                parallel_time_s=0.034,
                speedup=5.44,
                efficiency_pct=68.0,
                throughput=5882352.0,
                verification_passed=True,
                extra_metrics={"startup_s": 0.006, "dispatch_s": 0.002, "collection_s": 0.002, "merge_s": 0.001, "estimated_distribution_overhead_s": 0.009},
            )
        ],
        measured_records=[
            BenchmarkIterationRecord(
                iteration_idx=1,
                is_warmup=False,
                sequential_time_s=0.182,
                parallel_time_s=0.029,
                speedup=6.28,
                efficiency_pct=78.5,
                throughput=6896551.0,
                verification_passed=True,
                extra_metrics={
                    "startup_s": 0.001,
                    "dispatch_s": 0.001,
                    "collection_s": 0.001,
                    "merge_s": 0.001,
                    "compute_interval_union_s": 0.026,
                    "no_worker_compute_time_s": 0.002,
                    "idle_gap_time_s": 0.002,
                    "aggregate_worker_compute_time_s": 0.180,
                    "aggregate_estimated_residual_s": 0.002,
                },
            ),
            BenchmarkIterationRecord(
                iteration_idx=2,
                is_warmup=False,
                sequential_time_s=0.183,
                parallel_time_s=0.028,
                speedup=6.54,
                efficiency_pct=81.7,
                throughput=7142857.0,
                verification_passed=True,
                extra_metrics={
                    "startup_s": 0.001,
                    "dispatch_s": 0.001,
                    "collection_s": 0.001,
                    "merge_s": 0.001,
                    "compute_interval_union_s": 0.026,
                    "no_worker_compute_time_s": 0.002,
                    "idle_gap_time_s": 0.002,
                    "aggregate_worker_compute_time_s": 0.180,
                    "aggregate_estimated_residual_s": 0.002,
                },
            ),
            BenchmarkIterationRecord(
                iteration_idx=3,
                is_warmup=False,
                sequential_time_s=0.181,
                parallel_time_s=0.028,
                speedup=6.46,
                efficiency_pct=80.8,
                throughput=7142857.0,
                verification_passed=True,
                extra_metrics={
                    "startup_s": 0.001,
                    "dispatch_s": 0.001,
                    "collection_s": 0.001,
                    "merge_s": 0.001,
                    "compute_interval_union_s": 0.026,
                    "no_worker_compute_time_s": 0.002,
                    "idle_gap_time_s": 0.002,
                    "aggregate_worker_compute_time_s": 0.180,
                    "aggregate_estimated_residual_s": 0.002,
                },
            ),
        ],
        statistics={
            "sequential_time_s": {"mean": 0.182, "std_dev": 0.001},
            "parallel_time_s": {"mean": 0.028, "std_dev": 0.001},
            "speedup": {"mean": 6.43, "std_dev": 0.13},
            "efficiency_pct": {"mean": 80.3, "std_dev": 1.6},
            "throughput": {"mean": 7060755.0, "std_dev": 142203.0},
        },
        verification_passed=True,
    )
    hist_mgr.save_session(dp_session)

    # TP session
    tp_session = BenchmarkSessionResult(
        benchmark_id="tp_diamond_20261106_183200",
        engine_type=BenchmarkEngineType.TASK_PARALLEL,
        workload_name="Task DAG (Diamond)",
        worker_count=4,
        config_parameters={"dag_type": "diamond", "worker_count": 4},
        hardware_metadata={
            "cpu_model": "13th Gen Intel(R) Core(TM) i7-13650HX",
            "physical_cores": 14,
            "total_logical_cores": 20,
            "architecture": "x86_64",
            "operating_system": "Arch Linux (Linux 7.2.14-arch1-1)",
        },
        start_timestamp="2026-11-06T18:32:00Z",
        end_timestamp="2026-11-06T18:32:01Z",
        total_wall_clock_s=0.45,
        iterations_requested=3,
        warmup_iterations_requested=1,
        warmup_records=[],
        measured_records=[
            BenchmarkIterationRecord(
                iteration_idx=1,
                is_warmup=False,
                sequential_time_s=0.310,
                parallel_time_s=0.112,
                speedup=2.77,
                efficiency_pct=69.2,
                throughput=35.7,
                verification_passed=True,
                extra_metrics={
                    "parallelism_ratio": 2.82,
                    "worker_utilization_pct": 70.5,
                    "aggregate_worker_compute_time_s": 0.316,
                    "cumulative_compute_s": 0.316,
                    "compute_interval_union_s": 0.098,
                    "no_worker_compute_time_s": 0.014,
                    "idle_gap_time_s": 0.014,
                    "aggregate_estimated_residual_s": 0.014,
                },
            )
        ],
        statistics={
            "sequential_time_s": {"mean": 0.310, "std_dev": 0.0},
            "parallel_time_s": {"mean": 0.112, "std_dev": 0.0},
            "speedup": {"mean": 2.77, "std_dev": 0.0},
            "efficiency_pct": {"mean": 69.2, "std_dev": 0.0},
        },
        verification_passed=True,
    )
    hist_mgr.save_session(tp_session)

    # Refresh history & dashboard
    perf_page._refresh_history_table()
    perf_page._render_dp_results(dp_session)
    perf_page._render_tp_results(tp_session)

    # Run quick sched & vlab benchmarks to populate those tabs
    perf_page.sched_combo_preset.setCurrentIndex(0)
    perf_page._run_sched_benchmark()
    perf_page._runner_thread.wait(2000)

    perf_page.vlab_spin_cores.setValue(8)
    perf_page.vlab_spin_tasks.setValue(50)
    perf_page._run_vlab_benchmark()
    perf_page._runner_thread.wait(2000)

    app.processEvents()
    time.sleep(0.3)
    app.processEvents()

    # -------------------------------------------------------------------------
    # 1. Capture Dashboard (Tab 0)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(0)
    app.processEvents()
    pix = window.grab()
    p1 = SCREENSHOTS_DIR / "09_performance_dashboard.png"
    pix.save(str(p1), "PNG")
    print(f"[Screenshot 1] Saved: {p1} ({p1.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 2. Capture Data Parallelism Analytics (Tab 1)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(1)
    app.processEvents()
    pix = window.grab()
    p2 = SCREENSHOTS_DIR / "09_data_parallel_analytics.png"
    pix.save(str(p2), "PNG")
    print(f"[Screenshot 2] Saved: {p2} ({p2.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 3. Capture Task Parallelism Analytics (Tab 2)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(2)
    app.processEvents()
    pix = window.grab()
    p3 = SCREENSHOTS_DIR / "09_task_parallel_analytics.png"
    pix.save(str(p3), "PNG")
    print(f"[Screenshot 3] Saved: {p3} ({p3.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 4. Capture CPU Scheduling Analytics (Tab 3)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(3)
    app.processEvents()
    pix = window.grab()
    p4 = SCREENSHOTS_DIR / "09_scheduling_analytics.png"
    pix.save(str(p4), "PNG")
    print(f"[Screenshot 4] Saved: {p4} ({p4.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 5. Capture Virtual Lab Analytics (Tab 4)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(4)
    app.processEvents()
    pix = window.grab()
    p5 = SCREENSHOTS_DIR / "09_virtual_lab_analytics.png"
    pix.save(str(p5), "PNG")
    print(f"[Screenshot 5] Saved: {p5} ({p5.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 6. Capture Benchmark History (Tab 5)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(5)
    perf_page._refresh_history_table()
    if perf_page.hist_table.rowCount() > 0:
        perf_page.hist_table.selectRow(0)
    app.processEvents()
    pix = window.grab()
    p6 = SCREENSHOTS_DIR / "09_benchmark_history.png"
    pix.save(str(p6), "PNG")
    print(f"[Screenshot 6] Saved: {p6} ({p6.stat().st_size} bytes)")

    # -------------------------------------------------------------------------
    # 7. Capture Amdahl's Law Calculator (Tab 6)
    # -------------------------------------------------------------------------
    perf_page.tabs.setCurrentIndex(6)
    perf_page.amdahl_slider_p.setValue(85)
    perf_page.amdahl_slider_n.setValue(8)
    perf_page._update_amdahl_display()
    app.processEvents()
    pix = window.grab()
    p7 = SCREENSHOTS_DIR / "09_amdahl_calculator.png"
    pix.save(str(p7), "PNG")
    print(f"[Screenshot 7] Saved: {p7} ({p7.stat().st_size} bytes)")

    window.close()
    print("All Phase 9 screenshots captured successfully!")
    os._exit(0)


if __name__ == "__main__":
    main()

