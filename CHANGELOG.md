# Changelog

All notable changes to the CoreSync project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

