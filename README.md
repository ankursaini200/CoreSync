# CoreSync

> **Multicore Processing and Parallelism Simulator**  
> An advanced Operating Systems academic desktop workstation demonstrating actual concurrent CPU execution, Data Parallelism, and Task Parallelism.

---

## 1. Overview

**CoreSync** is an educational and analytical desktop application engineered to demonstrate, benchmark, and visualize true parallel processing on modern multicore CPUs. It provides **two distinct operating environments**:

1. **Real System**:
   - Deeply inspects host CPU topology via Linux `sysfs` (`/sys/devices/system/cpu/`), `/proc/cpuinfo`, and `psutil`.
   - Differentiates physical cores, logical hyperthreads, Performance (P) cores, and Efficiency (E) cores (authoritative Intel PMU classification and Apple Silicon perf levels).
   - Inspects running OS processes, memory RSS, and active CoreSync child worker processes.
   - Includes a safe, user-initiated **Real CPU Stress Tool** with duty-cycle throttling and a 30-second safety cap.
   - Spawns real, isolated operating system processes using Python's `multiprocessing` library (`spawn` context).

2. **Virtual Lab**:
   - Allows users to architect and experiment with software-simulated multicore processors (1 to 128 virtual cores, 1 to 256 threads).
   - Models heterogeneous hybrid computing with configurable P-Core and E-Core speed multipliers.
   - Simulates multicore dispatching and educational scheduling policies (FCFS, Priority, and Round Robin with time-quantum preemption).
   - Keeps virtual simulation metrics strictly decoupled from actual host hardware metrics.

---

## 2. Tech Stack

- **Language & Runtime**: Python 3.14+ (Arch Linux x86_64, cross-platform ready)
- **GUI Framework**: PySide6 (Qt 6.12)
- **Parallel Engine**: Python `multiprocessing` (isolated worker architecture, `spawn` start method)
- **Numerical Computing**: NumPy 2.5+
- **Monitoring & Affinity**: `psutil` 7.2+, Linux `sysfs` (`core_id`, `thread_siblings_list`, `cpufreq`)
- **Performance Visualization**: Matplotlib
- **Testing & Verification**: pytest, pytest-qt

---

## 3. Architecture & Directory Layout

```
CoreSync/
│
├── main.py                      # Application entry point & Qt event loop
├── requirements.txt             # Pinned production dependencies
├── requirements-dev.txt         # Development & testing dependencies
├── pyproject.toml               # Packaging & pytest configuration
├── README.md                    # Project documentation
├── CHANGELOG.md                 # Milestone & version history
│
├── gui/                         # Presentation Layer (PySide6)
│   ├── main_window.py           # Master container window & 11-page sidebar router
│   ├── dashboard.py             # System overview & live RAM/CPU telemetry
│   ├── core_monitor.py          # Real CPU core topology & per-core meters
│   ├── real_system/             # Real hardware views (Process monitor & Stress tool)
│   ├── virtual_lab/             # Virtual Lab views (CPU architect, Core matrix, Scheduler)
│   ├── styles.py                # Modern dark workstation palette & QSS
│   └── components/              # Reusable UI widgets (cards, badges, header)
│
├── engine/                      # Computation & Concurrency Layer
│   ├── data_parallel/           # Actual Data Parallelism engine (partitioner, workers, collector, verification)
│   ├── real_system/             # Genuine multi-process CPU stress generator
│   ├── virtual_lab/             # Software virtual CPU, cores, tasks, & scheduler
│   ├── worker.py                # Pure Python worker entrypoint (ZERO Qt imports)
│   └── process_manager.py       # Worker lifecycle & graceful termination
│
├── monitoring/                  # Real-Time Telemetry & Metrics
│   ├── cpu_monitor.py           # Asynchronous QThread CPU/RAM/process sampler
│   └── metrics.py               # Speedup, efficiency, and overhead math
│
├── utils/                       # Foundation & Hardware Utilities
│   ├── hardware/                # Platform providers (Linux, Windows, Darwin) & factory
│   ├── cpu_topology.py          # Linux sysfs CPU topology & PMU parser
│   ├── system_info.py           # System hardware detection consolidation
│   ├── config.py                # Configuration constants
│   └── logging_config.py        # Structured logging
│
└── tests/                       # Automated Test Suite (44 passing tests)
    ├── conftest.py              # Test fixtures & Qt offscreen config
    ├── test_hardware_providers.py # Cross-platform provider tests
    ├── test_virtual_lab.py      # Virtual multicore simulation tests
    ├── test_real_stress.py      # Stress safety & orphan process tests
    ├── test_cpu_topology.py     # Sysfs parsing tests
    ├── test_cpu_monitor.py      # QThread sampler tests
    ├── test_gui_navigation.py   # GUI page routing & switching tests
    ├── test_system_info.py      # System detection tests
    └── test_environment.py      # Environment & worker isolation tests
```
│   └── check_deps.py            # Runtime dependency verification script
│
└── tests/                       # Automated Test Suite (pytest)
    ├── conftest.py              # Test fixtures
    └── test_environment.py      # Dependency & environment sanity tests
```

---

## 4. Setup & Installation

### Arch Linux / Linux (PEP 668 Compliant)

1. Clone or navigate to the repository:
   ```bash
   cd CoreSync
   ```

2. Create a virtual environment inheriting system site packages (enables hardware-optimized PySide6 and NumPy):
   ```bash
   python3 -m venv --system-site-packages .venv
   source .venv/bin/activate
   ```

3. Install testing and graphing dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Verify all dependencies:
   ```bash
   python utils/check_deps.py
   ```

5. Run the test suite:
   ```bash
   pytest
   ```

6. Launch the application:
   ```bash
   python main.py
   ```

---

## 5. Development Status

- [x] **Phase 1**: Architecture, Requirements, and Phased Roadmap.
- [x] **Phase 2**: Environment Setup, Project Skeleton, and Initial Entry Point.
- [x] **Phase 3**: Dark Workstation GUI Shell & Sidebar Navigation.
- [x] **Phase 4**: Hardware Detection, Live Core Monitoring & Dual-Environment Expansion (Real System + Virtual Lab).
- [x] **Phase 5**: Data Parallelism Engine & Verification.
- [ ] **Phase 6**: Task Parallelism Engine & DAG Scheduling.
- [ ] **Phase 7**: Process Lifecycle Management & CPU Affinity Binding.
- [ ] **Phase 8**: Educational Scheduling Simulation (FCFS, Priority, Round Robin).
- [ ] **Phase 9**: Performance Analytics & Amdahl's Law Visualizer.
- [ ] **Phase 10**: Integration Testing, Hardening & Final Documentation.

