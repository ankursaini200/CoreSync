# CoreSync

> **Multicore Processing and Parallelism Simulator**  
> An advanced Operating Systems academic desktop workstation demonstrating actual concurrent CPU execution, Data Parallelism, and Task Parallelism.

---

## 1. Overview

**CoreSync** is an educational and analytical desktop application engineered to demonstrate, benchmark, and visualize true parallel processing on modern multicore CPUs. Unlike simple instructional tools that mock execution with timers or synthetic graphs, CoreSync:
- Spawns real, isolated operating system processes using Python's `multiprocessing` library (`spawn` context).
- Deeply inspects host CPU topology via Linux `sysfs` (`/sys/devices/system/cpu/`) and `psutil`.
- Differentiates between physical cores, logical hyperthreads, Performance (P) cores, and Efficiency (E) cores.
- Demonstrates actual **Data Parallelism** (chunk partitioning, parallel computation, result gather and verification).
- Demonstrates actual **Task Parallelism** (heterogeneous CPU-bound workloads, dependency graphs, priority scheduling).
- Clarifies the boundary between user-space educational dispatchers (FCFS, Priority, Round Robin) and preemptive kernel scheduling (Linux CFS/EEVDF).
- Empirically quantifies speedup, parallel efficiency, process spawn latency, and communication overhead.

---

## 2. Tech Stack

- **Language & Runtime**: Python 3.14+ (Arch Linux x86_64)
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
│   ├── main_window.py           # Master container window & sidebar router
│   ├── styles.py                # Modern dark workstation palette & QSS
│   └── components/              # Reusable UI widgets
│
├── engine/                      # Computation & Concurrency Layer
│   ├── worker.py                # Pure Python worker entrypoint (ZERO Qt imports)
│   └── process_manager.py       # Worker lifecycle & graceful termination
│
├── monitoring/                  # System & Performance Metrics
│   └── metrics.py               # Speedup, efficiency, and overhead math
│
├── utils/                       # Foundation Utilities
│   ├── system_info.py           # Linux sysfs & hardware topology probe
│   ├── config.py                # Configuration constants
│   ├── logging_config.py        # Structured logging
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
- [ ] **Phase 3**: Dark Workstation GUI Shell & Sidebar Navigation.
- [ ] **Phase 4**: Hardware Detection & Live Per-Core CPU Monitor.
- [ ] **Phase 5**: Data Parallelism Engine & Verification.
- [ ] **Phase 6**: Task Parallelism Engine & DAG Scheduling.
- [ ] **Phase 7**: Process Lifecycle Management & CPU Affinity Binding.
- [ ] **Phase 8**: Educational Scheduling Simulation (FCFS, Priority, Round Robin).
- [ ] **Phase 9**: Performance Analytics & Amdahl's Law Visualizer.
- [ ] **Phase 10**: Integration Testing, Hardening & Final Documentation.

