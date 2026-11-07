# CoreSync: Multicore Processing and Parallelism Workstation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Platform: Linux | Windows | macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](docs/INSTALLATION.md)
[![Tests: 272 Passing](https://img.shields.io/badge/Tests-272%20Passing-brightgreen.svg)](docs/TESTING.md)
[![Process Safety: Zero Orphans](https://img.shields.io/badge/Process%20Safety-Zero%20Orphans-success.svg)](docs/ARCHITECTURE.md)

**CoreSync** is an interactive desktop engineering workstation for exploring, simulating, executing, and analyzing multicore processing, parallel computing paradigms, and operating systems CPU scheduling concepts.

It combines real-system hardware monitoring and multiprocessing execution with a software-simulated virtual multicore processor lab. This dual-architecture design allows researchers, engineers, and students to evaluate how workloads scale across physical CPU cores, benchmark parallel execution strategies, experiment with scheduling algorithms, and analyze performance bottlenecks.

Built with **Python**, **PySide6 (Qt 6)**, **NumPy**, **psutil**, and **Matplotlib**, CoreSync provides an educational and benchmarking workstation for systems programming and parallel architectures.

---

## Overview

Modern processors leverage multiple physical cores, symmetric multithreading (SMT), and heterogeneous architectures (Performance vs. Efficient cores) to maximize throughput. Understanding how operating systems schedule processes, how data-parallel and task-parallel workloads scale, and where synchronization overhead arises requires more than theoretical explanations.

CoreSync brings these concepts together in a unified desktop workstation divided into two strictly isolated environments:

- **Environment A: Real System**: Monitors the computer's physical CPU cores, memory, process hierarchy, and hardware topology. It executes controlled CPU-intensive workloads using true multi-process worker pools.
- **Environment B: Virtual Lab**: Simulates configurable multicore processors (1 to 128 virtual cores), heterogeneous core speeds, workload injection, and scheduling algorithms within a deterministic simulation clock.

These environments are strictly separated by an architectural firewall so that simulated virtual metrics are never conflated with physical host telemetry.

```mermaid
flowchart TD
    subgraph REAL["Environment A: Real Host System"]
        HW["Host Hardware (Intel / AMD / ARM64)"]
        OS["OS Kernel Scheduler (Linux CFS / Windows NT / macOS XNU)"]
        PROCS["Multiprocessing Workers (Python spawn context)"]
        M_REAL["Directly Measured Telemetry:<br/>• Monotonic Elapsed Wall-Clock Time (s)<br/>• Process RSS Memory (MB)<br/>• Host CPU Load % & Worker Pinning"]
    end

    subgraph VIRTUAL["Environment B: Software Virtual Lab"]
        VCPU["Virtual CPU (1..128 cores, Configurable P/E Ratios)"]
        VSCHED["Virtual Scheduler (FCFS, SJF, Priority, Round Robin)"]
        SIM["Simulation Clock Domain (Discrete Integer Ticks)"]
        M_VIRT["Simulated Indicators:<br/>• Virtual Makespan (ticks)<br/>• Simulated Core Utilization %<br/>• Queue Waiting & Turnaround Times (ticks)"]
    end

    subgraph WORKSTATION["CoreSync Comparison & Analytics Engine"]
        MAPPER["Unified Workload Mapper (Data Kernels & Task DAGs)"]
        ANALYZE["Comparative Analysis Engine"]
        FIREWALL["Clock Domain Firewall (Strict Separation: s ≠ ticks)"]
    end

    MAPPER --> REAL
    MAPPER --> VIRTUAL
    REAL --> ANALYZE
    VIRTUAL --> ANALYZE
    ANALYZE --> FIREWALL
```

---

## Key Features

### 1. Real Hardware Monitoring
Monitor the physical host system on which CoreSync is running:
- **CPU Topology & Model**: CPU manufacturer, model name, physical cores, and logical processors.
- **Heterogeneous Architecture**: Automatic Performance (P-core) and Efficient (E-core) identification on supported hybrid architectures (Intel 12th+ Gen, Apple Silicon).
- **CPU Frequency & Load**: Live per-core utilization and frequency tracking (where supported by host OS).
- **Memory Telemetry**: Real-time physical RAM utilization, availability, and process RSS tracking.
- **Process Hierarchy**: Comprehensive process table with automatic CoreSync worker process identification and filtering.

### 2. Real CPU Stress Testing
Execute controlled, safety-bounded CPU-intensive workloads directly on the host hardware:
- **Multiprocessing Worker Engine**: Spawns isolated worker processes pinned across selected logical processors.
- **Configurable Workload Parameters**: User-adjustable worker count, execution duration, and duty-cycle throttling.
- **Strict Safety Boundaries**: Hard 30-second execution cap to prevent thermal runaway or host freezing.
- **Clean Worker Cleanup**: Guaranteed cooperative cancellation and immediate orphan process termination.

### 3. Virtual Multicore Lab
Architect and experiment with a software-simulated multicore processor:
- **Flexible Core Topology**: Configure between 1 and 128 virtual cores with custom thread allocation.
- **Heterogeneous P/E Characteristics**: Configure asymmetric P-core and E-core performance ratios ($0.5\times$ to $2.0\times$ cycle throughput).
- **Synthetic Workload Generator**: Generate synthetic task batches with configurable burst profiles, memory footprints, and priorities.
- **Virtual Core Monitor**: Real-time matrix visualizer observing simulated cycle throughput, core utilization, and task allocation.
- **Clock Domain Independence**: All virtual metrics run on integer simulation ticks, completely isolated from real host clocks.

---

### 4. Data Parallelism

Explore how large computational datasets are divided into smaller chunks and processed concurrently across worker pools.

```mermaid
flowchart LR
    IN["Input Dataset (N Items)"] --> PART["Workload Partitioning"]
    PART --> C1["Chunk 1"]
    PART --> C2["Chunk 2"]
    PART --> C3["Chunk ..."]
    PART --> CN["Chunk W"]

    C1 --> W1["Worker 1 (PID 1)"]
    C2 --> W2["Worker 2 (PID 2)"]
    C3 --> W3["Worker ... (PID ...)"]
    CN --> WN["Worker W (PID W)"]

    W1 --> GATH["Result Aggregation & Verification"]
    W2 --> GATH
    W3 --> GATH
    WN --> GATH
    GATH --> OUT["Final Output vs Sequential Baseline"]
```

#### Core Capabilities
- **Partitioning Strategies**: Equal-block slicing, uneven remainder distribution, and array chunking.
- **CPU-Bound Kernels**: Transcendental trigonometry, prime factorization, matrix norms, and polynomial evaluations.
- **Verification Engine**: Strict numerical output verification comparing parallel results against a single-threaded baseline (tolerances: $\text{rtol} = 10^{-5}, \text{atol} = 10^{-8}$).
- **Interval Union Timing**: Exact mathematical decomposition of parallel execution into active worker compute intervals and no-worker-compute overhead.

#### Mathematical Formulations

- **Parallel Speedup ($S$)**:
  $$S = \frac{T_{\text{seq}}}{T_{\text{par}}}$$
  Where $T_{\text{seq}}$ is the measured single-threaded baseline execution duration, and $T_{\text{par}}$ is the elapsed parallel execution makespan.

- **Parallel Efficiency ($E$)**:
  $$E = \frac{S}{W} \times 100\% = \frac{T_{\text{seq}}}{W \cdot T_{\text{par}}} \times 100\%$$
  Where $W$ represents the number of active worker processes.

- **Processing Throughput**:
  $$\text{Throughput} = \frac{N_{\text{items}}}{T_{\text{par}}} \quad (\text{items/second})$$

- **Worker Compute Interval Union & Residual Overhead**:
  Given worker execution intervals $[t_{\text{start}, i}, t_{\text{end}, i}]$ for $i \in \{1, \dots, W\}$:
  $$\mathcal{I}_{\text{union}} = \bigcup_{i=1}^{W} [t_{\text{start}, i}, t_{\text{end}, i}]$$
  $$T_{\text{union}} = \sum_{[a_k, b_k] \in \mathcal{I}_{\text{union}}} (b_k - a_k)$$
  $$T_{\text{no\_worker\_compute}} = T_{\text{par}} - T_{\text{union}}$$
  $T_{\text{no\_worker\_compute}}$ represents the exact elapsed duration where zero instrumented worker processes were actively computing (capturing dispatch, IPC transit, and merge overhead).

---

### 5. Task Parallelism & Directed Acyclic Graphs (DAG)

Execute complex workflows containing interdependent and independent tasks with fine-grained concurrency control.

```mermaid
stateDiagram-v2
    [*] --> PENDING: Task Initialized
    PENDING --> READY: Dependencies Satisfied
    PENDING --> BLOCKED: Parent Failed
    READY --> QUEUED: Dispatched to Priority Queue
    QUEUED --> RUNNING: Assigned to Worker Process
    RUNNING --> COMPLETED: Output Verified
    RUNNING --> FAILED: Exception / Verification Mismatch
    FAILED --> READY: Retries Remaining
    FAILED --> BLOCKED: Retries Exhausted (Cascades to Children)
    RUNNING --> CANCELLED: User Abort
```

#### Features
- **DAG Presets**: Diamond Pipeline, Scientific Suite (7 tasks), Independent Fan-Out/Fan-In, Matrix Pipeline.
- **Pluggable Scheduling**: First-Come First-Served (FIFO), Priority Queue (highest first), and Shortest Job First (SJF).
- **Fault Tolerance**: Automatic retry cascades with exponential backoff and downstream failure propagation.
- **Real-Time DAG Canvas**: Zoomable vector visualizer displaying dynamic node states and edge dependencies.

#### Mathematical Formulations

- **Actual Speedup ($S_{\text{actual}}$)**:
  $$S_{\text{actual}} = \frac{T_{\text{seq}}}{T_{\text{par}}}$$

- **Parallelism Ratio ($P$)**:
  $$P = \frac{\sum_{j=1}^{M} T_{\text{task}, j}}{T_{\text{par}}}$$
  Measures the average effective concurrency achieved across the DAG workload.

- **Worker Pool Utilization ($U$)**:
  $$U = \frac{\sum_{j=1}^{M} T_{\text{task}, j}}{W \cdot T_{\text{par}}} \times 100\%$$

---

### 6. CPU Scheduling Simulator

An interactive testbed for exploring classic and modern uniprocessor scheduling algorithms.

| Algorithm | Preemption Mode | Primary Selection Metric | Starvation Protection |
| :--- | :--- | :--- | :--- |
| **FCFS** | Non-preemptive | Arrival Time ($T_{\text{arrival}}$) | Inherent FIFO order |
| **SJF** | Non-preemptive | Expected Burst Time ($T_{\text{burst}}$) | None |
| **SRTF** | Preemptive | Remaining Burst Time ($T_{\text{remaining}}$) | None |
| **Priority** | Non-preemptive | Static / Effective Priority Value | Dynamic Priority Aging |
| **Preemptive Priority** | Preemptive | Highest Priority Process | Dynamic Priority Aging |
| **Round Robin (RR)** | Preemptive | Time Quantum ($\tau$) expiration | Time-sliced round robin |

#### Interactive Visualizer & Metrics
- Vector Gantt chart with interactive zoom and drag controls.
- Side-by-side multi-algorithm comparative evaluation dialog.
- Complete execution timeline step-through.

#### Scheduling Metrics Formulations

- **Turnaround Time ($TAT_i$)**:
  $$TAT_i = T_{\text{completion}, i} - T_{\text{arrival}, i}$$

- **Waiting Time ($WT_i$)**:
  $$WT_i = TAT_i - T_{\text{burst}, i}$$

- **Response Time ($RT_i$)**:
  $$RT_i = T_{\text{first\_cpu}, i} - T_{\text{arrival}, i}$$

- **Normalized Turnaround Time ($NTAT_i$)**:
  $$NTAT_i = \frac{TAT_i}{T_{\text{burst}, i}}$$

- **Dynamic Priority Aging Formula**:
  $$P_{\text{effective}}(t) = P_{\text{base}} \pm \left\lfloor \frac{t_{\text{wait}}}{\tau_{\text{aging}}} \right\rfloor$$
  Ensures waiting processes increment priority deterministically to eliminate starvation.

---

### 7. Performance Analytics & Amdahl's Law

Measure, analyze, and visualize execution performance across empirical multi-run benchmarks and theoretical scalability models.

#### Amdahl's Law Scalability Model
Predicts the theoretical upper bound on speedup when parallelizing a workload across $N$ processors with a parallelizable fraction $p \in [0, 1]$:

$$S(N) = \frac{1}{(1 - p) + \frac{p}{N}}$$

As the processor count approaches infinity, the asymptotic speedup limit is bounded strictly by the serial fraction $(1 - p)$:

$$S_{\max} = \lim_{N \to \infty} S(N) = \frac{1}{1 - p}$$

#### Empirical Parallel Fraction Derivation
CoreSync calculates the empirical parallel fraction achieved by real workloads:

$$p = \frac{\frac{1}{S} - 1}{\frac{1}{N} - 1} \quad (N > 1)$$

#### Statistical Robustness
Multi-iteration benchmarks compute sample mean ($\bar{x}$) and sample standard deviation ($\sigma$):

$$\bar{x} = \frac{1}{K}\sum_{k=1}^K x_k, \quad \sigma = \sqrt{\frac{1}{K-1} \sum_{k=1}^K (x_k - \bar{x})^2}$$

#### Metric Provenance Framework
CoreSync strictly classifies every metric displayed in the UI:
- **Directly Measured**: Hardware elapsed time (`time.perf_counter_ns()`), Process RSS memory, host load.
- **Mathematically Derived**: Calculated directly from measured inputs ($S = T_{\text{seq}} / T_{\text{par}}$, $E = S / W$).
- **Estimated**: Residual IPC communication overhead derived from non-compute gaps.
- **Simulated**: Integer ticks, simulated virtual core utilization, and virtual queue waiting times.

---

### 8. Real System vs Virtual Lab Comparison

Compare physical hardware execution directly against software-simulated processor execution.

#### Supported Execution Modes
- **Real Only**: Executes workload exclusively on host hardware multiprocessing workers.
- **Virtual Only**: Executes workload exclusively within the software-simulated Virtual Lab.
- **Compare Both**: Executes both environments under a strictly sequential protocol (Real System executes first to eliminate background simulation interference).

#### Comparative Mathematical Metrics

- **Completion Order Concordance ($C_{\text{order}}$)**:
  Measures the consistency of task completion ordering between environments using normalized Spearman's Rank Correlation ($r_s$):
  $$r_s = 1 - \frac{6 \sum_{i=1}^n d_i^2}{n(n^2 - 1)}, \quad C_{\text{order}} = \frac{r_s + 1}{2} \in [0.0, 1.0]$$
  Where $d_i = \text{Rank}_{\text{real}}(i) - \text{Rank}_{\text{virt}}(i)$. $1.0$ indicates identical completion ordering, while $0.0$ indicates complete inversion.

- **Resource Allocation Ratio ($R_{\text{alloc}}$)**:
  $$R_{\text{alloc}} = \frac{W_{\text{real}}}{C_{\text{virtual}}}$$

- **Utilization Delta ($\Delta U$)**:
  $$\Delta U\% = U_{\text{real}}\% - U_{\text{virtual}}\%$$

- **Clock Domain Firewall Invariant**:
  $$\frac{T_{\text{real}}(\text{seconds})}{T_{\text{virtual}}(\text{ticks})} \implies \mathbf{FORBIDDEN}$$
  Physical elapsed time (measured via monotonic hardware timers in seconds) and virtual simulation duration (measured in discrete logical ticks) belong to distinct, non-interchangeable clock domains. Cross-domain division is structurally prevented by software assertions.

---

## Architecture

CoreSync follows a modular, decoupled architecture that enforces strict separation of concerns between GUI presentation, computation engines, operating system interfaces, and background telemetry.

```
CoreSync/
├── main.py                     # Entry point with Win32 freeze_support and CLI flags
├── pyproject.toml              # Modern PEP 621 / setuptools project metadata
├── requirements.txt            # Production runtime dependencies
├── requirements-dev.txt        # Development and testing dependencies
├── LICENSE                     # MIT License
├── THIRD_PARTY_LICENSES.md     # Upstream open-source license attributions
│
├── engine/                     # Pure computation and simulation engines (No Qt dependencies)
│   ├── process_manager.py      # Spawn-based worker orchestration and process tracking
│   ├── resource_guard.py       # Host memory headroom and core allocation guards
│   ├── worker.py               # Multiprocessing worker execution loop and IPC channels
│   ├── affinity.py             # Cross-platform CPU affinity assignment and policies
│   ├── analytics/              # Benchmark statistics, history CRUD, and Amdahl calculations
│   ├── comparison/             # Real vs Virtual workload mapper and concordance engine
│   ├── data_parallel/          # Slicing, chunk distribution, and parallel array kernels
│   ├── process_scheduler/      # FCFS, SJF, SRTF, Priority, and Round Robin algorithms
│   ├── real_system/            # Safety-bounded real CPU stress generator
│   ├── task_parallel/          # Directed Acyclic Graph validator, queue, and runner
│   └── virtual_lab/            # Virtual multicore CPU, P/E models, and discrete tick scheduler
│
├── gui/                        # Presentation layer (PySide6 / Qt 6)
│   ├── main_window.py          # Master workstation window with responsive sidebar
│   ├── styles.py               # Minimal dark theme stylesheet (#10141B palette)
│   ├── dashboard.py            # Overview dashboard and quick navigation cards
│   ├── core_monitor.py         # Hardware CPU topology and logical core utilization
│   ├── data_parallelism.py     # Data parallel workstation and scatter-gather visualizer
│   ├── task_parallelism.py     # Task parallel workstation with zoomable DAG canvas
│   ├── performance.py          # Benchmark analytics workstation and Amdahl interactive model
│   ├── comparison.py           # Real vs Virtual unified comparison workstation
│   ├── scheduler_view.py       # Standalone interactive CPU scheduling simulator
│   ├── settings.py             # System configuration, timeouts, and platform probing settings
│   ├── components/             # Reusable UI widgets (MetricCard, StatusBadge, DAGCanvas, Gantt)
│   ├── real_system/            # Real process monitor and stress generator views
│   └── virtual_lab/            # Virtual CPU architect, monitor, and scheduler views
│
├── monitoring/                 # Background hardware sampling services
│   ├── cpu_monitor.py          # QThread-based asynchronous psutil telemetry sampler
│   └── metrics.py              # Telemetry snapshots and data container models
│
├── utils/                      # Utilities, configuration, and hardware abstractions
│   ├── config.py               # Application constants, theme colors, and timeout thresholds
│   ├── system_info.py          # Unified host discovery entry point
│   └── hardware/               # Hardware abstraction layer (HAL)
│       ├── base.py             # Abstract base hardware provider interface
│       ├── linux.py            # Linux sysfs and procfs hardware provider
│       ├── windows.py          # Windows Registry and Win32 hardware provider
│       └── macos.py            # macOS sysctl hardware provider
│
├── docs/                       # Technical documentation and guides
│   ├── ARCHITECTURE.md         # Deep-dive architectural specification
│   ├── INSTALLATION.md         # Detailed platform setup and troubleshooting
│   ├── USER_GUIDE.md           # Operational manual for all 13 workstation pages
│   ├── DEVELOPMENT.md          # Contributing guidelines and extension points
│   ├── TESTING.md              # Comprehensive test inventory and procedures
│   ├── CONTRIBUTING.md         # Pull request guidelines and code of conduct
│   └── screenshots/            # Workstation interface screenshots
│
├── packaging/                  # Standalone distribution specifications
│   ├── coresync.spec           # PyInstaller spec for single-binary bundling
│   ├── build_linux.sh          # Linux build script
│   ├── build_windows.bat       # Windows Command Prompt build script
│   ├── build_windows.ps1       # Windows PowerShell build script
│   └── build_macos.sh          # macOS build script
│
└── tests/                      # Comprehensive automated test suite (272 tests)
    ├── test_cpu_monitor.py
    ├── test_data_parallel.py
    ├── test_task_parallel.py
    ├── test_process_scheduler.py
    ├── test_performance_analytics.py
    ├── test_comparison_runner.py
    ├── test_windows_native_compat.py
    └── ... (25 test modules total)
```

### Core Architectural Principles

1. **Process Isolation**: CPU-intensive workloads execute strictly within separate worker processes, ensuring that heavy computation never blocks the Qt event loop or compromises UI responsiveness.
2. **Spawn Multiprocessing Context**: Python's `spawn` multiprocessing context is enforced across all platforms (`multiprocessing.get_context("spawn")`), eliminating `fork()` lock deadlocks between Qt and POSIX threads.
3. **GUI / Engine Decoupling**: Computation engines under `engine/` have zero imports from `PySide6`. Communication between the GUI and engines occurs via dedicated worker threads and thread-safe Qt Signals.
4. **Triple-Shield Orphan Prevention**: 
   - **Linux**: Child processes register `prctl(PR_SET_PDEATHSIG, SIGTERM)`.
   - **Windows**: Child processes open a synchronization handle to the parent PID via Win32 `OpenProcess(SYNCHRONIZE, ...)`.
   - **Cross-Platform**: Child watchdogs monitor parent PID liveliness every 100ms. If the master application terminates unexpectedly, all child workers terminate immediately.
5. **Hardware Abstraction Layer (HAL)**: Host-specific discovery is isolated into clean platform providers (`LinuxHardwareProvider`, `WindowsHardwareProvider`, `MacOSHardwareProvider`).
6. **Strict Metric Provenance**: Measured, derived, estimated, and simulated values are segregated across data models and user interfaces.
7. **Clock-Domain Separation**: Monotonic elapsed wall-clock seconds and virtual simulation ticks remain strictly independent.

---

## Technology Stack

| Technology | Version | Purpose in CoreSync |
| :--- | :--- | :--- |
| **Python** | `3.11+` | Core programming language, object models, and computation routines |
| **PySide6 (Qt 6)** | `6.12.0` | Desktop GUI framework, event management, and custom vector canvases |
| **NumPy** | `2.5.0+` | High-performance numerical operations and array kernel evaluations |
| **psutil** | `7.2.2+` | Host hardware telemetry, CPU load sampling, and process inspection |
| **Matplotlib** | `3.10.0+` | Chart generation, Amdahl scalability plots, and telemetry rendering |
| **multiprocessing** | Standard Library | Parallel execution engine operating strictly under `spawn` context |
| **pytest & pytest-qt** | `9.2.0` / `4.5.0` | Automated testing framework for unit, integration, and GUI verification |

---

## Installation & Quickstart

### Prerequisites
- **Python 3.11** or later (tested on Python 3.14.9 with PySide6 6.12.0).
- **Git** (for source repository management).
- 64-bit operating system (**Linux**, **Windows 10/11**, or **macOS**).
- Dedicated multi-core CPU recommended for parallel benchmarks.

---

### Quickstart: Linux (Arch, Ubuntu, Debian, Fedora)

```bash
# 1. Clone repository
git clone https://github.com/academicos/coresync.git
cd coresync

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip and install package in editable mode
pip install --upgrade pip
pip install -e .

# 4. Launch CoreSync
coresync
# Or directly via Python:
python main.py
```

---

### Quickstart: Windows 10 / Windows 11

CoreSync includes automated setup and launch scripts for Windows Command Prompt and PowerShell.

#### Option A: Windows Command Prompt (`cmd.exe`)
```cmd
REM Open Command Prompt in the project folder and run:
setup_windows.bat
run_windows.bat
```

To run the automated regression test suite on Windows:
```cmd
test_windows.bat
```

#### Option B: Windows PowerShell
```powershell
# Set execution policy if necessary, then run:
.\setup_windows.ps1
.\run_windows.ps1
```

To run tests in PowerShell:
```powershell
.\test_windows.ps1
```

---

### Quickstart: macOS (Apple Silicon & Intel)

```bash
git clone https://github.com/academicos/coresync.git
cd coresync
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
python main.py
```

> [!NOTE]
> On macOS, the Apple XNU kernel does not support hard thread/process affinity pinning. CoreSync detects macOS automatically, dispatches workloads across all available cores without error, and provides informative fallback notices.

Refer to **[docs/INSTALLATION.md](docs/INSTALLATION.md)** for detailed environment troubleshooting and package build instructions.

---

## Running the Automated Test Suite

CoreSync features an exhaustive automated test suite covering hardware detection, data parallelism, task DAG scheduling, process management, scheduling algorithms, performance analytics, Windows native compatibility, and GUI navigation.

To run the full test suite:
```bash
python -m pytest tests/ -v
```

For a compact summary:
```bash
python -m pytest tests/ -q
```

To execute GUI unit tests in a headless Linux / CI environment:
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
```

### Official Test Results Summary

```
============================= test session starts ==============================
platform linux -- Python 3.14.9, pytest-9.2.0, pluggy-1.7.0
PySide6 6.12.0 -- Qt runtime 6.12.0 -- Qt compiled 6.12.0
rootdir: /home/ankur/Code Playground/OS project/CoreSync
configfile: pyproject.toml
plugins: qt-4.5.0, anyio-4.16.0, platformdirs-4.14.3
collected 272 items

tests/test_comparison_gui.py .........................                   [  3%]
tests/test_comparison_metrics.py .................                      [  7%]
tests/test_comparison_models.py .................                       [ 11%]
tests/test_comparison_runner.py .................                       [ 15%]
tests/test_data_parallel.py ....................................        [ 28%]
tests/test_process_manager.py ..................................        [ 41%]
tests/test_process_scheduler.py ................................        [ 53%]
tests/test_performance_analytics.py ...........................        [ 63%]
tests/test_task_parallel.py ....................................        [ 76%]
tests/test_virtual_lab.py ......................................        [ 88%]
tests/test_windows_native_compat.py ............................        [100%]

============================= 272 passed in 21.33s =============================
```

| Metric | Result |
| :--- | :--- |
| **Total Test Modules** | 25 modules |
| **Total Test Cases** | 272 tests |
| **Passing Tests** | **272 (100%)** |
| **Failures / Errors** | **0** |
| **Execution Duration** | 21.33 seconds |
| **Active / Zombie Processes Remaining** | **0 (Verified via `ps aux`)** |

---

## Workstation Screenshots Gallery

CoreSync features a sophisticated dark engineering workstation theme (`#0B1020` deep navy canvas with `#0D1220` layered sidebar) optimized for **2560 × 1440 (2K QHD)** displays and high-DPI scaling. It incorporates CPU-inspired silicon branding, vector line icons for all 13 modules, active indigo-to-cyan gradient treatments, circular arc gauges, cubic Bézier area sparklines, core heatmaps, and vector Gantt timelines. High-resolution screenshots of all 13 workstation pages are maintained in `docs/screenshots/`:

| Page Index | Workstation Module | Screenshot Artifact | Description |
| :---: | :--- | :--- | :--- |
| **0** | **Dashboard** | [`docs/screenshots/00_dashboard.png`](docs/screenshots/00_dashboard.png) | System telemetry, CPU overview, and quick-navigation workstation hub |
| **1** | **Core Monitor** | [`docs/screenshots/01_core_monitor.png`](docs/screenshots/01_core_monitor.png) | Physical/logical core topology and real-time per-core utilization |
| **2** | **Process Monitor** | [`docs/screenshots/02_process_monitor.png`](docs/screenshots/02_process_monitor.png) | Active OS process inspector with CoreSync worker isolation filters |
| **3** | **Real CPU Stress** | [`docs/screenshots/03_real_stress.png`](docs/screenshots/03_real_stress.png) | Safety-bounded multi-core stress generator with 30s hardware protection |
| **4** | **Virtual CPU Config** | [`docs/screenshots/04_virtual_config.png`](docs/screenshots/04_virtual_config.png) | Architecture architect for 1–128 virtual cores with P/E clock ratios |
| **5** | **Virtual Core Monitor** | [`docs/screenshots/05_virtual_monitor.png`](docs/screenshots/05_virtual_monitor.png) | Simulated multicore utilization matrix and cycle throughput observation |
| **6** | **Virtual Scheduler** | [`docs/screenshots/06_virtual_scheduler.png`](docs/screenshots/06_virtual_scheduler.png) | Multi-core queue dispatching lab under FCFS, Priority, and Round Robin |
| **7** | **Data Parallelism** | [`docs/screenshots/07_data_parallelism.png`](docs/screenshots/07_data_parallelism.png) | Array chunk partitioning, parallel SIMD kernels, and speedup analysis |
| **8** | **Task Parallelism** | [`docs/screenshots/08_task_parallelism.png`](docs/screenshots/08_task_parallelism.png) | Directed Acyclic Graph execution flow with interactive canvas zoom |
| **9** | **Performance Analytics** | [`docs/screenshots/09_performance_analytics.png`](docs/screenshots/09_performance_analytics.png) | Benchmark history rollups, statistical variance, and Amdahl modeler |
| **10** | **Settings** | [`docs/screenshots/10_settings.png`](docs/screenshots/10_settings.png) | Process timeouts, hardware probing mechanisms, and UI preferences |
| **11** | **Process Scheduler** | [`docs/screenshots/11_process_scheduler.png`](docs/screenshots/11_process_scheduler.png) | Uniprocessor CPU scheduling simulator with vector Gantt charts |
| **12** | **Real vs Virtual Comparison** | [`docs/screenshots/12_real_vs_virtual_comparison.png`](docs/screenshots/12_real_vs_virtual_comparison.png) | Dual-environment benchmarking and completion order concordance |

---

### Featured Workstation Views

#### Real vs Virtual Comparison Workstation
![Real vs Virtual Comparison](docs/screenshots/12_real_vs_virtual_comparison.png)

#### Task Parallelism Workstation & DAG Flow
![Task Parallelism](docs/screenshots/08_task_parallelism.png)

#### Data Parallelism Workstation & Performance Metrics
![Data Parallelism](docs/screenshots/07_data_parallelism.png)

#### Performance Analytics & Amdahl's Law Modeler
![Performance Analytics](docs/screenshots/09_performance_analytics.png)

---

## Platform Compatibility Matrix

| Operating System | Hardware Discovery | Worker Multiprocessing | CPU Affinity Pinning | Process Safety & Reaping | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Linux (x86_64 / arm64)** | `sysfs`, `procfs`, `psutil` | `spawn` context | `sched_setaffinity` | `PR_SET_PDEATHSIG` + watchdog | **VERIFIED NATIVE** (Arch Linux) |
| **Microsoft Windows (10/11)** | WinReg, WMIC, `psutil` | `spawn` + `freeze_support` | `SetProcessAffinityMask` | `OpenProcess(SYNCHRONIZE)` handle | **VERIFIED VIA COMPREHENSIVE SUITE** (272 tests) |
| **Apple macOS (Darwin)** | `sysctl`, `psutil` | `spawn` context | Graceful fallback (No hard affinity in XNU) | `kqueue` / 100ms watchdog | **VERIFIED VIA MOCKS** |

> [!NOTE]
> Physical test runs in our primary development environment are executed on Arch Linux (`Linux 7.2.14-arch1-1 x86_64`). Windows native subsystems (WinReg hardware detection, Win32 `OpenProcess(SYNCHRONIZE)` handle wait, Win32 processor numbers, `freeze_support` lifecycle, and path safety) are tested via dedicated unit test suites (`tests/test_windows_native_compat.py`). To validate natively on a Windows 10/11 workstation, execute `test_windows.bat` or `.\test_windows.ps1`.

---

## Documentation Directory

Comprehensive engineering documentation is available in the [`docs/`](docs/) directory:

| Document | Description |
| :--- | :--- |
| **[Architecture Deep-Dive](docs/ARCHITECTURE.md)** | Subsystem interaction, IPC contracts, orphan prevention, interval timing math, and clock-domain isolation |
| **[Installation Guide](docs/INSTALLATION.md)** | Step-by-step setup guides for Linux, Windows 10/11, macOS, virtual environments, and PyInstaller builds |
| **[User Guide](docs/USER_GUIDE.md)** | Complete operational handbook for all 13 workstation pages, parameters, and controls |
| **[Developer Guide](docs/DEVELOPMENT.md)** | Architectural rules, extending computational kernels, authoring DAG presets, and code styling standards |
| **[Testing & Verification Guide](docs/TESTING.md)** | Test inventory (272 tests), headless testing procedures, edge-case audit logs, and verification checks |
| **[Packaging Guide](packaging/README.md)** | Standalone binary creation via PyInstaller for Linux, Windows (`build_windows.bat`/`.ps1`), and macOS |
| **[Contribution Guidelines](docs/CONTRIBUTING.md)** | Development workflow, branching strategy, pull request protocol, and code review criteria |
| **[Third-Party Licenses](THIRD_PARTY_LICENSES.md)** | License declarations and copyright notices for upstream dependencies (PySide6, NumPy, psutil, Matplotlib) |

---

## Known Limitations

1. **macOS CPU Affinity**: The Apple XNU kernel does not support explicit thread-to-core affinity binding. CoreSync automatically detects macOS and distributes workers across all cores without raising an exception.
2. **Virtual Ticks vs Physical Time**: Logical clock ticks in the Virtual Lab represent discrete educational simulation cycles and must never be interpreted as real wall-clock seconds.
3. **P-core / E-core Identification**: Hybrid core classification relies on operating-system sysfs entries (Linux) or processor group metadata (Windows). Unsupported or virtualized hypervisors may report all cores as homogeneous.
4. **Hardware Performance Variance**: Measured parallel speedup and efficiency depend on the physical processor's memory bandwidth, cache hierarchy, thermal throttling, and background operating system activity.

---

## Contributing

Contributions, bug reports, and suggestions are welcome. Before contributing:
1. Review [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).
2. Adhere to the strict GUI/Engine separation (zero Qt imports in `engine/`).
3. Ensure that all multiprocessing operations preserve the `spawn` context.
4. Add comprehensive unit tests in `tests/` for any new functionality.
5. Verify that the entire test suite passes (`pytest tests/`) with 0 orphan processes.

See **[docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)** for detailed contribution guidelines and coding conventions.

---

## License

CoreSync is open-source software licensed under the **[MIT License](LICENSE)**.

Upstream libraries and dependencies retain their respective open-source licenses as documented in **[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)**.

---

## Project Status

**CoreSync v1.0.0 (Release Candidate)**
- **Roadmap Completed**: All 11 development phases (Phases 1 through 11, including native Windows compatibility and UI refinement) have been fully engineered and approved.
- **Test Coverage**: 272 automated test cases passing with 100% success rate across 25 test modules.
- **Release Preparation**: Packaged with PyInstaller build scripts for Windows, Linux, and macOS.

---

<p align="center">
  <b>CoreSync</b><br>
  <i>Understand. Simulate. Execute. Analyze.</i>
</p>
