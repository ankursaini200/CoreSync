# CoreSync Architecture Documentation

## 1. Overview & System Mission

**CoreSync** is a unified Operating Systems research and educational workstation designed to demonstrate, benchmark, and contrast actual multicore execution on host hardware (**Environment A: Real System**) with idealized software simulation (**Environment B: Virtual Lab**).

```mermaid
flowchart TD
    subgraph UI_LAYER["Presentation Layer (PySide6 / Qt 6.12)"]
        MAIN["MainWindow (13 Functional Pages, Dark Workstation Styling)"]
        SIDEBAR["Sidebar Navigation (6 Categories, 13 Pages)"]
        CANVAS["Custom Vector QPainter Canvases (Gantt, Interval Timelines, Core Grids)"]
    end

    subgraph THREAD_LAYER["Asynchronous Thread Coordinators (QThread)"]
        MON_THREAD["CPUMonitorService (psutil background telemetry)"]
        DP_THREAD["DataParallelRunnerThread"]
        TP_THREAD["TaskParallelRunnerThread"]
        ANALYTICS_THREAD["AnalyticsRunnerThread"]
        COMP_THREAD["ComparisonRunnerThread"]
    end

    subgraph ENGINE_REAL["Environment A: Real Multiprocessing Engines (spawn context)"]
        PM["ProcessManager (Worker registration, affinity, orphan prevention)"]
        DP_EXEC["DataParallelExecutor (Array chunking, scatter-gather)"]
        TP_EXEC["TaskParallelExecutor (TaskGraph DAG dependencies, worker pool)"]
        STRESS["RealStressGenerator (Bounded duty-cycle CPU stress)"]
        AFFINITY["AffinityManager (Linux sched_setaffinity, P/E core pinning)"]
    end

    subgraph ENGINE_VIRTUAL["Environment B: Software Virtual Lab Simulation"]
        VCPU["VirtualCPU (1..128 cores, homogeneous or hybrid P/E)"]
        VSCHED["VirtualScheduler (FCFS, Priority, Preemptive Round Robin)"]
        VGEN["VirtualWorkloadGenerator (Simulated synthetic tasks)"]
    end

    subgraph SCHED_SIM["Process Scheduling Simulation Engine"]
        SIM["SchedulerSimulator (FCFS, SJF, SRTF, Priority+Aging, Round Robin)"]
        GANTT["TimelineBuilder & Gantt Visualizer"]
        COMPARATOR["AlgorithmComparator (Turnaround, waiting, context switches)"]
    end

    subgraph ANALYTICS_LAYER["Performance Analytics & Comparison"]
        AMDAHL["AmdahlCalculator (Theoretical speedup asymptote curves)"]
        HISTORY["BenchmarkHistoryManager (mtime-cached JSON persistence)"]
        COMP_MAPPER["ComparisonWorkloadMapper (DP kernels & DAG presets)"]
        COMP_RUNNER["ComparisonRunner (Sequential execution, concordance, resource ratio)"]
        FIREWALL["Clock Domain Firewall (assert_no_cross_domain_ratio)"]
    end

    MAIN --> THREAD_LAYER
    THREAD_LAYER --> ENGINE_REAL
    THREAD_LAYER --> ENGINE_VIRTUAL
    THREAD_LAYER --> SCHED_SIM
    ENGINE_REAL --> ANALYTICS_LAYER
    ENGINE_VIRTUAL --> ANALYTICS_LAYER
    ANALYTICS_LAYER --> UI_LAYER
```

---

## 2. Strict Architectural Invariants

CoreSync enforces strict separation of concerns across its architectural boundaries:

1. **Worker Isolation from Qt**:
   Worker processes spawned for Data Parallelism, Task Parallelism, and Real CPU Stress **MUST NEVER** import `PySide6` or any Qt modules. Worker entry points reside in standalone modules (`engine.data_parallel.worker`, `engine.task_parallel.worker`) communicating purely via pickle-safe IPC queues and primitive Python dataclasses.
2. **Process Spawn Context**:
   `multiprocessing.set_start_method("spawn", force=True)` is enforced at application startup. Forking is strictly prohibited to prevent deadlocks with Qt's C++ thread runtime and X11/Wayland display sockets.
3. **Clock Domain Separation**:
   Real System elapsed monotonic time (seconds) and Virtual Lab simulated time (discrete logical clock ticks) belong to separate, incommensurable domains. **Dividing seconds by ticks is strictly prohibited** by `assert_no_cross_domain_ratio`.

---

## 3. Process Management Subsystem

The unified `ProcessManager` (`engine/process_manager.py`) coordinates child worker lifecycles, resource allocation, CPU affinity, and orphan prevention across all execution engines.

```mermaid
sequenceDiagram
    participant P as Parent Process (CoreSync GUI)
    participant W as Child Worker Process
    participant K as OS Kernel (Linux / Win32 / macOS)

    P->>P: Register WorkerMetadata (spawn start_method)
    P->>W: Spawn child worker process
    activate W
    Note over W: Worker Entrypoint Startup

    alt Linux OS
        W->>K: prctl(PR_SET_PDEATHSIG, SIGTERM)
        W->>K: os.getppid() check
        Note over W: If PPID != expected parent PID -> Terminate immediately
        W->>W: Start child-side polling watchdog (100ms)
    else Windows OS
        W->>K: OpenProcess(SYNCHRONIZE, parent_pid)
        W->>W: WaitForSingleObject thread blocks on parent death
    else macOS / Darwin
        W->>K: kqueue EVFILT_PROC NOTE_EXIT (when supported)
        W->>W: Start child-side polling watchdog (100ms)
    end

    Note over P,W: Workload Execution (Data / Task Parallelism)

    alt Normal Completion
        W-->>P: IPC Result Message
        P->>W: Process Join
        deactivate W
    else Parent Crash / SIGKILL
        K-->>W: Kernel delivers SIGTERM (Linux) / Handle Signals (Win32)
        W->>W: os._exit(0) immediate cooperative termination
        Note over W: Zero Orphan Processes Guaranteed
    end
```

### Triple-Shield Orphan Defense
1. **Kernel-Level Termination**: On Linux, `prctl(PR_SET_PDEATHSIG, SIGTERM)` instructs the Linux kernel to send `SIGTERM` to the child worker the instant the parent thread dies.
2. **Startup Race Check**: Between child fork/spawn and `prctl` execution, the parent could theoretically die. The child worker captures `expected_parent_pid` before enabling protection, invokes `prctl`, and immediately checks `os.getppid()`. If reparented to `systemd`/`init` (PID 1), it aborts immediately.
3. **Child-Side Watchdog Thread**: A dedicated daemon thread in every worker inspects parent liveness every 100ms. If the parent disappears, the child terminates itself without relying on parent-side cleanup.

---

## 4. Data Parallelism Subsystem

The Data Parallelism engine (`engine/data_parallel/`) visualizes and executes Scatter-Compute-Gather patterns on host hardware.

```mermaid
flowchart LR
    DATA["Raw Numerical Dataset (NumPy array)"] --> PART["DataPartitioner"]
    PART --> C1["Chunk 1"]
    PART --> C2["Chunk 2"]
    PART --> CN["Chunk N"]

    C1 --> W1["Worker 1 (spawned PID)"]
    C2 --> W2["Worker 2 (spawned PID)"]
    CN --> WN["Worker N (spawned PID)"]

    W1 --> R1["WorkerResult 1"]
    W2 --> R2["WorkerResult 2"]
    WN --> RN["WorkerResult N"]

    R1 & R2 & RN --> GATHER["Result Verifier & Gatherer"]
    GATHER --> OUT["Verified Output Array & Metric Analysis"]
```

### High-Resolution Interval Instrumentation
Rather than calculating residuals by subtracting summed worker durations from makespan, CoreSync calculates the **Exact Mathematical Interval Union**:
$$T_{\text{union}} = \left| \bigcup_{i=1}^{W} [t_{\text{start}, i}, t_{\text{finish}, i}] \right|$$
$$T_{\text{no\_worker\_compute}} = T_{\text{makespan}} - T_{\text{union}}$$
This guarantees that worker overlap during concurrent execution does not distort elapsed non-compute overhead measurements.

---

## 5. Task Parallelism Subsystem

The Task Parallelism engine (`engine/task_parallel/`) implements a dynamic Directed Acyclic Graph (DAG) dependency executor.

```mermaid
flowchart TD
    subgraph DAG["TaskGraph (Diamond DAG Example)"]
        T1["Task 1: Initialization"]
        T2["Task 2: Matrix Multiplication"]
        T3["Task 3: Prime Sieve"]
        T4["Task 4: Reduction & Norm"]

        T1 --> T2
        T1 --> T3
        T2 --> T4
        T3 --> T4
    end

    subgraph DISPATCH["Dynamic Dispatcher & Worker Pool"]
        QUEUE["Priority / SJF / FIFO Task Queue"]
        WPOOL["Worker Process Pool (spawn)"]
    end

    DAG --> QUEUE
    QUEUE --> WPOOL
    WPOOL --> GATHER["Result Collector & Verification Engine"]
```

### Fault Isolation & Retry Cascades
- Individual task failures trigger bounded exponential retries.
- If a task exceeds its maximum retry threshold, dependent child tasks are automatically canceled via dependency cascade while independent sibling branches continue uninterrupted.

---

## 6. CPU Scheduling Simulator

The CPU Scheduling engine (`engine/process_scheduler/`) models uniprocessor CPU scheduling policies:

- **FCFS**: First-Come, First-Served (non-preemptive).
- **SJF**: Shortest Job First (non-preemptive).
- **SRTF**: Shortest Remaining Time First (preemptive).
- **Priority**: Preemptive and Non-Preemptive with starvation aging.
- **Round Robin**: Time-sliced execution with configurable quantum.

### Aging Algorithm Integrity
Effective priority is updated strictly as a function of time spent in the `READY` queue:
$$\text{effective\_prio} = \text{initial\_prio} \pm \left\lfloor \frac{t_{\text{waiting}}}{\text{aging\_interval}} \right\rfloor \times \text{aging\_step}$$
Running time on the CPU does not contribute to aging; preempted processes resume accumulating waiting time from their exact preemption tick.

---

## 7. Real vs Virtual Comparison Subsystem

The Comparison Workstation (`engine/comparison/`) translates identical computational workloads into both real and virtual domains:

```mermaid
flowchart TD
    WORKLOAD["ComparisonWorkloadConfig (Paradigm, Kernel/Preset, Size)"]
    MAPPER["ComparisonWorkloadMapper"]

    WORKLOAD --> MAPPER
    MAPPER --> REAL_MAP["MappedRealWorkload (NumPy array or TaskGraph)"]
    MAPPER --> VIRT_MAP["MappedVirtualWorkload (VirtualTasks with DAG constraints)"]

    REAL_MAP --> REAL_RUN["RealComparisonExecutor (Real host multiprocessing)"]
    VIRT_MAP --> VIRT_RUN["VirtualComparisonExecutor (VirtualCPU + VirtualScheduler)"]

    REAL_RUN --> M_REAL["RealExecutionResult (wall_clock_time_s, RSS MB, host load)"]
    VIRT_RUN --> M_VIRT["VirtualExecutionResult (virtual_makespan_ticks, busy ticks)"]

    M_REAL & M_VIRT --> ANALYSIS["ComparisonMetricsCalculator"]

    ANALYSIS --> CONCORD["Completion Order Concordance (Rank Correlation)"]
    ANALYSIS --> RATIO["Resource Ratio: W_real / C_virtual"]
    ANALYSIS --> UDELTA["Utilization Delta: U_real - U_virtual"]
    ANALYSIS --> FIREWALL["Clock Domain Firewall: assert_no_cross_domain_ratio"]
```

### Sequential Execution in Compare Both Mode
In `COMPARE_BOTH` mode, the Real System executes first, followed by the Virtual Lab. This eliminates host CPU contention and CPU cache pollution, guaranteeing pristine physical benchmark measurements.

