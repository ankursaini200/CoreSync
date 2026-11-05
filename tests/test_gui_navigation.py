"""Automated GUI Navigation and Page Initialization Tests for CoreSync."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget

from gui.main_window import MainWindow
from gui.dashboard import DashboardPage
from gui.core_monitor import CoreMonitorPage
from gui.real_system.process_view import RealProcessPage
from gui.real_system.stress_view import RealStressPage
from gui.virtual_lab.config_view import VirtualConfigPage
from gui.virtual_lab.monitor_view import VirtualMonitorPage
from gui.virtual_lab.scheduler_view import VirtualSchedulerPage
from gui.data_parallelism import DataParallelismPage
from gui.task_parallelism import TaskParallelismPage
from gui.performance import PerformancePage
from gui.settings import SettingsPage


def test_main_window_all_pages(qapp):
    """Verify that MainWindow initializes all 11 workstation pages."""
    window = MainWindow(start_monitor=False)
    assert window.pages.count() == 11

    assert isinstance(window.pages.widget(0), DashboardPage)
    assert isinstance(window.pages.widget(1), CoreMonitorPage)
    assert isinstance(window.pages.widget(2), RealProcessPage)
    assert isinstance(window.pages.widget(3), RealStressPage)
    assert isinstance(window.pages.widget(4), VirtualConfigPage)
    assert isinstance(window.pages.widget(5), VirtualMonitorPage)
    assert isinstance(window.pages.widget(6), VirtualSchedulerPage)
    assert isinstance(window.pages.widget(7), DataParallelismPage)
    assert isinstance(window.pages.widget(8), TaskParallelismPage)
    assert isinstance(window.pages.widget(9), PerformancePage)
    assert isinstance(window.pages.widget(10), SettingsPage)
    window.close()


def test_sidebar_navigation_switching(qapp):
    """Verify that clicking each of the 11 sidebar buttons switches the active page."""
    window = MainWindow(start_monitor=False)
    assert window.pages.currentIndex() == 0

    for idx in range(11):
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

    # Request navigation to Core Monitor (index 1)
    window.page_dashboard.navigate_requested.emit(1)
    assert window.pages.currentIndex() == 1
    assert window.nav_buttons[1].isChecked()

    # Request navigation to Virtual CPU Config (index 4)
    window.page_dashboard.navigate_requested.emit(4)
    assert window.pages.currentIndex() == 4
    assert window.nav_buttons[4].isChecked()

    # Request navigation to Virtual Scheduler (index 6)
    window.page_dashboard.navigate_requested.emit(6)
    assert window.pages.currentIndex() == 6
    assert window.nav_buttons[6].isChecked()

    window.close()


def test_virtual_lab_inter_page_signals(qapp):
    """Verify that Virtual Lab configuration applies to monitor and scheduler."""
    window = MainWindow(start_monitor=False)
    assert len(window.virtual_cpu.cores) > 0

    # Simulate applying new config
    window.page_vconfig.spin_threads.setValue(8)
    window.page_vconfig.btn_apply.click()

    assert len(window.virtual_cpu.cores) == 8
    assert len(window.page_vmonitor.core_cards) == 8

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
