# CoreSync: Multicore Processing, Parallelism, and Scheduling Simulator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Platform: Linux | Windows | macOS](https://img.shields.io/badge/Platform-Linux%20%7C%20Windows%20%7C%20macOS-lightgrey.svg)](docs/INSTALLATION.md)
[![Tests: 255 Passing](https://img.shields.io/badge/Tests-255%20Passing-brightgreen.svg)](docs/TESTING.md)
[![Zero Orphans](https://img.shields.io/badge/Process%20Safety-Zero%20Orphans-success.svg)](docs/ARCHITECTURE.md)

**CoreSync** is an Operating Systems research, benchmarking, and educational desktop workstation engineered to evaluate, visualize, and contrast actual concurrent multiprocessing execution on host hardware (**Environment A: Real System**) with software-simulated processor architectures (**Environment B: Virtual Lab**).

---

## 1. Workstation Showcase

![CoreSync Real vs Virtual Comparison Workstation](docs/screenshots/10_real_vs_virtual_comparison.png)

```mermaid
flowchart TD
    subgraph REAL["Environment A: Real Host System"]
        HW["Host Hardware (Intel / AMD / Apple Silicon)"]
        OS["Operating System Kernel Scheduler"]
        PROCS["Real Multiprocessing Workers (spawn context)"]
        M_REAL["Directly Measured:<br/>Monotonic Wall-Clock Time (s)<br/>Process RSS Memory (MB)<br/>Host CPU Load %"]
    end

    subgraph VIRTUAL["Environment B: Software Virtual Lab"]
        VCPU["Virtual CPU (1..128 cores, Hybrid P/E)"]
        VSCHED["Virtual Scheduler (FCFS, Priority, Round Robin)"]
        SIM["Simulation Clock (Integer Ticks)"]
        M_VIRT["Simulated Virtual:<br/>Virtual Makespan (ticks)<br/>Core Utilization %<br/>Queue Waiting & Turnaround (ticks)"]
    end

    subgraph COMPARISON["Comparison Workstation Engine"]
        MAPPER["Unified Workload Mapper (DP Kernels & DAGs)"]
        ANALYZE["Comparative Analysis Engine"]
        FIREWALL["Clock Domain Firewall (assert_no_cross_domain_ratio)"]
    end

    MAPPER --> REAL
    MAPPER --> VIRTUAL
    REAL --> ANALYZE
    VIRTUAL --> ANALYZE
    ANALYZE --> FIREWALL
```

---

## 2. CoreSync Subsystems & Major Capabilities

### 1. Dual Independent Environments
- **Environment A: Real System**:
  - Genuine host hardware inspection via Linux `sysfs` (`/sys/devices/system/cpu/`), `/proc/cpuinfo`, and `psutil`.
  - Authoritative Performance (P) vs Efficient (E) core classification on Intel hybrid CPUs and Apple Silicon.
  - Real multiprocessing execution using Python's `spawn` start method (zero `fork()` deadlocks).
  - Safety-bounded Real CPU Stress tool with duty-cycle throttling and a hard 30-second cap.
- **Environment B: Virtual Lab**:
  - Configurable virtual topologies (1 to 128 virtual cores, 1 to 256 threads).
  - Heterogeneous computing with configurable P/E clock speed multipliers ($0.5\times$ to $2.0\times$).
  - Simulated scheduling with discrete integer clock ticks, keeping simulated metrics decoupled from physical hardware.

### 2. Parallel Processing Engines
- **Data Parallelism (Page 7)**:
  - 5 computational kernels: `transcendental`, `polynomial`, `matrix_norms`, `prime_count`, `sum_of_squares`.
  - Exact mathematical interval union timing ($T_{\text{union}}$) and no-worker-compute gap analysis.
  - Strict output verification comparing parallel execution results against single-threaded sequential baselines.
- **Task Parallelism & Directed Acyclic Graphs (Page 8)**:
  - 4 production DAG presets: `Diamond DAG`, `Scientific Suite`, `Independent Suite`, `Fan-Out / Fan-In`.
  - Pluggable queue dispatching (FIFO, Priority, Shortest Job First).
  - Fault tolerance with automatic retry cascades and child-branch cancellation on kernel failures.

### 3. CPU Scheduling Simulator (Page 11)
- Implements classic OS uniprocessor scheduling algorithms:
  - **FCFS** (First-Come, First-Served)
  - **SJF** (Shortest Job First, Non-Preemptive)
  - **SRTF** (Shortest Remaining Time First, Preemptive)
  - **Priority Scheduling** (Preemptive & Non-Preemptive with starvation aging)
  - **Round Robin** (Time-sliced execution with configurable quantum)
- Interactive vector Gantt chart with zoom, pan, and side-by-side multi-algorithm comparative dialogs.

### 4. Performance Analytics & Amdahl's Law (Page 9)
- Scalability curve plotting comparing actual speedup against theoretical Amdahl limits ($S_{\max} = \frac{1}{1-P}$).
- Local persistent benchmark history storage with high-performance `mtime`-indexed JSON caching.

### 5. Real System vs Virtual Lab Comparison Workstation (Page 12)
- Unified execution harness supporting three modes: `Real Only`, `Virtual Only`, and `Compare Both`.
- Sequential execution protocol in compare mode (Real System executes first to prevent simulation thread interference).
- Mathematical comparative metrics:
  - **Completion Order Concordance** ($C_{\text{order}}$): Normalized rank correlation ($0.0$ to $1.0$).
  - **Resource Allocation Ratio** ($W_{\text{real}} / C_{\text{virtual}}$).
  - **Utilization Delta** ($\Delta U\% = U_{\text{real}} - U_{\text{virtual}}$).
- **Strict Clock Domain Separation**: Real seconds and virtual ticks belong to separate clock domains and are never divided.

### 6. Process Management & Safety Subsystem
- **Triple-Shield Orphan Prevention**: Linux `prctl(PR_SET_PDEATHSIG, SIGTERM)`, Windows `OpenProcess(SYNCHRONIZE)`, and child-side 100ms parent-death polling watchdogs.
- Guaranteed zero lingering or zombie worker processes upon exit or abort.

---

## 3. Technology Stack

- **Language & Runtime**: Python 3.11, 3.12, 3.13, 3.14 (64-bit)
- **GUI Framework**: PySide6 (Qt 6.12) with custom `QPainter` vector canvases
- **Parallel Processing**: Python standard library `multiprocessing` (`spawn` context)
- **Telemetry & Probing**: `psutil` 7.2+, Linux `sysfs` & `procfs`, Windows WMI/kernel32, macOS sysctl
- **Numerical Computing**: NumPy 2.5+
- **Data Visualization**: Matplotlib
- **Testing & Verification**: `pytest` 9.2+, `pytest-qt`

---

## 4. Installation & Quickstart

### Prerequisites
- Python 3.11+
- Virtual environment tool (`python -m venv`)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/academicos/coresync.git
cd coresync

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate.bat

# 3. Install CoreSync and dependencies
pip install --upgrade pip
pip install -e .

# 4. Launch CoreSync
coresync
```

Alternatively, run directly with Python:
```bash
python main.py
```

For complete platform-specific instructions, see [docs/INSTALLATION.md](docs/INSTALLATION.md).

---

## 5. Documentation Directory

- **[Architecture Deep-Dive](docs/ARCHITECTURE.md)**: System design, IPC contracts, orphan prevention, interval timing math, and clock domain isolation.
- **[Installation Guide](docs/INSTALLATION.md)**: Setup guides for Linux, Windows, macOS, and headless CI.
- **[User Guide](docs/USER_GUIDE.md)**: Operational guide for all 13 workstation pages.
- **[Developer Guide](docs/DEVELOPMENT.md)**: Module conventions, extending kernels/DAGs/schedulers, and coding standards.
- **[Testing & Verification](docs/TESTING.md)**: Full test inventory (255 tests), headless test execution, and orphan verification.
- **[Packaging Guide](packaging/README.md)**: Standalone binary builds via PyInstaller for Linux, Windows, and macOS.
- **[Contributing](docs/CONTRIBUTING.md)**: Pull request protocol and code of conduct.
- **[Third-Party Licenses](THIRD_PARTY_LICENSES.md)**: Licenses and attributions for upstream open-source dependencies.

---

## 6. Cross-Platform Compatibility Matrix

| Operating System | Hardware Probing | Multiprocessing | CPU Affinity | Parent-Death Protection | Test Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Linux (x86_64 / arm64)** | `sysfs`, `procfs`, `psutil` | `spawn` context | `sched_setaffinity` | `PR_SET_PDEATHSIG` + watchdog | **VERIFIED NATIVE** (Arch Linux) |
| **Microsoft Windows (10/11)** | WMI, Registry, `psutil` | `spawn` context | `psutil.cpu_affinity` | `SYNCHRONIZE` handle wait | **VERIFIED VIA MOCKS** |
| **Apple macOS (Darwin)** | `sysctl`, `psutil` | `spawn` context | Informative fallback (No hard affinity in XNU) | `kqueue` / 100ms watchdog | **VERIFIED VIA MOCKS** |

> [!NOTE]
> Testing was physically executed on Linux. Windows and macOS compatibility behaviors are verified through platform-specific automated unit test suites and mocks; native validation on Windows and macOS hardware is documented as unverified pending community runners.

---

## 7. Known Limitations

1. **macOS CPU Affinity**: The Apple XNU kernel does not support hard process-to-core CPU affinity pinning. CoreSync transparently detects macOS and dispatches workers across all available cores without error.
2. **Virtual Ticks vs Physical Time**: Logical clock ticks in the Virtual Lab represent discrete educational simulation cycles and must never be interpreted as real wall-clock seconds.

---

## 8. License

CoreSync is released under the **MIT License**. See the [LICENSE](LICENSE) file for complete terms.
