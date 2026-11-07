# CoreSync Workstation User Guide

This guide describes how to operate each of the 13 workstation pages in CoreSync.

---

## Navigation & Workstation Layout

The workstation interface features:
- **Sidebar Navigation**: Organized into 6 functional categories.
- **Top Header Bar**: Displays current section breadcrumb, active hardware summary, and live status.
- **Main Viewport**: High-density workstation panels with real-time responsive updates.

### Launching on Windows (Windows 10 / 11)
- Double-click `run_windows.bat` in the project root, or execute:
  ```cmd
  run_windows.bat
  ```
- Or via PowerShell:
  ```powershell
  .\run_windows.ps1
  ```
- CoreSync automatically binds to the native Windows desktop platform plugin, applies high-DPI font scaling, and sets up worker parent-death handle watchers.

### Launching on Linux / macOS
```bash
coresync       # Or: python main.py
```

---

## 1. Dashboard (Index 0)

The **Dashboard** provides an executive summary of host system capabilities and quick-action launcher cards.
- **Hardware Pill**: Displays physical cores, logical hyperthreads, CPU architecture, and total RAM.
- **Live Activity Feed**: Logs recent worker lifecycle events and system status.
- **Quick Action Cards**: One-click navigation shortcuts to Core Monitor, Virtual Config, and Virtual Scheduler.

---

## 2. Core Monitor (Index 1)

The **Core Monitor** displays individual logical core topology and live utilization percentages.
- **Core Cards**: Visual card for each CPU core showing core number, frequency, and current utilization percentage.
- **Topology Indicator**: Identifies Performance (P) vs Efficient (E) cores on hybrid platforms (Intel 12th+ Gen, Apple Silicon).
- **CPU Affinity Map**: Shows current allowed CPU core mask.

---

## 3. Process Monitor (Index 2)

The **Process Monitor** inspects live operating system processes and actively tracks CoreSync child worker processes.
- **Worker Process Table**: Displays worker process ID (PID), process name, CPU %, RSS memory ($MB$), and execution state.
- **Child Worker Tagging**: Highlighting for genuine CoreSync workers spawned by Data Parallelism, Task Parallelism, or Real CPU Stress.

---

## 4. Real CPU Stress Generator (Index 3)

The **Real CPU Stress Generator** allows users to safely apply controlled multicore load to the physical processor.
- **Safety Boundaries**: Strictly capped to a maximum duration of **30 seconds**; requires explicit user initiation.
- **Worker Count**: Slider to select number of target stress workers ($1 \le W \le \text{Logical CPUs}$).
- **Duty-Cycle Throttling**: Configurable active vs rest duty cycle ($10\%$ to $100\%$) preventing thermal runaway.
- **Immediate Stop**: Emergency "Halt Stress" button terminates all stress worker processes cooperatively within 500ms.

---

## 5. Virtual CPU Config (Index 4)

The **Virtual CPU Configurator** allows users to design simulated multicore processors.
- **Topology Controls**: Configure virtual physical cores ($1$ to $128$) and virtual threads ($1$ to $256$).
- **Heterogeneous P/E Presets**: Toggle hybrid processor architectures with custom Performance and Efficiency speed multipliers ($0.5\times$ to $2.0\times$).
- **Apply & Rebuild**: Propagates updated virtual topologies immediately to the Virtual Monitor and Virtual Scheduler.

---

## 6. Virtual Core Monitor (Index 5)

The **Virtual Core Monitor** presents a live matrix of software-simulated processor cores.
- **Virtual Core Cards**: Shows simulated busy/idle state, assigned simulated task ID, and accumulated clock ticks.
- **Core Utilization Grid**: Heatmap representing simulated execution distribution across virtual cores.

---

## 7. Virtual Scheduler Lab (Index 6)

The **Virtual Scheduler** executes synthetic simulation tasks within the virtual processor model.
- **Scheduling Policies**: Select between FCFS, Priority, and Round Robin.
- **Step & Run Modes**: Step simulation by single ticks or run continuously with speed control slider.
- **Simulated Metrics**: Discrete virtual makespan, core busy ticks, queue latency.

---

## 8. Data Parallelism (Index 7)

The **Data Parallelism** workstation visualizes Scatter-Compute-Gather numerical chunk processing on host hardware.
- **Computational Kernels**:
  - `transcendental`: $\sin(x) + \cos(x) + \exp(-x)$
  - `polynomial`: $a x^3 + b x^2 + c x + d$
  - `matrix_norms`: Frobenius norm calculations
  - `prime_count`: Trial-division prime testing
  - `sum_of_squares`: Parallel reduction
- **Dataset Size Slider**: Partition arrays from $1,000$ to $2,000,000$ elements.
- **Real Worker Selection**: Choose between automatic logical processor selection or manual worker counts.
- **Verification**: Exact numerical output validation comparing parallel results with a sequential baseline.
- **Residual Overhead Calculation**: Measures exact mathematical interval union ($T_{\text{union}}$) and no-worker-compute time.

---

## 9. Task Parallelism (Index 8)

The **Task Parallelism** workstation manages heterogeneous workloads and Directed Acyclic Graph (DAG) dependencies.
- **DAG Presets**:
  - `Diamond DAG`: 4-task classic diamond pipeline ($A \rightarrow B, C \rightarrow D$).
  - `Scientific Suite`: 6-task matrix-heavy scientific pipeline.
  - `Independent Suite`: 4 decoupled tasks executing in parallel.
  - `Fan-Out / Fan-In`: 1-to-4 scatter-gather pipeline.
- **Custom DAG Editor**: Add custom tasks, set CPU priorities, and define dependency parents.
- **Fault Tolerance**: Demonstrates automatic retry cascades and child branch cancellation on simulated kernel failures.

---

## 10. Process Scheduler Simulator (Index 11)

The **Process Scheduler** workstation simulates classic OS uniprocessor scheduling algorithms with interactive timelines.
- **Algorithms**: FCFS, Non-Preemptive SJF, Preemptive SRTF, Priority (Non-Preemptive & Preemptive with Aging), Round Robin (configurable quantum).
- **Gantt Chart Canvas**: Interactive, zoomable, and scrollable vector timeline displaying exact dispatch, execution, and preemption ticks.
- **Comparative Analysis Dialog**: One-click "Compare All Algorithms" modal evaluating turnaround time, waiting time, and context switch counts side-by-side.

---

## 11. Performance Analytics (Index 9)

The **Performance Analytics** dashboard provides deep scalability evaluation and historical tracking.
- **Speedup & Efficiency**: Directly measured and mathematically derived metrics across worker scalability sweeps.
- **Amdahl's Law Calculator**: Interactive theoretical speedup curve plotter with configurable parallel fraction ($P$) and asymptotic limits ($S_{\max} = \frac{1}{1-P}$).
- **Benchmark History Storage**: Persistent, mtime-cached JSON benchmark database with instant lookup and table sorting.

---

## 12. Settings (Index 10)

The **Settings** page configures operational boundaries and background services.
- **Worker Timeouts**: Configurable execution time limits ($5.0\text{s}$ to $60.0\text{s}$) before graceful termination escalation.
- **Monitoring Refresh Rate**: Dynamic slider adjusting background sampling frequency ($200\text{ms}$ to $5000\text{ms}$).
- **Benchmark Run Counts**: Adjust warmup iterations and measured repetitions for statistical confidence.

---

## 13. Real vs Virtual Comparison Workstation (Index 12)

The **Comparison Workstation** unifies physical OS multiprocessing and software simulation under a single experimental harness.
- **Mode Toggle**:
  - `Compare Both Environments`: Sequential execution (Real System first, then Virtual Lab).
  - `Real System Only`: Executes exclusively on physical OS processes.
  - `Virtual Lab Only`: Executes exclusively in software simulation.
- **Comparative Metrics**:
  - **Completion Order Concordance**: Evaluates relative sequence rank correlation ($0.0$ to $1.0$).
  - **Resource Allocation Ratio**: $W_{\text{real}} / C_{\text{virtual}}$.
  - **Utilization Delta**: Real worker busy ratio minus virtual core utilization percentage ($\Delta U\%$).
- **Dual Timelines**: Independent vector canvases displaying physical compute intervals on a seconds ($s$) axis alongside virtual core tracks on a ticks axis.

