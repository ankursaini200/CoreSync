# Changelog

All notable changes to the CoreSync project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - Phase 3: Dark GUI Shell, Sidebar Navigation & View Routing

### Added
- Reusable UI component library (`gui/components/`):
  - `StatusBadge`: Colored status indicator pills.
  - `MetricCard`: Rounded KPI card with title, status, primary metric, subtitle, and progress bar.
  - `HeaderBar`: Top application bar with dynamic breadcrumbs, page title, and hardware status tags.
  - `ActionCard`: Interactive launch cards with description and navigation callbacks.
- Expanded modern dark workstation stylesheet (`gui/styles.py`) matching professional system monitoring tools.
- Implemented all 7 functional view modules:
  - `gui/dashboard.py`: Workstation overview, genuine hardware detection, metric cards, module launchers.
  - `gui/data_parallelism.py`: Data parallelism chunking controls, numerical kernel selection, Amdahl speedup summary.
  - `gui/task_parallelism.py`: Heterogeneous workload selector, priority dispatching, and task queue status.
  - `gui/core_monitor.py`: CPU topology overview, P-core / E-core classification, and affinity preset masks.
  - `gui/scheduler_view.py`: Educational dispatch policies (FCFS, Priority, Round Robin) and timeline preview.
  - `gui/performance.py`: Empirical speedup and efficiency benchmarking sweep parameters.
  - `gui/settings.py`: Lifecycle timeouts, topology detection methods, and runtime diagnostics.
- Master container routing in `gui/main_window.py` with responsive sidebar categories and `QStackedWidget` page switching.
- Automated GUI test suite in `tests/test_gui_navigation.py` covering all 7 pages, navigation switching, and resizing.

## [0.1.0] - Phase 2: Project Skeleton & Environment Setup

### Added
- Virtual environment setup with `--system-site-packages` for Arch Linux PEP 668 compliance.
- Dependency compatibility verification for Python 3.14.9, PySide6 6.12, NumPy 2.5, psutil 7.2, Matplotlib, and pytest.
- Modular architecture skeleton across `gui/`, `engine/`, `monitoring/`, `utils/`, and `tests/`.
- Isolated worker module (`engine/worker.py`) with zero PySide6/Qt dependencies to ensure clean child processes under `spawn` context.
- Centralized configuration (`utils/config.py`) and logging (`utils/logging_config.py`).
- Runtime dependency checker script (`utils/check_deps.py`).
- Minimal dark-themed PySide6 application entry point (`main.py` and `gui/main_window.py`).
- Baseline test suite (`tests/conftest.py`, `tests/test_environment.py`).

