# Changelog

All notable changes to the CoreSync project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - Phase 4 Expansion: Real System + Virtual Lab + Cross-Platform Hardware Architecture

### Added
- **Cross-Platform Hardware Provider Abstraction Layer (`utils/hardware/`)**:
  - `BaseHardwareProvider` defining unified detection interface and data models (`HardwareInfo`, `RAMInfo`, `ProcessInfo`).
  - `LinuxHardwareProvider`: Linux implementation using sysfs topology, Intel PMU hybrid core detection, `/proc/cpuinfo`, and `psutil`.
  - `WindowsHardwareProvider`: Windows provider utilizing `platform` and native `psutil` CPU/memory APIs with graceful fallbacks.
  - `DarwinHardwareProvider`: macOS provider utilizing `sysctl` and `psutil` with Apple Silicon M-series Performance / Efficiency core detection.
  - `get_hardware_provider()` factory dynamically resolving platform at runtime.
  - Real RAM usage detection (`total_gb`, `used_gb`, `percent_used`).
  - Top OS process inspection with CPU%, memory RSS, and active CoreSync child worker identification.
- **Real CPU Stress Generator (`engine/real_system/cpu_stress.py`)**:
  - `RealCPUStressGenerator`: Spawns genuine CPU-bound worker processes under POSIX `spawn` method.
  - Worker loop isolated in non-GUI module with mathematical calculations (pure CPU load, zero Qt imports).
  - Explicit user initiation only (never automatic).
  - Conservative safety duration limit hard-capped at 30 seconds.
  - Duty-cycle throttling (10% to 100%) for proportional core heating and load scaling.
  - Three-stage process termination guarantee (Cooperative `Event` -> `SIGTERM` -> `SIGKILL`), ensuring zero orphan/zombie processes.
- **Virtual Multicore Lab Simulation Engine (`engine/virtual_lab/`)**:
  - `VirtualCPU` and `VirtualCPUConfig`: Simulated multicore processor supporting arbitrary topologies (1 to 128 virtual cores, 1 to 256 threads).
  - Heterogeneous hybrid architecture simulation: Configurable P-Core and E-Core ratios with asymmetric speed multipliers (e.g. 1.5x P-Cores, 0.8x E-Cores).
  - `VirtualCore`: Simulated core execution unit with discrete tick progression, task assignment, and simulated windowed duty cycle.
  - `VirtualTask` and `VirtualWorkloadGenerator`: Synthetic task models with priority levels, burst requirements, and reproducible task batch generation.
  - `VirtualScheduler`: Educational scheduling policies including FCFS, Priority Scheduling, and Round Robin (with time-quantum preemption), tracking waiting ticks, turnaround ticks, and core dispatching.
  - Pure software simulation: Virtual metrics are strictly decoupled from real host hardware and `psutil` metrics.
- **Expanded Modern Dark Workstation GUI (`gui/`)**:
  - `gui/real_system/process_view.py`: `RealProcessPage` inspecting live OS processes, top CPU consumers, and CoreSync workers.
  - `gui/real_system/stress_view.py`: `RealStressPage` with worker slider, duration spinner, duty-cycle slider, Start/Stop buttons, and live progress bars.
  - `gui/virtual_lab/config_view.py`: `VirtualConfigPage` providing hardware presets, core count spinners, hybrid toggles, and live topology summary.
  - `gui/virtual_lab/monitor_view.py`: `VirtualMonitorPage` featuring an interactive multicore matrix grid displaying per-virtual-core load, speed pills, and current tasks.
  - `gui/virtual_lab/scheduler_view.py`: `VirtualSchedulerPage` with algorithm selector, Round Robin quantum adjustment, workload injector, simulation step/run buttons, and live ready/completed queues.
  - `gui/dashboard.py`: Updated with host RAM usage card and 6 direct module launcher action cards.
  - `gui/main_window.py`: Reorganized 11-page routing with categorized sidebar (Overview, Real System, Virtual Lab, Parallel Processing, Analytics & Config).
- **Automated Test Suite Expansion (`tests/`)**:
  - 17 new tests: `test_hardware_providers.py`, `test_virtual_lab.py`, and `test_real_stress.py`.
  - Full suite now contains **44 passing tests** (100% pass rate).

## [0.3.0] - Phase 4: CPU Hardware Detection, Sysfs Topology & Live Core Monitoring

### Added
- Linux sysfs CPU topology parser (`utils/cpu_topology.py`):
  - Standard Linux CPU-list syntax parser (`parse_cpu_list`) supporting complex range combinations (e.g. `0-3,8-11,14`).
  - Physical socket package identification via `topology/physical_package_id`.
  - Physical core identification and SMT thread siblings detection via `topology/thread_siblings_list`.
  - Authoritative Intel Hybrid PMU core type detection (`/sys/bus/event_source/devices/cpu_core` for P-cores, `cpu_atom` for E-cores).
  - Deterministic unit test support using mock sysfs directory trees.
- Consolidated hardware & system information service (`utils/system_info.py`):
  - CPU model and vendor querying (`/proc/cpuinfo` with platform fallbacks).
  - Physical and logical core count consolidation.
  - Active process CPU affinity retrieval (`os.sched_getaffinity` / `psutil`).
  - CPU frequency range detection (`cpufreq`).
- Asynchronous CPU monitoring service (`monitoring/cpu_monitor.py`):
  - `CPUMonitorWorker` running in a dedicated `QThread` with periodic `QTimer` sampling.
  - `CPUMonitorService` singleton coordinator ensuring a single shared thread without UI event loop lag.
  - Clean QueuedConnection signal shutdown avoiding cross-thread timer warnings.
- GUI Dashboard & Core Monitor Integration:
  - `gui/core_monitor.py`: Real-time 20-core utilization grid with P-Core (`#388bfd`) and E-Core (`#a371f7`) badges, live percentage meters, and frequency indicators.
  - `gui/dashboard.py`: Live overall CPU utilization card and progress bar consuming the centralized monitoring service.
  - `gui/main_window.py`: Automatic thread lifecycle management on application startup and window close.
- 15 new automated unit & integration tests covering topology parsing, SMT detection, PMU hybrid classification, system summary consolidation, and monitor service lifecycle (total: 27 tests).

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

