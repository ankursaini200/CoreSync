"""Master Screenshot Generator for CoreSync Rich Data Visualization UI Redesign.

Populates high-fidelity live telemetry and benchmark results across all 13 pages
and captures pixel-perfect 1440x960 screenshots.
"""

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

from monitoring.cpu_monitor import CPUMetricsSnapshot
from utils.hardware.base import ProcessInfo
from engine.process_manager import WorkerMetadata, WorkerLifecycleStatus
from engine.data_parallel.executor import (
    DataParallelBenchmarkResult,
    ParallelExecutionResult,
    ParallelTimingBreakdown,
)
from engine.data_parallel.verification import VerificationResult
from engine.data_parallel.worker import WorkerResult
from engine.data_parallel.partitioner import Chunk
from engine.task_parallel.result_collector import TaskDAGResult
from engine.task_parallel.worker import TaskExecutionResult
from gui.components.task_gantt import GanttTaskItem
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

SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

ARTIFACT_SCREENSHOTS = Path("/home/ankur/.gemini/antigravity/brain/36c47103-bffc-4579-9fdf-6bd23ce66107/screenshots")
ARTIFACT_SCREENSHOTS.mkdir(parents=True, exist_ok=True)


def populate_dashboard(page):
    """Seed dashboard with rich live metrics."""
    core_count = page.summary.logical_cores or 8
    cores = [38.2, 72.5, 45.1, 88.0, 24.3, 56.7, 91.2, 33.4] * 4
    cores = cores[:core_count]
    freqs = [3200.0 + (i * 100.0) for i in range(core_count)]

    snap = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=56.2,
        per_cpu_percent=cores,
        per_cpu_freq_mhz=freqs,
        ram_used_gb=9.98,
        ram_total_gb=16.0,
        ram_percent=62.4,
        coresync_workers_count=4,
    )
    # Feed ring buffer history for the area chart
    if hasattr(page, "timeline_chart"):
        for i in range(40):
            val_cpu = 40.0 + 25.0 * (0.5 + 0.5 * ((i % 7) - 3) / 3.0)
            val_ram = 58.0 + (i * 0.1)
            page.timeline_chart.add_sample(val_cpu, val_ram)
    page.update_metrics(snap)


def populate_core_monitor(page):
    """Seed core monitor with dynamic heatmap and timeline data."""
    core_count = page.summary.logical_cores or 8
    cores = [42.5, 84.1, 29.8, 93.4, 61.2, 18.7, 77.3, 36.9] * 4
    cores = cores[:core_count]
    freqs = [3400.0 + (i * 80.0) for i in range(core_count)]

    mock_workers = [
        WorkerMetadata(
            worker_id="DP-Worker-0",
            pid=5001,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[1],
            actual_cpu_affinity=[1],
            status=WorkerLifecycleStatus.RUNNING,
        ),
        WorkerMetadata(
            worker_id="DP-Worker-1",
            pid=5002,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[3],
            actual_cpu_affinity=[3],
            status=WorkerLifecycleStatus.RUNNING,
        ),
    ]

    snap = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=55.5,
        per_cpu_percent=cores,
        per_cpu_freq_mhz=freqs,
        ram_used_gb=9.98,
        ram_total_gb=16.0,
        ram_percent=62.4,
        coresync_workers_count=2,
        coresync_workers=mock_workers,
    )
    if hasattr(page, "timeline_chart"):
        for i in range(40):
            avg_c = 45.0 + 15.0 * ((i % 5) / 5.0)
            peak_c = avg_c + 28.0
            page.timeline_chart.add_sample(avg_c, min(100.0, peak_c))
    page.update_metrics(snap)


def populate_process_monitor(page):
    """Seed process monitor with ranked process table and distribution bars."""
    core_count = 8
    mock_workers = [
        WorkerMetadata(
            worker_id="CoreSync-Worker-0",
            pid=4812,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[1],
            actual_cpu_affinity=[1],
            status=WorkerLifecycleStatus.RUNNING,
        ),
        WorkerMetadata(
            worker_id="CoreSync-Worker-1",
            pid=4813,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[3],
            actual_cpu_affinity=[3],
            status=WorkerLifecycleStatus.RUNNING,
        ),
        WorkerMetadata(
            worker_id="CoreSync-Worker-2",
            pid=4814,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[5],
            actual_cpu_affinity=[5],
            status=WorkerLifecycleStatus.RUNNING,
        ),
        WorkerMetadata(
            worker_id="CoreSync-Worker-3",
            pid=4815,
            parent_pid=os.getpid(),
            engine_name="DataParallel",
            assigned_cpu_affinity=[7 % core_count],
            actual_cpu_affinity=[7 % core_count],
            status=WorkerLifecycleStatus.RUNNING,
        ),
    ]

    top_procs = [
        ProcessInfo(pid=4812, name="CoreSync-Worker-0", cpu_percent=78.4, memory_percent=3.2, memory_rss_mb=210.5, status="running", is_coresync_worker=True),
        ProcessInfo(pid=4813, name="CoreSync-Worker-1", cpu_percent=82.1, memory_percent=3.1, memory_rss_mb=208.2, status="running", is_coresync_worker=True),
        ProcessInfo(pid=4814, name="CoreSync-Worker-2", cpu_percent=69.5, memory_percent=3.4, memory_rss_mb=220.0, status="running", is_coresync_worker=True),
        ProcessInfo(pid=4815, name="CoreSync-Worker-3", cpu_percent=74.8, memory_percent=3.3, memory_rss_mb=214.8, status="running", is_coresync_worker=True),
        ProcessInfo(pid=1204, name="code-server", cpu_percent=12.4, memory_percent=6.5, memory_rss_mb=420.0, status="sleeping", is_coresync_worker=False),
        ProcessInfo(pid=892, name="Xorg", cpu_percent=8.2, memory_percent=4.1, memory_rss_mb=280.0, status="running", is_coresync_worker=False),
    ]

    snap = CPUMetricsSnapshot(
        timestamp=time.time(),
        overall_percent=55.5,
        per_cpu_percent=[50.0] * core_count,
        ram_used_gb=9.98,
        ram_total_gb=16.0,
        ram_percent=62.4,
        top_processes=top_procs,
        coresync_workers_count=4,
        coresync_worker_pids=[4812, 4813, 4814, 4815],
        coresync_workers=mock_workers,
    )
    page.update_metrics(snap)


def populate_virtual_monitor(page):
    """Seed virtual core monitor."""
    if hasattr(page, "gauge_sim_load"):
        page.gauge_sim_load.set_value(68.5)


def populate_data_parallel(page):
    """Seed data parallelism page with verified benchmark result."""
    chunks = [
        Chunk(chunk_id=0, start_idx=0, end_idx=250_000, size=250_000),
        Chunk(chunk_id=1, start_idx=250_000, end_idx=500_000, size=250_000),
        Chunk(chunk_id=2, start_idx=500_000, end_idx=750_000, size=250_000),
        Chunk(chunk_id=3, start_idx=750_000, end_idx=1_000_000, size=250_000),
    ]
    w_results = [
        WorkerResult(task_id=0, worker_id=0, chunk_id=0, success=True, data=None, worker_pid=5001, compute_time_s=0.038, input_delivery_latency_s=0.002, worker_start_time=1.002, worker_finish_time=1.040),
        WorkerResult(task_id=1, worker_id=1, chunk_id=1, success=True, data=None, worker_pid=5002, compute_time_s=0.039, input_delivery_latency_s=0.002, worker_start_time=1.002, worker_finish_time=1.041),
        WorkerResult(task_id=2, worker_id=2, chunk_id=2, success=True, data=None, worker_pid=5003, compute_time_s=0.037, input_delivery_latency_s=0.002, worker_start_time=1.002, worker_finish_time=1.039),
        WorkerResult(task_id=3, worker_id=3, chunk_id=3, success=True, data=None, worker_pid=5004, compute_time_s=0.040, input_delivery_latency_s=0.003, worker_start_time=1.003, worker_finish_time=1.043),
    ]
    tb = ParallelTimingBreakdown(
        startup_s=0.008,
        dispatch_s=0.003,
        collection_s=0.045,
        merge_s=0.002,
        total_s=0.058,
        max_worker_compute_s=0.040,
        estimated_distribution_overhead_s=0.018,
    )
    v_res = VerificationResult(
        passed=True,
        mismatch_count=0,
        total_items=1_000_000,
        max_difference=0.0,
        mean_difference=0.0,
        rtol=1e-5,
        atol=1e-8,
        status_message="Sequential and parallel outputs match perfectly",
    )
    res = DataParallelBenchmarkResult(
        op_id="transcendental",
        op_name="Transcendental (sin, cos, exp)",
        dataset_size=1_000_000,
        worker_count=4,
        chunks_count=4,
        sequential_time_s=0.152,
        parallel_time_s=0.042,
        timings=tb,
        speedup=3.62,
        efficiency_pct=90.5,
        throughput_items_per_s=23_800_000.0,
        verification=v_res,
        chunks=chunks,
        worker_results=w_results,
        success=True,
    )
    page._on_benchmark_finished(res)


def populate_task_parallel(page):
    """Seed task parallelism with diamond pipeline completion and Gantt tasks."""
    t_results = {
        "t1_prep": TaskExecutionResult(task_id="t1_prep", worker_id=0, worker_pid=5101, success=True, data={"count": 100}, compute_time_s=0.024, start_timestamp=10.000, finish_timestamp=10.024),
        "t2_matrix": TaskExecutionResult(task_id="t2_matrix", worker_id=1, worker_pid=5102, success=True, data={"shape": [100, 100]}, compute_time_s=0.042, start_timestamp=10.026, finish_timestamp=10.068),
        "t3_primes": TaskExecutionResult(task_id="t3_primes", worker_id=2, worker_pid=5103, success=True, data={"count": 250}, compute_time_s=0.038, start_timestamp=10.026, finish_timestamp=10.064),
        "t4_reduce": TaskExecutionResult(task_id="t4_reduce", worker_id=0, worker_pid=5101, success=True, data={"result": 42.0}, compute_time_s=0.018, start_timestamp=10.070, finish_timestamp=10.088),
    }
    dag_res = TaskDAGResult(
        success=True,
        total_tasks=4,
        completed_tasks=4,
        failed_tasks=0,
        cancelled_tasks=0,
        worker_count=3,
        makespan_s=0.088,
        cumulative_compute_s=0.122,
        sequential_time_s=0.136,
        actual_speedup=1.55,
        parallelism_ratio=1.39,
        worker_utilization_pct=46.2,
        sequential_verification_passed=True,
        task_results=t_results,
    )
    page._on_dag_finished(dag_res)


def populate_comparison(page):
    """Seed Real vs Virtual Comparison with complete dual-environment result."""
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
        comparison_id="cmp_rich_001",
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
        comparison_id="cmp_rich_001",
        timestamp="2026-11-07T12:00:00Z",
        configuration=cfg,
        real_result=real_res,
        virtual_result=virt_res,
        analysis=analysis,
        hardware_metadata=page.summary.__dict__ if hasattr(page, "summary") else {},
        success=True,
    )
    page._on_comparison_finished(session)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow(start_monitor=False)
    window.resize(1440, 960)
    window.show()
    app.processEvents()

    # Pre-populate dynamic pages
    populate_dashboard(window.pages.widget(0))
    populate_core_monitor(window.pages.widget(1))
    populate_process_monitor(window.pages.widget(2))
    populate_virtual_monitor(window.pages.widget(5))
    populate_data_parallel(window.pages.widget(7))
    populate_task_parallel(window.pages.widget(8))
    populate_comparison(window.pages.widget(12))

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

    import shutil

    for idx, filename, label in pages_to_capture:
        window.navigate_to_page(idx)
        app.processEvents()
        time.sleep(0.08)
        app.processEvents()

        dest = SCREENSHOTS_DIR / filename
        pixmap = window.grab()
        pixmap.save(str(dest), "PNG")
        print(f"[Captured] Page {idx:02d} ({label:28s}) -> {dest} ({dest.stat().st_size:,} bytes)")

        # Copy to artifacts directory
        artifact_dest = ARTIFACT_SCREENSHOTS / filename
        shutil.copy2(dest, artifact_dest)

    window.close()
    print("\n✓ All 13 rich visualization screenshots captured and saved to docs/screenshots/ & artifacts!")
    os._exit(0)


if __name__ == "__main__":
    main()
