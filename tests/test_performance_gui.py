"""GUI integration tests for Performance Analytics, Benchmarking, and Amdahl's Law page."""

import os
import sys
from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel

from engine.analytics.benchmarking import (
    BenchmarkEngineType,
    BenchmarkIterationRecord,
    BenchmarkSessionResult,
)
from engine.analytics.history import BenchmarkHistoryManager
from gui.components.analytics_chart import (
    AmdahlCurveWidget,
    ScalabilityChartWidget,
    TimingBreakdownWidget,
)
from gui.performance import PerformancePage


@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication instance is initialized for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_performance_page_tabs_and_structure(qapp, tmp_path):
    """Verify PerformancePage loads all 7 required workstation tabs."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    assert page.tabs.count() == 7
    expected_tabs = [
        "Overview Dashboard",
        "Data Parallelism",
        "Task Parallelism",
        "CPU Scheduling",
        "Virtual Lab",
        "Benchmark History",
        "Amdahl's Law",
    ]
    for idx, expected_name in enumerate(expected_tabs):
        assert page.tabs.tabText(idx) == expected_name


def test_amdahl_slider_interactive_updates(qapp, tmp_path):
    """Verify that moving sliders updates theoretical predictions and chart in real time."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    # Move parallel fraction to 80% (P = 0.8) and processors to 4
    page.amdahl_slider_p.setValue(80)
    page.amdahl_slider_n.setValue(4)

    assert "80.0%" in page.amdahl_lbl_p_val.text()
    assert "20.0%" in page.amdahl_lbl_p_val.text()
    assert "4 Cores" in page.amdahl_lbl_n_val.text()

    # S(0.8, 4) = 2.5x, Eff = 62.5%, S_max = 5.0x
    assert page.amdahl_card_speedup.value_label.text() == "2.50 x"
    assert page.amdahl_card_eff.value_label.text() == "62.5 %"
    assert page.amdahl_card_max_speedup.value_label.text() == "5.00 x"
    assert page.amdahl_card_serial_frac.value_label.text() == "20.0 %"

    # Move parallel fraction to 100% (P = 1.0)
    page.amdahl_slider_p.setValue(100)
    assert "100.0%" in page.amdahl_lbl_p_val.text()
    assert "0.0%" in page.amdahl_lbl_p_val.text()
    assert page.amdahl_card_max_speedup.value_label.text() == "Unbounded (∞)"
    assert "Zero Serial Bottleneck" in page.amdahl_card_max_speedup.subtitle_label.text()


def test_render_data_parallel_benchmark_results(qapp, tmp_path):
    """Verify Data Parallel benchmark session result renders metrics, table, and charts."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    rec_warmup = BenchmarkIterationRecord(
        iteration_idx=1,
        is_warmup=True,
        sequential_time_s=0.010,
        parallel_time_s=0.005,
        speedup=2.0,
        efficiency_pct=50.0,
        throughput=2000.0,
        verification_passed=True,
        extra_metrics={"startup_s": 0.001, "dispatch_s": 0.0005, "collection_s": 0.0005, "merge_s": 0.0005, "estimated_distribution_overhead_s": 0.0025},
    )
    rec_measured = BenchmarkIterationRecord(
        iteration_idx=1,
        is_warmup=False,
        sequential_time_s=0.008,
        parallel_time_s=0.002,
        speedup=4.0,
        efficiency_pct=100.0,
        throughput=5000.0,
        verification_passed=True,
        extra_metrics={"startup_s": 0.0002, "dispatch_s": 0.0001, "collection_s": 0.0001, "merge_s": 0.0001, "estimated_distribution_overhead_s": 0.0005},
    )

    session = BenchmarkSessionResult(
        benchmark_id="dp_test_001",
        engine_type=BenchmarkEngineType.DATA_PARALLEL,
        workload_name="Test Transcendental",
        worker_count=4,
        config_parameters={"op_id": "transcendental", "dataset_size": 10000, "worker_count": 4},
        hardware_metadata={"cpu_model": "Host Processor"},
        start_timestamp="2026-11-06T12:00:00Z",
        end_timestamp="2026-11-06T12:00:01Z",
        total_wall_clock_s=0.015,
        iterations_requested=1,
        warmup_iterations_requested=1,
        warmup_records=[rec_warmup],
        measured_records=[rec_measured],
        statistics={
            "speedup": {"mean": 4.0, "std_dev": None},
            "efficiency_pct": {"mean": 100.0, "std_dev": None},
            "throughput": {"mean": 5000.0, "std_dev": None},
        },
        verification_passed=True,
    )

    page._render_dp_results(session)

    assert "4.00 x" in page.dp_card_speedup.value_label.text()
    assert "N/A (N=1 iteration)" in page.dp_card_speedup.subtitle_label.text()
    assert "100.0 %" in page.dp_card_efficiency.value_label.text()
    assert page.dp_table.rowCount() == 2
    assert page.dp_table.item(0, 1).text() == "Warm-up"
    assert page.dp_table.item(1, 1).text() == "Measured"


def test_render_task_parallel_benchmark_results(qapp, tmp_path):
    """Verify Task Parallel DAG benchmark session result renders metrics, table, and charts."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    rec = BenchmarkIterationRecord(
        iteration_idx=1,
        is_warmup=False,
        sequential_time_s=0.050,
        parallel_time_s=0.020,
        speedup=2.5,
        efficiency_pct=62.5,
        throughput=200.0,
        verification_passed=True,
        extra_metrics={
            "parallelism_ratio": 2.2,
            "worker_utilization_pct": 55.0,
            "cumulative_compute_s": 0.044,
        },
    )

    session = BenchmarkSessionResult(
        benchmark_id="tp_test_001",
        engine_type=BenchmarkEngineType.TASK_PARALLEL,
        workload_name="Task DAG (Diamond)",
        worker_count=4,
        config_parameters={"dag_type": "diamond", "worker_count": 4},
        hardware_metadata={"cpu_model": "Host Processor"},
        start_timestamp="2026-11-06T12:00:00Z",
        end_timestamp="2026-11-06T12:00:01Z",
        total_wall_clock_s=0.050,
        iterations_requested=1,
        warmup_iterations_requested=0,
        warmup_records=[],
        measured_records=[rec],
        statistics={
            "speedup": {"mean": 2.5, "std_dev": None},
            "efficiency_pct": {"mean": 62.5, "std_dev": None},
        },
        verification_passed=True,
    )

    page._render_tp_results(session)

    assert "2.50 x" in page.tp_card_actual_speedup.value_label.text()
    assert "N/A (N=1 iteration)" in page.tp_card_actual_speedup.subtitle_label.text()
    assert "2.20 x" in page.tp_card_parallelism_ratio.value_label.text()
    assert "55.0 %" in page.tp_card_utilization.value_label.text()
    assert page.tp_table.rowCount() == 1


def test_render_scheduling_benchmark_results(qapp, tmp_path):
    """Verify CPU Scheduling comparative benchmark populates ranking cards and matrix table."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    rec1 = BenchmarkIterationRecord(
        iteration_idx=1,
        is_warmup=False,
        sequential_time_s=10.0,
        parallel_time_s=10.0,
        speedup=1.0,
        efficiency_pct=90.0,
        throughput=0.5,
        verification_passed=True,
        extra_metrics={
            "algorithm_name": "Round Robin",
            "algorithm_type": "Preemptive",
            "average_waiting_time": 4.5,
            "average_turnaround_time": 8.5,
            "context_switches": 6,
        },
    )
    rec2 = BenchmarkIterationRecord(
        iteration_idx=2,
        is_warmup=False,
        sequential_time_s=10.0,
        parallel_time_s=10.0,
        speedup=1.0,
        efficiency_pct=95.0,
        throughput=0.6,
        verification_passed=True,
        extra_metrics={
            "algorithm_name": "FCFS",
            "algorithm_type": "Non-preemptive",
            "average_waiting_time": 3.0,
            "average_turnaround_time": 7.0,
            "context_switches": 0,
        },
    )

    session = BenchmarkSessionResult(
        benchmark_id="sched_test_001",
        engine_type=BenchmarkEngineType.CPU_SCHEDULING,
        workload_name="Scheduler (Staggered)",
        worker_count=1,
        config_parameters={},
        hardware_metadata={},
        start_timestamp="2026-11-06T12:00:00Z",
        end_timestamp="2026-11-06T12:00:01Z",
        total_wall_clock_s=0.01,
        iterations_requested=2,
        warmup_iterations_requested=0,
        warmup_records=[],
        measured_records=[rec1, rec2],
        statistics={},
        verification_passed=True,
    )

    page._render_sched_results(session)

    assert "3.00" in page.sched_card_best_wait.value_label.text()
    assert "7.00" in page.sched_card_best_turnaround.value_label.text()
    assert "0 switches" in page.sched_card_lowest_cs.value_label.text()
    assert "95.0 %" in page.sched_card_max_util.value_label.text()
    assert page.sched_table.rowCount() == 2


def test_render_virtual_lab_benchmark_results(qapp, tmp_path):
    """Verify Virtual Lab multicore simulation result populates discrete tick metrics."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    rec = BenchmarkIterationRecord(
        iteration_idx=1,
        is_warmup=False,
        sequential_time_s=120.0,
        parallel_time_s=120.0,
        speedup=6.0,
        efficiency_pct=75.0,
        throughput=50.0,
        verification_passed=True,
        extra_metrics={
            "ticks_elapsed": 120,
            "virtual_cores": 8,
            "completed_tasks": 50,
            "virtual_util_pct": 75.0,
            "is_simulated": True,
        },
    )

    session = BenchmarkSessionResult(
        benchmark_id="vlab_test_001",
        engine_type=BenchmarkEngineType.VIRTUAL_LAB,
        workload_name="Virtual Lab Multicore (8 Cores)",
        worker_count=8,
        config_parameters={"virtual_cores": 8, "task_count": 50},
        hardware_metadata={},
        start_timestamp="2026-11-06T12:00:00Z",
        end_timestamp="2026-11-06T12:00:01Z",
        total_wall_clock_s=0.05,
        iterations_requested=1,
        warmup_iterations_requested=0,
        warmup_records=[],
        measured_records=[rec],
        statistics={},
        verification_passed=True,
    )

    page._render_vlab_results(session)

    assert "120 ticks" in page.vlab_card_ticks.value_label.text()
    assert "75.0 %" in page.vlab_card_util.value_label.text()
    assert "50.00" in page.vlab_card_throughput.value_label.text()
    assert "50 / 50" in page.vlab_card_verified.value_label.text()


def test_benchmark_history_table_and_details_viewer(qapp, tmp_path):
    """Verify persistent benchmark history table loading and JSON details inspection."""
    hist_dir = tmp_path / "benchmarks"
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(hist_dir)
    hist_mgr = BenchmarkHistoryManager(storage_dir=hist_dir)

    session = BenchmarkSessionResult(
        benchmark_id="dp_sample_01",
        engine_type=BenchmarkEngineType.DATA_PARALLEL,
        workload_name="Prime Sieve",
        worker_count=4,
        config_parameters={"op_id": "prime_sieve"},
        hardware_metadata={"cpu_model": "Host CPU"},
        start_timestamp="2026-11-06T10:00:00Z",
        end_timestamp="2026-11-06T10:00:01Z",
        total_wall_clock_s=1.0,
        iterations_requested=1,
        warmup_iterations_requested=0,
        warmup_records=[],
        measured_records=[],
        statistics={"speedup": {"mean": 3.5}, "efficiency_pct": {"mean": 87.5}},
        verification_passed=True,
    )
    hist_mgr.save_session(session)

    page = PerformancePage()
    assert page.hist_table.rowCount() == 1
    assert page.hist_table.item(0, 0).text() == "dp_sample_01"
    assert "Prime Sieve" in page.hist_table.item(0, 2).text()
    assert page.hist_table.item(0, 4).text() == "3.50x"

    # Select row and inspect details viewer
    page.hist_table.selectRow(0)
    assert "dp_sample_01" in page.hist_details_text.toPlainText()
    assert "Prime Sieve" in page.hist_details_text.toPlainText()

    # Delete selected
    page._delete_selected_history()
    assert page.hist_table.rowCount() == 0
    assert page.hist_details_text.toPlainText() == ""


def test_custom_painter_widgets_rendering(qapp):
    """Verify that custom QPainter canvas widgets paint offscreen without exceptions."""
    w1 = AmdahlCurveWidget()
    w1.set_parameters(0.85, 8, 32)
    w1.repaint()

    w2 = ScalabilityChartWidget()
    w2.set_data([(1, 1.0, 100.0), (2, 1.9, 95.0), (4, 3.6, 90.0)], title="Test Speedup")
    w2.repaint()

    w3 = TimingBreakdownWidget()
    w3.set_timings({"startup_s": 0.001, "compute_s": 0.010, "merge_s": 0.002})
    w3.repaint()


def test_dashboard_tab_hardware_and_provenance_labels(qapp, tmp_path):
    """Verify that Overview Dashboard renders hardware topology and classification labels."""
    os.environ["CORESYNC_BENCHMARK_DIR"] = str(tmp_path / "benchmarks")
    page = PerformancePage()

    # Find labels in dashboard tab
    dash_widget = page.tabs.widget(0)
    all_labels = [lbl.text() for lbl in dash_widget.findChildren(QLabel)]
    all_text = " ".join(all_labels)

    # Must mention physical cores, logical processors, and monotonic time
    assert "14 Physical Cores" in all_text or "Physical Cores:" in all_text
    assert "Logical Processors" in all_text or "Logical Threads:" in all_text
    assert "time.perf_counter_ns" in all_text
    assert "ESTIMATED_RESIDUAL" in all_text
    assert "SIMULATED_VIRTUAL" in all_text

