"""Offscreen screenshot generation script for Phase 10 Real System vs Virtual Lab Comparison."""

import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_PLATFORMTHEME"] = ""

PROJECT_ROOT = Path("/home/ankur/Code Playground/OS project/CoreSync")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from gui.comparison import ComparisonPage
from engine.comparison.models import (
    ComparisonAnalysis,
    ComparisonConfiguration,
    ComparisonExecutionMode,
    ComparisonSessionResult,
    ComparisonWorkloadConfig,
    ComparisonWorkloadType,
    RealExecutionResult,
    RealSystemConfig,
    VirtualExecutionResult,
    VirtualLabConfig,
)
from engine.virtual_lab.virtual_scheduler import SchedulingAlgorithm

SCREENSHOTS_DIR = Path("/home/ankur/.gemini/antigravity/brain/36c47103-bffc-4579-9fdf-6bd23ce66107/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow(start_monitor=False)
    window.resize(1440, 960)
    window.show()
    app.processEvents()

    # Navigate to page 12: Real vs Virtual Comparison
    window.navigate_to_page(12)
    app.processEvents()

    comp_page: ComparisonPage = window.pages.widget(12)

    # Populate with an active high-fidelity comparison result
    real_res = RealExecutionResult(
        status="completed",
        wall_clock_time_s=0.0842,
        worker_count=4,
        worker_intervals=[
            (0.005, 0.048),
            (0.006, 0.051),
            (0.005, 0.046),
            (0.007, 0.053),
        ],
        aggregate_worker_compute_time_s=0.1750,
        compute_interval_union_s=0.0480,
        no_worker_compute_time_s=0.0362,
        sequential_baseline_s=0.1980,
        actual_speedup=2.35,
        worker_utilization_pct=52.0,
        peak_memory_rss_mb=46.8,
        host_cpu_percent=28.4,
        task_completions=[
            {"task_id": "dp_chunk_0", "process_id": 48120, "duration_s": 0.0430},
            {"task_id": "dp_chunk_1", "process_id": 48121, "duration_s": 0.0450},
            {"task_id": "dp_chunk_2", "process_id": 48122, "duration_s": 0.0410},
            {"task_id": "dp_chunk_3", "process_id": 48123, "duration_s": 0.0460},
        ],
        verification_passed=True,
    )

    virt_res = VirtualExecutionResult(
        status="completed",
        virtual_makespan_ticks=120,
        simulated_clock_ticks=120,
        virtual_core_utilization_pct=83.3,
        virtual_core_count=4,
        virtual_core_allocation={
            0: ["dp_chunk_0"],
            1: ["dp_chunk_1"],
            2: ["dp_chunk_2"],
            3: ["dp_chunk_3"],
        },
        task_completion_order=[
            {"task_id": "dp_chunk_2", "assigned_core_id": 2, "finish_tick": 95, "waiting_ticks": 0},
            {"task_id": "dp_chunk_0", "assigned_core_id": 0, "finish_tick": 100, "waiting_ticks": 0},
            {"task_id": "dp_chunk_1", "assigned_core_id": 1, "finish_tick": 105, "waiting_ticks": 0},
            {"task_id": "dp_chunk_3", "assigned_core_id": 3, "finish_tick": 110, "waiting_ticks": 0},
        ],
        scheduling_events=[
            {"tick": 0, "event": "DISPATCH", "task_id": "dp_chunk_0", "core_id": 0},
            {"tick": 0, "event": "DISPATCH", "task_id": "dp_chunk_1", "core_id": 1},
            {"tick": 0, "event": "DISPATCH", "task_id": "dp_chunk_2", "core_id": 2},
            {"tick": 0, "event": "DISPATCH", "task_id": "dp_chunk_3", "core_id": 3},
            {"tick": 95, "event": "COMPLETE", "task_id": "dp_chunk_2", "core_id": 2},
            {"tick": 100, "event": "COMPLETE", "task_id": "dp_chunk_0", "core_id": 0},
            {"tick": 105, "event": "COMPLETE", "task_id": "dp_chunk_1", "core_id": 1},
            {"tick": 110, "event": "COMPLETE", "task_id": "dp_chunk_3", "core_id": 3},
        ],
        simulated_throughput_tasks_per_tick=0.0333,
        avg_waiting_ticks=0.0,
        avg_turnaround_ticks=102.5,
        preemption_count=0,
    )

    analysis = ComparisonAnalysis(
        workload_equivalence=True,
        workload_equivalence_details="Verified identical mathematical kernel inputs: 50,000 float64 elements partitioned across 4 logical chunks.",
        task_count_match=True,
        completion_order_concordance=0.8333,
        real_worker_count=4,
        virtual_core_count=4,
        resource_allocation_ratio=1.00,
        real_utilization_pct=52.0,
        virtual_utilization_pct=83.3,
        utilization_difference_pct=-31.3,
        scheduling_policy_effects=[
            "Virtual Lab executed with First-Come First-Served scheduling without preemption.",
            "Real System executed via OS kernel scheduler with dynamic process contention.",
        ],
        explanatory_notes=[
            "CLOCK DOMAIN BOUNDARY: Real System wall-clock elapsed time (seconds) and Virtual Lab simulation time (discrete logical ticks) belong to distinct clock domains. They are never divided.",
            "REAL SYSTEM: Reflects physical OS process management, memory paging, IPC serialization, and host kernel scheduling delays.",
            "VIRTUAL LAB: Reflects idealized software-simulated processor cores, discrete tick advancing, and educational scheduling algorithms.",
            "UTILIZATION COMPARISON: Real worker utilization was 52.0% (cumulative compute W*s / capacity), while Virtual core utilization was 83.3% (busy ticks / capacity ticks).",
        ],
    )

    cfg = ComparisonConfiguration(
        comparison_id="cmp_showcase_001",
        execution_mode=ComparisonExecutionMode.COMPARE_BOTH,
        workload=ComparisonWorkloadConfig(
            workload_type=ComparisonWorkloadType.DATA_PARALLEL,
            workload_id="transcendental",
            workload_name="Transcendental (sin/cos/exp)",
            dataset_size=50000,
            task_count=4,
        ),
        real_config=RealSystemConfig(worker_count=4),
        virtual_config=VirtualLabConfig(
            virtual_core_count=4,
            scheduling_algorithm=SchedulingAlgorithm.FCFS,
        ),
    )

    session = ComparisonSessionResult(
        comparison_id="cmp_showcase_001",
        timestamp="2026-11-07T12:00:00Z",
        configuration=cfg,
        real_result=real_res,
        virtual_result=virt_res,
        analysis=analysis,
        hardware_metadata=window.summary.__dict__,
        success=True,
    )

    # Deliver session result to page
    comp_page._on_comparison_finished(session)

    # 1. Capture Comparative Analysis & Equivalence Tab (Tab 2)
    comp_page.tabs_results.setCurrentIndex(2)
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()

    target_path = SCREENSHOTS_DIR / "10_real_vs_virtual_comparison.png"
    pixmap = window.grab()
    pixmap.save(str(target_path), "PNG")
    print(f"[Screenshot 1] Saved: {target_path} ({target_path.stat().st_size} bytes)")

    # 2. Capture Real System Tab (Tab 0)
    comp_page.tabs_results.setCurrentIndex(0)
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    target_real = SCREENSHOTS_DIR / "10_real_system_tab.png"
    window.grab().save(str(target_real), "PNG")
    print(f"[Screenshot 2] Saved: {target_real} ({target_real.stat().st_size} bytes)")

    # 3. Capture Virtual Lab Tab (Tab 1)
    comp_page.tabs_results.setCurrentIndex(1)
    app.processEvents()
    time.sleep(0.1)
    app.processEvents()
    target_virt = SCREENSHOTS_DIR / "10_virtual_lab_tab.png"
    window.grab().save(str(target_virt), "PNG")
    print(f"[Screenshot 3] Saved: {target_virt} ({target_virt.stat().st_size} bytes)")

    window.close()
    print("All Phase 10 screenshots captured successfully!")
    os._exit(0)


if __name__ == "__main__":
    main()
