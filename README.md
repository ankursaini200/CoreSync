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
│   ├── process_manager.py       # Unified worker lifecycle coordinator & 4-stage shutdown
│   ├── affinity.py              # Cross-platform CPU affinity assignment & core allocation policies
│   ├── resource_guard.py        # Worker concurrency bounds, memory headroom & system load guard
│   ├── data_parallel/           # Actual Data Parallelism engine (partitioner, workers, collector, verification)
│   ├── task_parallel/           # Task Parallelism engine (DAG graph, queues, dispatcher, executor, verifier)
│   ├── real_system/             # Genuine multi-process CPU stress generator
│   ├── virtual_lab/             # Software virtual CPU, cores, tasks, & scheduler
│   └── worker.py                # Pure Python worker entrypoint (ZERO Qt imports)
│
├── monitoring/                  # Real-Time Telemetry & Metrics
│   ├── cpu_monitor.py           # Asynchronous QThread CPU/RAM/process sampler & worker registry
│   └── metrics.py               # Speedup, efficiency, and overhead math
│
├── utils/                       # Foundation & Hardware Utilities
│   ├── hardware/                # Platform providers (Linux, Windows, Darwin) & factory
│   ├── cpu_topology.py          # Linux sysfs CPU topology & PMU parser
│   ├── system_info.py           # System hardware detection consolidation
│   ├── config.py                # Configuration constants
│   └── logging_config.py        # Structured logging
│
└── tests/                       # Automated Test Suite (121 passing tests)
    ├── conftest.py              # Test fixtures & Qt offscreen config
    ├── test_process_manager.py  # Unified ProcessManager & CPU affinity tests (21 tests)
    ├── test_hardware_providers.py # Cross-platform provider tests
    ├── test_virtual_lab.py      # Virtual multicore simulation tests
    ├── test_real_stress.py      # Stress safety & orphan process tests
    ├── test_cpu_topology.py     # Sysfs parsing tests
    ├── test_cpu_monitor.py      # QThread sampler tests
    ├── test_gui_navigation.py   # GUI page routing & switching tests
    ├── test_system_info.py      # System detection tests
    ├── test_environment.py      # Environment & worker isolation tests
    ├── test_data_parallel.py    # Data Parallelism & timing breakdown tests
    └── test_task_parallel.py    # Task Parallelism DAG & benchmark tests
```

---

## 4. Benchmark Metric Definitions & Mathematical Foundations

CoreSync strictly separates measured execution intervals from derived estimates to maintain academic rigor:

### Data Parallelism Metrics
- **Sequential Baseline ($T_{\text{seq}}$)**: Wall-clock duration executing the single-threaded operation over the entire dataset.
- **Parallel Makespan ($T_{\text{par}}$)**: Wall-clock interval from worker process pool creation to output reassembly:
  $$T_{\text{total}} \approx T_{\text{spawn}} + T_{\text{dispatch}} + T_{\text{collection}} + T_{\text{merge}}$$
- **Speedup ($S$)**: $$S = \frac{T_{\text{seq}}}{T_{\text{par}}}$$
- **Parallel Efficiency ($E$)**: $$E = \frac{S}{\text{Worker Count}} \times 100\%$$
- **Input Delivery Latency**: Measured latency ($\Delta t = t_{\text{worker\_recv}} - t_{\text{master\_dispatch}}$) via shared `CLOCK_MONOTONIC`. Captures serialization, queue waiting, and Linux CFS scheduler wake-up time.
- **Estimated Distribution & Collection Overhead**: Derived residual gap:
  $$\text{Overhead}_{\text{est}} = T_{\text{dispatch}} + \max(0, T_{\text{collection}} - T_{\text{max\_worker\_compute}})$$

### Task Parallelism Metrics (DAG Workloads)
- **Sequential Baseline ($T_{\text{seq}}$)**: Wall-clock duration executing the exact same task graph sequentially in topological dependency order on 1 worker, using identical input parameters and seeds.
- **Parallel Makespan ($T_{\text{par}}$)**: Wall-clock interval from initial root dispatch to final leaf task completion across the worker process pool.
- **Actual Speedup ($S$)**:
  $$S = \frac{T_{\text{seq}}}{T_{\text{par}}}$$
  Measures the true performance multiplier achieved over single-threaded execution. Reported only when both runs succeed and outputs match mathematically.
- **Parallelism Ratio ($P$)**:
  $$P = \frac{\sum_{i=1}^{N} T_{\text{worker\_compute}, i}}{T_{\text{par}}}$$
  Quantifies the average concurrency density (effective number of workers actively computing concurrently during the parallel makespan window).
- **Worker Utilization ($U$)**:
  $$U = \frac{\sum_{i=1}^{N} T_{\text{worker\_compute}, i}}{\text{Worker Count} \times T_{\text{par}}} \times 100\%$$
  Percentage of total available worker compute capacity spent in active computation. Strictly bounded between **0.0% and 100.0%**. The remainder $(100\% - U)$ accounts for worker idle time, queue waiting, inter-task IPC transit, and dependency synchronization delays.

---

## 5. Output Verification Integrity & Equivalence Strategies

To guarantee scientific rigor, CoreSync distinguishes **Full Output Equivalence Verification** from **Summary / Invariant-Based Verification**:

| Workload Kernel | Verification Level | Verification Strategy | Discrepancies Caught |
| :--- | :--- | :--- | :--- |
| **`matrix_mult`** | **Full Output Equivalence** | Compares entire resulting matrices element-by-element via `np.allclose(mat_seq, mat_par, rtol=1e-5, atol=1e-8)`. Trace and Frobenius norm are retained as supplementary checks. | Catches matrices with matching trace/norm but altered internal elements. |
| **`sorting`** | **Full Output Equivalence** | Compares full sorted arrays element-by-element via `np.allclose(arr_seq, arr_par)` and checks monotonic ascending order (`np.all(arr[:-1] <= arr[1:])`). | Catches sorted arrays with identical min/max bounds but differing internal items. |
| **`fibonacci`** | **Full Output Equivalence** | Compares the complete exact big-integer value (`seq["fib_value"] == par["fib_value"]`). Digit count and trailing digits are retained as supplementary checks. | Catches arbitrary integers that share digit lengths and trailing digits. |
| **`prime_calc`** | **Full Output Equivalence** | Compares the complete sequence of computed prime integers (`seq["primes"] == par["primes"]`), with count and largest prime as supplementary checks. | Catches missing or erroneous primes in range. |
| **`data_transform`** | **Full Output Equivalence** | Compares the complete transformed floating-point vector element-by-element via `np.allclose()`. Mean and std are retained as supplementary checks. | Catches localized vector deviations that preserve summary moments. |
| **`numerical_integration`** | **Tolerance-Bounded Scalar** | Evaluates $|I_{\text{seq}} - I_{\text{par}}| \le \text{atol} + \text{rtol} \cdot |I_{\text{seq}}|$. As a mathematical reduction over a continuous function, verification validates the scalar integral value. | Catches Simpson quadrature calculation errors. |

> [!IMPORTANT]
> **Measurement Isolation**: Verification logic is executed **after** both sequential and parallel makespan intervals have concluded. Verification overhead is strictly excluded from reported execution timings. Any verification divergence invalidates the benchmark and resets `actual_speedup` to `0.0`.

---

## 6. Unified Process Management & CPU Affinity Subsystem

CoreSync coordinates all spawned worker processes across Data Parallelism, Task Parallelism, and Real CPU Stress through a centralized, cross-platform process management layer:

### Architecture
- **Unified Lifecycle Tracking**: Every worker process registers its OS PID, parent PID, engine identifier, task/chunk assignment, allocated logical CPU affinity mask, and lifecycle state (`INITIALIZING`, `RUNNING`, `IDLE`, `COMPLETED`, `FAILED`, `CANCELLED`, `TERMINATED`).
- **4-Stage Shutdown Protocol**: Guaranteed termination escalation without leaking zombie or orphan processes:
  1. Cooperative cancellation via shared `multiprocessing.Event`.
  2. Graceful `Process.terminate()` (`SIGTERM`).
  3. Forceful `Process.kill()` (`SIGKILL`).
  4. Final process reaping and join.
- **Orphan Detection & Reaping**: Background scan identifying any dangling CoreSync processes whose parent PID has exited, safely terminating them without touching unrelated user processes.
- **Resource Safeguards**: Automatic worker count clamping, available memory headroom verification, and worker memory threshold monitoring.

### CPU Affinity Policies
- **Automatic**: Default OS scheduling across all available logical cores.
- **Round Robin**: Sequential round-robin assignment of workers to available logical CPUs.
- **One-to-One Pinning**: Direct pinning of worker $i$ to logical CPU $i$.
- **Performance (P-Core) Only**: Strict pinning to verified Performance cores on hybrid architectures.
- **Efficiency (E-Core) Only**: Strict pinning to verified Efficiency cores on hybrid architectures.
- **Manual / Custom**: Explicit user-defined worker-to-core mapping.

---

## 7. Setup & Installation

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

## 7. Development Status

- [x] **Phase 1**: Architecture, Requirements, and Phased Roadmap.
- [x] **Phase 2**: Environment Setup, Project Skeleton, and Initial Entry Point.
- [x] **Phase 3**: Dark Workstation GUI Shell & Sidebar Navigation.
- [x] **Phase 4**: Hardware Detection, Live Core Monitoring & Dual-Environment Expansion (Real System + Virtual Lab).
- [x] **Phase 5**: Data Parallelism Engine & Verification.
- [x] **Phase 5.1/5.2**: IPC & Timing Breakdown Audit, Delivery Latency & Overhead Correction.
- [x] **Phase 6**: Task Parallelism Engine, DAG Dependencies, Pluggable Queues & Isolated Workers.
- [x] **Phase 6.1**: Task Parallelism Benchmark Metric Audit (Actual Speedup, Parallelism Ratio, Worker Utilization).
- [x] **Phase 6.2**: Task Parallelism Verification Integrity Audit (Full Equivalence vs Invariant Verification).
- [ ] **Phase 7**: Process Lifecycle Management & CPU Affinity Binding.
- [ ] **Phase 8**: Educational Scheduling Simulation (FCFS, Priority, Round Robin).
- [ ] **Phase 9**: Performance Analytics & Amdahl's Law Visualizer.
- [ ] **Phase 10**: Integration Testing, Hardening & Final Documentation.

