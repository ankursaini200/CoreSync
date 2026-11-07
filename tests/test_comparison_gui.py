"""GUI Tests for CoreSync Phase 10 Comparison Workstation Page."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

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
from gui.comparison import ComparisonPage, ExecutionTimelineWidget


def test_comparison_page_init(qapp):
    """Verify that ComparisonPage initializes all UI components and default configuration."""
    page = ComparisonPage()
    assert page is not None

    # Verify mode radio buttons exist
    assert hasattr(page, "rb_compare_both")
    assert hasattr(page, "rb_real_only")
    assert hasattr(page, "rb_virtual_only")
    assert page.rb_compare_both.isChecked()

    # Verify paradigm combo
    assert hasattr(page, "combo_paradigm")
    assert page.combo_paradigm.count() == 2

    # Verify action buttons
    assert hasattr(page, "btn_run")
    assert hasattr(page, "btn_cancel")
    assert hasattr(page, "btn_reset")
    assert page.btn_run.isEnabled()
    assert not page.btn_cancel.isEnabled()

    page.shutdown()


def test_comparison_page_paradigm_switching(qapp):
    """Verify switching between Data Parallelism and Task Parallelism updates operations."""
    page = ComparisonPage()

    # Initial is Data Parallelism (index 0)
    assert page.combo_paradigm.currentIndex() == 0
    assert page.slider_dataset.isEnabled()
    assert page.combo_workload.count() > 0

    # Switch to Task Parallelism (index 1)
    page.combo_paradigm.setCurrentIndex(1)
    assert page.slider_dataset.isHidden()
    assert page.combo_workload.count() > 0

    # Switch back to Data Parallelism
    page.combo_paradigm.setCurrentIndex(0)
    assert not page.slider_dataset.isHidden()

    page.shutdown()


def test_comparison_page_mode_switching(qapp):
    """Verify switching execution modes toggles controls appropriately."""
    page = ComparisonPage()

    # Mode: Real Only
    page.rb_real_only.setChecked(True)
    page._on_mode_changed(page.rb_real_only)
    cfg = page._build_configuration()
    assert cfg.execution_mode == ComparisonExecutionMode.REAL_ONLY

    # Mode: Virtual Only
    page.rb_virtual_only.setChecked(True)
    page._on_mode_changed(page.rb_virtual_only)
    cfg = page._build_configuration()
    assert cfg.execution_mode == ComparisonExecutionMode.VIRTUAL_ONLY

    # Mode: Compare Both
    page.rb_compare_both.setChecked(True)
    page._on_mode_changed(page.rb_compare_both)
    cfg = page._build_configuration()
    assert cfg.execution_mode == ComparisonExecutionMode.COMPARE_BOTH

    page.shutdown()


def test_comparison_page_display_session_results(qapp):
    """Verify that receiving a ComparisonSessionResult updates UI cards, tables, and timelines."""
    page = ComparisonPage()

    real_res = RealExecutionResult(
        status="completed",
        wall_clock_time_s=0.456,
        worker_count=2,
        worker_intervals=[(0.05, 0.45)],
        aggregate_worker_compute_time_s=0.40,
        compute_interval_union_s=0.40,
        no_worker_compute_time_s=0.056,
        worker_utilization_pct=87.7,
        peak_memory_rss_mb=42.0,
        task_completions=[
            {"task_id": "chunk_0", "process_id": 5001, "duration_s": 0.20},
            {"task_id": "chunk_1", "process_id": 5002, "duration_s": 0.20},
        ],
    )
    virt_res = VirtualExecutionResult(
        status="completed",
        virtual_makespan_ticks=80,
        simulated_clock_ticks=80,
        virtual_core_utilization_pct=78.5,
        virtual_core_count=2,
        virtual_core_allocation={0: ["chunk_0"], 1: ["chunk_1"]},
        task_completion_order=[
            {"task_id": "chunk_0", "assigned_core_id": 0, "finish_tick": 40, "waiting_ticks": 0},
            {"task_id": "chunk_1", "assigned_core_id": 1, "finish_tick": 40, "waiting_ticks": 0},
        ],
    )
    analysis = ComparisonAnalysis(
        workload_equivalence=True,
        workload_equivalence_details="Verified identical mathematical kernel inputs.",
        task_count_match=True,
        completion_order_concordance=1.0,
        resource_allocation_ratio=1.0,
        real_worker_count=2,
        virtual_core_count=2,
        real_utilization_pct=87.7,
        virtual_utilization_pct=78.5,
        utilization_difference_pct=9.2,
    )
    session = ComparisonSessionResult(
        comparison_id="gui-test-01",
        timestamp="2026-11-07T12:00:00Z",
        configuration=page._build_configuration(),
        real_result=real_res,
        virtual_result=virt_res,
        analysis=analysis,
        success=True,
    )

    page._on_comparison_finished(session)

    # Check metric cards
    assert "456.00 ms" in page.card_r_makespan.value_label.text()
    assert "80 ticks" in page.card_v_makespan.value_label.text()
    assert "Verified" in page.card_c_equiv.value_label.text()
    assert "1.00" in page.card_c_ratio.value_label.text()

    # Check table rows populated
    assert page.comp_table.rowCount() == 2
    assert page.comp_table.item(0, 0).text() == "chunk_0"
    assert page.comp_table.item(0, 6).text() == "Verified"

    page.shutdown()


def test_timeline_canvas_painting(qapp):
    """Verify execution timeline widget handles track updates and repaints cleanly."""
    canvas = ExecutionTimelineWidget(domain_label="seconds")
    tracks = [
        {
            "track_id": "Worker 0",
            "intervals": [(0.0, 0.5, Qt.blue)],
        },
        {
            "track_id": "Worker 1",
            "intervals": [(0.1, 0.6, Qt.green)],
        },
    ]
    canvas.set_timeline_data(tracks, max_val=1.0)
    canvas.resize(400, 150)
    canvas.repaint()
    assert len(canvas._tracks) == 2
