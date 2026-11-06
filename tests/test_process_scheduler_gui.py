"""Automated GUI Tests for CoreSync Process Scheduler Page."""

from unittest.mock import patch
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QTableWidget

from engine.process_scheduler import AlgorithmType, Process
from gui.scheduler_view import ComparisonDialog, SchedulerViewPage


def test_scheduler_view_page_initialization(qtbot):
    """Verify that SchedulerViewPage initializes with default preset and populated table."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    assert page.table_processes.rowCount() > 0
    assert page.combo_algo.count() == 6
    assert page.btn_run.isEnabled()
    assert page.btn_compare.isEnabled()
    assert page.gantt_widget is not None


def test_scheduler_view_add_and_delete_process(qtbot):
    """Verify adding and deleting processes through GUI controls."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    initial_count = page.table_processes.rowCount()

    # Add a custom process
    page.edit_pid.setText("P_CUSTOM")
    page.spin_arrival.setValue(3.5)
    page.spin_burst.setValue(6.0)
    page.spin_priority.setValue(2)

    page._on_add_process()
    assert page.table_processes.rowCount() == initial_count + 1
    assert page._processes[-1].process_id == "P_CUSTOM"
    assert page._processes[-1].arrival_time == 3.5
    assert page._processes[-1].burst_time == 6.0

    # Delete the newly added process
    last_idx = len(page._processes) - 1
    page._on_delete_process(last_idx)
    assert page.table_processes.rowCount() == initial_count


def test_scheduler_view_clear_all(qtbot):
    """Verify clearing all processes."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)
    assert len(page._processes) > 0

    page._on_clear_processes()
    assert len(page._processes) == 0
    assert page.table_processes.rowCount() == 0


def test_scheduler_view_load_presets(qtbot):
    """Verify loading different educational presets."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    # Find index for round_robin_preemption preset
    idx = page.combo_presets.findData("round_robin_preemption")
    assert idx >= 0
    page.combo_presets.setCurrentIndex(idx)
    page._on_load_preset()

    assert len(page._processes) == 3
    assert page._processes[0].process_id == "P1"
    assert page._processes[0].burst_time == 24.0

    # Simulation should have automatically run
    assert page._last_simulation_result is not None
    assert page.table_results.rowCount() == 3


def test_scheduler_view_algorithm_switching_parameter_toggles(qtbot):
    """Verify that switching algorithms dynamically enables/disables relevant parameters."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    # 1. FCFS: Quantum and Priority Direction disabled
    page.combo_algo.setCurrentIndex(0)
    assert not page.spin_quantum.isEnabled()
    assert not page.combo_direction.isEnabled()
    assert not page.chk_aging.isEnabled()

    # 2. Priority Scheduling (Non-Preemptive): Priority Direction enabled
    prio_idx = page.combo_algo.findData(AlgorithmType.PRIORITY_NON_PREEMPTIVE)
    page.combo_algo.setCurrentIndex(prio_idx)
    assert not page.spin_quantum.isEnabled()
    assert page.combo_direction.isEnabled()
    assert page.chk_aging.isEnabled()

    # 3. Round Robin: Quantum enabled
    rr_idx = page.combo_algo.findData(AlgorithmType.ROUND_ROBIN)
    page.combo_algo.setCurrentIndex(rr_idx)
    assert page.spin_quantum.isEnabled()
    assert not page.combo_direction.isEnabled()


def test_scheduler_view_run_simulation_updates_display(qtbot):
    """Verify running simulation updates Gantt chart, metrics cards, and results table."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    # Select SJF
    sjf_idx = page.combo_algo.findData(AlgorithmType.SJF)
    page.combo_algo.setCurrentIndex(sjf_idx)
    page.run_simulation()

    assert page._last_simulation_result is not None
    assert page.table_results.rowCount() == len(page._processes)

    # Metrics card checks
    assert "ms" in page.card_tat.value_label.text()
    assert "ms" in page.card_wt.value_label.text()
    assert "%" in page.card_util.value_label.text()
    assert page.card_util.value_label.text() != "-- %"

    # Gantt canvas timeline check
    assert page.gantt_widget.canvas._timeline is not None
    assert len(page.gantt_widget.canvas._timeline.blocks) > 0


def test_scheduler_comparison_dialog_rendering(qtbot):
    """Verify ComparisonDialog renders metrics rows across all algorithms."""
    from engine.process_scheduler import compare_all_algorithms, get_preset_by_id

    preset = get_preset_by_id("staggered_arrivals")
    procs = preset.get_cloned_processes()

    _, rows = compare_all_algorithms(procs, time_quantum=2.0)
    dialog = ComparisonDialog(rows)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Algorithm Comparison Benchmark"
    table = dialog.findChild(QTableWidget)
    assert table is not None
    assert table.rowCount() == 6
    assert table.columnCount() == 8


def test_scheduler_view_empty_process_list_handling(qtbot):
    """Verify that attempting to simulate with empty process list displays warning without crash."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)
    page._processes.clear()

    with patch.object(QMessageBox, "information") as mock_info:
        page.run_simulation()
        mock_info.assert_called_once()


def test_scheduler_view_invalid_input_validation(qtbot):
    """Verify input validation for empty PID and duplicate PID."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    # 1. Empty PID
    page.edit_pid.setText("")
    with patch.object(QMessageBox, "warning") as mock_warn:
        page._on_add_process()
        mock_warn.assert_called_once()

    # 2. Duplicate PID
    page.edit_pid.setText(page._processes[0].process_id)
    with patch.object(QMessageBox, "warning") as mock_warn:
        page._on_add_process()
        mock_warn.assert_called_once()


def test_scheduler_view_large_batch_and_long_timeline(qtbot):
    """Verify responsiveness with a large batch of 50 processes and a wide Gantt canvas."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)
    page._processes.clear()

    for i in range(50):
        page._processes.append(Process(process_id=f"P{i:02d}", arrival_time=float(i), burst_time=2.0))

    page.run_simulation()
    assert page.table_results.rowCount() == 50
    assert page._last_simulation_result is not None
    assert page.gantt_widget.canvas.minimumWidth() > 3000


def test_scheduler_view_zoom_and_canvas_controls(qtbot):
    """Verify zoom in and zoom out adjustments on the Gantt canvas."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    initial_zoom = page.gantt_widget._current_zoom
    page.gantt_widget.btn_zoom_in.click()
    assert page.gantt_widget._current_zoom > initial_zoom

    page.gantt_widget.btn_zoom_out.click()
    assert abs(page.gantt_widget._current_zoom - initial_zoom) < 1e-4


def test_scheduler_view_repeated_simulation_runs(qtbot):
    """Verify repeated simulations update metrics cards and results table without regression."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    for _ in range(5):
        page.run_simulation()

    assert page._last_simulation_result is not None
    assert page.table_results.rowCount() == len(page._processes)


def test_scheduler_view_compare_all_launches_dialog(qtbot):
    """Verify clicking Compare All opens the ComparisonDialog benchmark modal."""
    page = SchedulerViewPage()
    qtbot.addWidget(page)

    with patch.object(ComparisonDialog, "exec") as mock_exec:
        page._on_compare_all()
        mock_exec.assert_called_once()

