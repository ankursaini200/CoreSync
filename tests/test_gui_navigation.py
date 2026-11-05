"""Automated GUI Navigation and Page Initialization Tests for CoreSync."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget

from gui.main_window import MainWindow
from gui.dashboard import DashboardPage
from gui.data_parallelism import DataParallelismPage
from gui.task_parallelism import TaskParallelismPage
from gui.core_monitor import CoreMonitorPage
from gui.scheduler_view import SchedulerViewPage
from gui.performance import PerformancePage
from gui.settings import SettingsPage


def test_main_window_all_seven_pages(qapp):
    """Verify that MainWindow initializes all 7 required pages."""
    window = MainWindow(start_monitor=False)
    assert window.pages.count() == 7

    assert isinstance(window.pages.widget(0), DashboardPage)
    assert isinstance(window.pages.widget(1), DataParallelismPage)
    assert isinstance(window.pages.widget(2), TaskParallelismPage)
    assert isinstance(window.pages.widget(3), CoreMonitorPage)
    assert isinstance(window.pages.widget(4), SchedulerViewPage)
    assert isinstance(window.pages.widget(5), PerformancePage)
    assert isinstance(window.pages.widget(6), SettingsPage)
    window.close()


def test_sidebar_navigation_switching(qapp):
    """Verify that clicking each of the 7 sidebar buttons switches the active page."""
    window = MainWindow(start_monitor=False)
    assert window.pages.currentIndex() == 0

    # Test navigating through all 7 pages via buttons
    for idx in range(7):
        btn = window.nav_buttons[idx]
        btn.click()
        assert window.pages.currentIndex() == idx
        assert btn.isChecked()

        section_name, _ = window.NAV_SECTIONS[idx]
        assert section_name in window.header_bar.breadcrumb_label.text()

    window.close()


def test_dashboard_quick_navigation_signals(qapp):
    """Verify that quick action cards on Dashboard trigger navigation."""
    window = MainWindow(start_monitor=False)
    assert window.pages.currentIndex() == 0

    # Request navigation to Data Parallelism (index 1)
    window.page_dashboard.navigate_requested.emit(1)
    assert window.pages.currentIndex() == 1
    assert window.nav_buttons[1].isChecked()

    # Request navigation to Performance Analytics (index 5)
    window.page_dashboard.navigate_requested.emit(5)
    assert window.pages.currentIndex() == 5
    assert window.nav_buttons[5].isChecked()

    window.close()


def test_window_resizing(qapp):
    """Test window resizing and ensure minimum geometry constraints."""
    window = MainWindow(start_monitor=False)
    window.resize(1024, 680)
    assert window.width() >= 1024
    assert window.height() >= 680

    window.resize(1600, 1000)
    assert window.width() == 1600
    assert window.height() == 1000
    window.close()

