# Changelog

All notable changes to the CoreSync project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.9.0] - Phase 9: Performance Analytics, Repeatable Benchmarking & Amdahl's Law

### Added
- **Performance Analytics Engine (`engine/analytics/`)**:
  - `models.py`: Strict `MetricClassification` enum (`DIRECTLY_MEASURED`, `MATHEMATICALLY_DERIVED`, `ESTIMATED_RESIDUAL`, `SIMULATED_VIRTUAL`), `calculate_sample_statistics()` (mean, median, min, max, sample standard deviation with Bessel's correction $N-1$), and `ScalabilityMetrics` with division-by-zero protection.
  - `amdahl.py`: Pure-Python `AmdahlCalculator` implementing Gene Amdahl's 1967 scalability law ($S = 1 / ((1 - P) + P / N)$), theoretical efficiency, serial bottleneck quantification ($1 - P$), maximum speedup asymptote ($S_{\max} = 1 / (1 - P)$), core sweeps, and educational documentation of real-world hardware limitations (strong scaling, cache saturation, asymmetric cores).
  - `benchmarking.py`: Repeatable multi-run benchmark orchestrator for Data Parallelism, Task Parallelism, CPU Scheduling, and Virtual Lab subsystems. Includes warm-up pass isolation, cooperative cancellation, worker cleanup via `ProcessManager`, and verification certification.
  - `history.py`: Local JSON persistence manager (`BenchmarkHistoryManager`) with corruption resilience, metadata indexing, session loading, and record deletion.
- **Custom QPainter Visualization Widgets (`gui/components/analytics_chart.py`)**:
  - `AmdahlCurveWidget`: Real-time vector plot of theoretical Amdahl speedup curve, linear ideal scaling ($S = N$), horizontal asymptote ($S_{\max}$), and active operating point with drop lines and efficiency readout.
  - `ScalabilityChartWidget`: Empirical multi-worker speedup measurements plotted against linear ideal scaling with discrete data point callouts.
  - `TimingBreakdownWidget`: Stacked horizontal bar chart depicting execution lifecycle timing overheads (Process Startup, Task Dispatch, Computation, Result Collection, Result Merge, Residual Overhead).
- **Comprehensive GUI Workstation Page (`gui/performance.py` & `gui/analytics_runner.py`)**:
  - 7 organized tabs:
    1. Overview Dashboard (Dual Environment Paradigm, global rollups, provenance classification key).
    2. Data Parallelism Analytics (worker sweeps, warm-up isolation, speedup/efficiency cards, scalability & timing charts).
    3. Task Parallelism Analytics (DAG makespan, actual speedup vs sequential baseline, worker utilization, timing chart).
    4. CPU Scheduling Analytics (cross-algorithm comparative matrix, optimal waiting/turnaround/CS cards).
    5. Virtual Lab Analytics (multicore simulation, discrete tick elapsed duration, virtual core capacity).
    6. Benchmark History (persistent session archive, detailed JSON inspection pane, deletion).
    7. Amdahl's Law Calculator (interactive parallel fraction $P$ and processor count $N$ sliders with live curve updates).
  - Background `AnalyticsBenchmarkRunnerThread` coordinating asynchronous execution without GUI freezes.
- **Automated Tests**:
  - `tests/test_performance_analytics.py`: 16 comprehensive unit tests covering hand-calculated formulas, division by zero, worker utilization clamping, sample statistics, Amdahl boundary conditions, monotonic curves, history CRUD, and multi-run executor sweeps.
  - `tests/test_performance_gui.py`: 8 GUI integration tests covering tab navigation, slider updates, benchmark result rendering, and chart repaints.
  - Total test suite now stands at **206 passing tests** (100% pass rate).

## [0.8.0] - Phase 8 & 8.1: CPU Scheduling Simulator & Interactive Timeline

### Added
- **CPU Scheduling Subsystem (`engine/process_scheduler/`)**:
  - 6 classical algorithms: FCFS, SJF, SRTF, Non-preemptive Priority, Preemptive Priority, Round Robin.
  - Dynamic Priority Aging with deterministic FCFS tie-breaking.
  - Context-switch overhead accounting.
  - Visual Gantt chart canvas with zoom and pan controls.
  - Algorithm comparison matrix dialog and workload presets.

## [0.7.0] - Phase 7: Unified Process Management, Worker Lifecycle, CPU Affinity and Resource Allocation

### Added
- **Unified Process Manager (`engine/process_manager.py`)**:
  - Centralized worker lifecycle coordinator tracking `PID`, `Parent PID`, `Worker ID`, `Engine Name`, `Task/Chunk ID`, `Assigned CPU Affinity`, `Actual CPU Affinity`, `Status`, `Start/End Times`, `CPU %`, `Memory RSS (MB)`, `Exit Code`, and `Error Message`.
  - Integrated 4-stage shutdown protocol: Cooperative Cancellation (`Event.set()`) $\rightarrow$ Graceful `SIGTERM` $\rightarrow$ Forceful `SIGKILL` $\rightarrow$ Final `join()` to reap zombie processes.
  - Thread-safe global active worker registry accessible to GUI monitoring threads and background services.
  - Cross-platform orphan process detection (`detect_orphans()`) and automated termination (`reap_orphans()`) restricted strictly to CoreSync worker process signatures.
- **CPU Affinity Management Subsystem (`engine/affinity.py`)**:
  - Cross-platform affinity assignment and inspection (`set_process_affinity()`, `get_process_affinity()`, `get_available_system_cpus()`).
  - Native Linux support using `os.sched_setaffinity` and `os.sched_getaffinity` with `psutil` fallback.
  - Windows support using `psutil.Process().cpu_affinity()`.
  - Graceful macOS (Darwin) fallback acknowledging kernel lack of thread/process pinning without silently fabricating success.
  - Configurable worker allocation policies: `AUTOMATIC`, `ROUND_ROBIN`, `ONE_TO_ONE`, `MANUAL`, `CUSTOM`, `P_CORE_ONLY`, and `E_CORE_ONLY`.
  - Verified hybrid processor filtering restricting workers to P-cores or E-cores only when reliable PMU/sysfs topology detection exists.
- **Resource Management & Safety Safeguards (`engine/resource_guard.py`)**:
  - Dynamic worker concurrency bounds (`clamp_worker_count`) preventing accidental infinite process creation.
  - System memory headroom verification (`check_memory_headroom`) before spawning worker pools.
  - Heavy system load detection (`is_system_under_heavy_load`).
  - Worker memory threshold inspection (`check_worker_limit_violation`).
- **Engine Integrations**:
  - `DataParallelExecutor`: Integrated with `ProcessManager` and `AffinityPolicy` (automatic, round-robin, one-to-one, P-core, E-core). Affinity applied before chunk execution starts.
  - `TaskParallelExecutor`: Integrated with `ProcessManager` and `AffinityPolicy`. Workers spawned with explicit affinity, dynamically tracked across DAG tasks, and cleaned up cleanly.
  - `RealCPUStressGenerator`: Refactored to utilize `ProcessManager` with engine name `CPUStress`, support core pinning policies, and cleanly reap all stress workers.
- **GUI Updates**:
  - `RealProcessPage` (`gui/real_system/process_view.py`): Added dedicated CoreSync Active Workers management card with live worker table (PID, PPID, Engine, Task, Assigned CPUs, Status, CPU %, RSS MB, Cancel button), affinity policy selector, orphan counter, and global "Cancel All Workers" / "Reap Orphans" actions.
  - `CoreMonitorPage` (`gui/core_monitor.py`): Added live worker pinning indicators and highlight borders on `CoreWidget` indicating when a logical CPU has active CoreSync workers running on it.
  - `DataParallelismPage` & `TaskParallelismPage`: Added CPU Affinity Policy dropdowns directly in workload control panels.
- **Automated Tests (`tests/test_process_manager.py`)**:
  - Added 21 comprehensive unit and integration tests covering registration, state transitions, PID/PPID tracking, valid affinity assignment, invalid CPU ID handling, permission-denied fallback, Darwin unsupported fallback, round-robin allocation, manual mapping, hybrid P/E core filtering, non-hybrid fallback, cooperative cancellation, forced termination, zombie reaping, orphan detection/reaping, memory headroom checks, Data Parallelism integration, Task Parallelism integration, CPU Stress integration, and GUI snapshot updates.
  - Test suite now stands at **121 passing tests** (100% pass rate).

## [0.6.2] - Phase 6.2: Task Parallelism Verification Integrity Audit

### Added
- **Full Output Equivalence Verification (`engine/task_parallel/verification.py`)**:
  - `matrix_mult`: Upgraded comparison to full element-by-element equality using `numpy.allclose(mat_seq, mat_par, rtol=1e-5, atol=1e-8)`. Retained trace and Frobenius norm as supplementary metrics.
  - `sorting`: Upgraded comparison to full sorted array equality using `numpy.allclose(arr_seq, arr_par)` and verified monotonic ascending order.
  - `fibonacci`: Upgraded comparison to full exact integer representation (`seq["fib_value"] == par["fib_value"]`), retaining digit counts and trailing digits as supplementary metrics.
  - `prime_calc`: Upgraded comparison to full prime integer sequence equality (`seq["primes"] == par["primes"]`).
  - `data_transform`: Upgraded comparison to full floating-point array element-by-element equality via `numpy.allclose()`.
  - `numerical_integration`: Preserved scalar Simpson quadrature numerical comparison within defined tolerance ($|I_{\text{seq}} - I_{\text{par}}| \le \text{atol} + \text{rtol} \cdot |I_{\text{seq}}|$).
- **Kernel Payload Retentions (`engine/task_parallel/operations.py`)**:
  - Retained `primes` list in `_kernel_prime_calc`.
  - Retained `matrix` ndarray in `_kernel_matrix_mult`.
  - Retained `sorted_array` ndarray in `_kernel_sorting`.
  - Retained `fib_value` exact integer in `_kernel_fibonacci`.
  - Retained `output_array` ndarray in `_kernel_data_transform`.
- **Integrity Tests (`tests/test_task_parallel.py`)**:
  - Added 5 adversarial integrity tests verifying that `compare_results()` rejects:
    1. Matrices with matching trace and Frobenius norm but differing elements.
    2. Sorted arrays with matching min, max, and monotonicity but differing internal items.
    3. Fibonacci numbers with matching digit count and trailing digits but differing values.
    4. Verification failures strictly invalidating actual speedup ($S \to 0.0$).
    5. Verification overhead is excluded from sequential and parallel execution makespans.
  - Test suite now stands at **100 passing tests** (100% pass rate).

## [0.6.1] - Phase 6.1: Task Parallelism Benchmark Metric Audit

### Changed
- **Separated Speedup, Parallelism Ratio, and Worker Utilization**:
  - Replaced ambiguous speedup metric with three mathematically rigorous metrics:
    1. **Actual Speedup**: $S = T_{\text{seq}} / T_{\text{par}}$ comparing single-threaded sequential baseline execution with parallel makespan.
    2. **Parallelism Ratio**: $P = \sum T_{\text{worker-compute}} / T_{\text{par}}$ measuring concurrency density (average active worker count).
    3. **Worker Utilization**: $U = \frac{\sum T_{\text{worker-compute}}}{\text{Worker Count} \times T_{\text{par}}} \times 100\%$ strictly bounded between 0.0% and 100.0%.
- **Sequential Baseline Execution (`engine/task_parallel/executor.py`)**:
  - Implemented `run_sequential()` executing an identical replica of the DAG (`graph.clone()`) on 1 worker in strict topological order with identical inputs.
  - Implemented `run_benchmark()` coordinating sequential baseline execution, parallel DAG dispatch, and mathematical output comparison via `TaskVerifier.compare_results()`.
  - Guaranteed that failed or cancelled runs report $S = 0.0$ and are never treated as valid benchmarks.
- **GUI Telemetry Updates (`gui/task_parallelism.py`)**:
  - Updated metrics grid to display Sequential Baseline ($T_{\text{seq}}$), Parallel Makespan ($T_{\text{par}}$), Actual Speedup ($S$), Parallelism Ratio ($P$), Worker Utilization ($U$), and Cumulative Compute Time ($T_{\text{cpu}}$).
  - Added "Measure Sequential Baseline for Actual Speedup" toggle.
- **Automated Tests (`tests/test_task_parallel.py`)**:
  - Added 6 new unit and integration tests covering sequential baseline runs, correctness comparisons, mathematical formulas for $S$, $P$, and $U$, utilization clamping, zero-duration edge cases, and failed benchmark speedup resetting.
  - Test suite now stands at **95 passing tests** (100% pass rate).

## [0.6.0] - Phase 6: Task Parallelism Engine: Task Queues, DAG Dependencies, Worker Execution & Monitoring

### Added
- **Task Parallelism Engine (`engine/task_parallel/`)**:
  - `Task`: Dataclass with robust state machine transitions (`PENDING`, `READY`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `BLOCKED`). Enforces valid transitions and maintains execution timestamps.
  - `TaskGraph`: Directed Acyclic Graph (DAG) manager providing cycle detection via Kahn's algorithm, topological ordering, prerequisite validation, dynamic unblocking of children (`on_task_completed`), failure cascading to descendants (`on_task_failed`), and deadlock detection.
  - `TaskQueue`: Pluggable scheduling queue supporting **First-Come, First-Served (FIFO)**, **Priority Scheduling**, and **Shortest Job First (SJF)** based on task duration estimates.
  - `operations.py`: Six genuine CPU-bound computational kernels:
    1. Prime Number Sieve & Trial Division (`prime_calc`)
    2. Dense Matrix Multiplication & Frobenius Norm (`matrix_mult`)
    3. Simpson's Rule Numerical Integration (`numerical_integration`)
    4. Sorting & Monotonicity Verification (`sorting`)
    5. Fibonacci Fast Doubling Computation (`fibonacci`)
    6. Multi-Pass Transcendental Data Transformation (`data_transform`)
  - `worker.py`: Isolated spawned child process worker loop executing tasks without PySide6/Qt imports.
  - `dispatcher.py`: `TaskDispatcher` tracking idle/busy workers and mapping active operating system PIDs with automatic hardware-based worker allocation heuristics.
  - `verification.py`: `TaskVerifier` checking mathematical invariants (matrix norms, prime properties, sorted arrays, finite integrals).
  - `result_collector.py`: `ResultCollector` aggregating execution logs, makespan ($T_{par}$), cumulative compute work ($T_{cpu}$), speedup ($S$), and worker utilization percentage.
  - `executor.py`: `TaskParallelExecutor` orchestrating asynchronous DAG dispatch, retry policies up to `max_retries`, cooperative cancellation, and strict 4-stage worker cleanup (cooperative -> SIGTERM -> SIGKILL -> join) with zero orphan processes.
  - `presets.py`: Five realistic preset DAG workflows: Diamond Pipeline, Heterogeneous Scientific Suite, Fan-Out/Fan-In Pipeline, Independent Concurrency Suite, and Fault Tolerance & Retry Test.
- **Interactive Workstation GUI (`gui/task_parallelism.py` & `gui/components/dag_canvas.py`)**:
  - `DAGCanvasWidget`: Custom `QPainter` widget dynamically visualizing DAG nodes, topological layers, directed Bezier connection arrows, and status color transitions (Green, Blue, Yellow, Dark, Red, Purple).
  - Background `TaskParallelRunnerThread` coordinating execution without blocking Qt event loops.
  - Real-time metrics grid for Total Tasks, Running Tasks, Completed Tasks, Failed/Blocked Tasks, Parallel Makespan, and Speedup.
  - Worker process status badges reporting live PIDs and assigned tasks.
  - Task telemetry table reporting ID, Name, Type, Priority, Status, Worker/PID, Duration, and Dependencies.
- **Automated Test Suite Expansion (`tests/test_task_parallel.py`)**:
  - 23 new comprehensive tests covering task models, invalid transitions, FIFO/Priority/SJF queues, topological sorting, cycle detection, self-dependencies, missing dependencies, all 6 kernels, verifications, concurrent execution, scientific pipeline, independent suite, retries, failure cascades, cooperative cancellation, worker Qt isolation, and GUI page preset switching.
  - Total test suite now stands at **89 passing tests** (100% pass rate).

## [0.5.2] - Phase 5.2: Benchmark Metric Terminology Correction

### Changed
- **Input Latency Metric Renaming**:
  - Renamed `input_ipc_latency_s` to `input_delivery_latency_s` in `WorkerResult` and `ParallelTimingBreakdown`.
  - Clarified definition: this measurement measures end-to-end input delivery latency encompassing queue waiting, serialization/delivery, and worker process wake-up / OS scheduling delay (not pure IPC pipe transit time).
  - Maintained backwards-compatible property alias `input_ipc_latency_s` on `WorkerResult` and `avg_input_ipc_s` on `ParallelTimingBreakdown`.
- **Derived IPC Overhead Clarification**:
  - Renamed derived metric $T_{dispatch} + \max(0, T_{collection} - T_{max\_worker\_compute})$ from direct "IPC Overhead" to **"Estimated Distribution and Collection Overhead"** (`estimated_distribution_overhead_s`).
  - Documented that this value is a derived residual estimate and includes OS process scheduling, synchronization delays, and queue contention rather than pure transport wire overhead.
  - Retained backwards-compatible property alias `ipc_overhead_s`.
- **Collection Timing Window Clarification**:
  - Renamed collection phase description to **"Parallel Execution and Result Collection Window"** (`collection_s`), documenting that worker computation overlaps concurrently with this interval on the master process.
- **UI & Telemetry Refinements (`gui/data_parallelism.py`)**:
  - Updated overhead breakdown label to `Estimated Distribution and Collection Overhead`.
  - Updated worker table header to `Compute Time (Input Delivery Latency)`.
  - Updated per-chunk status format to reflect delivery delay (`X ms (Y ms delivery delay)`).

## [0.5.1] - Phase 5.1: IPC and Data Transfer Measurement Audit

### Added
- **Non-Overlapping Granular Timing Architecture (`ParallelTimingBreakdown`)**:
  - Phase 1: Process Startup Overhead ($T_{spawn}$): Dedicated timing of child process creation.
  - Phase 2: Input Slicing & IPC Dispatch ($T_{dispatch}$): Dedicated timing of dataset partitioning, task packaging, and serializing/putting tasks onto `multiprocessing.Queue`.
  - Phase 3: Parallel Execution & Result Gathering Window ($T_{collection}$): Wall-clock polling duration for worker completion.
  - Phase 4: Output Reassembly & Reduction Merge ($T_{merge}$): Array concatenation and scalar summation timing.
  - Verification that the sequential master phases strictly sum to total wall-clock time ($T_{total} \approx T_{spawn} + T_{dispatch} + T_{collection} + T_{merge}$) without double-counting.
- **Granular Worker & IPC Latency Metrics**:
  - `WorkerTask.dispatch_timestamp` and `WorkerResult.input_ipc_latency_s`: Measured IPC queue transit latency per chunk via shared `CLOCK_MONOTONIC`.
  - `max_worker_compute_s`: Critical-path computation duration across parallel worker pool.
  - `sum_worker_compute_s`: Cumulative CPU execution work across all child processes.
  - `ipc_overhead_s`: Total measured IPC distribution and collection overhead beyond compute.
- **UI & Telemetry Updates**:
  - Updated `gui/data_parallelism.py` to display the 6 non-overlapping timing components.
  - Added measured IPC latency per chunk in the worker process telemetry table.
- **Automated Tests**:
  - Added 3 new timing breakdown tests (`test_timing_breakdown_metrics_present_and_positive`, `test_timing_intervals_non_overlapping_and_consistent`, `test_worker_result_ipc_and_timestamps`).
  - Total test suite now stands at **66 passing tests** (100% pass rate).

## [0.5.0] - Phase 5: Actual Data Parallelism Engine: Partitioning, Multiprocessing, Scatter/Gather & Verification

### Added
- **Data Parallelism Engine (`engine/data_parallel/`)**:
  - `DataPartitioner`: Disjoint contiguous chunk partitioning supporting equal-sized chunks, uneven divisions with fair remainder distribution, zero-copy numpy slice views, and empty dataset edge cases.
  - `operations.py`: Five genuine CPU-bound computational kernels:
    1. Element-wise Transcendental Transformations (multi-pass trigonometric, exponential, square root, hyperbolic tangent).
    2. 8th-Order Horner Polynomial Evaluation (power expansion and series evaluation).
    3. Matrix Row Norms & Dot Products (Euclidean L2 vector norms and nonlinear cross terms across multi-dimensional matrix rows).
    4. Prime Number Sieve & Integer Factoring (trial division with 6k ± 1 optimization across integer intervals).
    5. Non-Linear Sum of Squares Reduction (parallel numerical aggregation).
  - `worker.py`: Isolated worker loop executing under POSIX `spawn` method with zero PySide6/Qt dependencies.
  - `result_collector.py`: Reassembles and concatenates array outputs in chunk order and reduces scalar outputs with timing measurements.
  - `verification.py`: Mathematical verification comparing parallel execution outputs directly against sequential baselines with configurable tolerances (`rtol`, `atol`), discrepancy counts, and maximum error metrics.
  - `executor.py`: `DataParallelExecutor` orchestrating sequential baseline runs, dynamic worker allocation heuristics, parallel spawn-based dispatch, cooperative cancellation, and 3-stage worker cleanup (cooperative -> SIGTERM -> SIGKILL).
- **Interactive GUI Integration (`gui/data_parallelism.py`)**:
  - `DataParallelRunnerThread`: Background `QThread` running compute workloads without blocking the GUI event loop.
  - Configuration card with kernel dropdown, dataset size spinner, automatic/manual worker allocation mode, random seed, and optional CPU cache warm-up.
  - Metrics grid displaying Speedup ($S = T_{seq} / T_{par}$), Parallel Efficiency ($E\%$), Sequential Time, Parallel Time, and Throughput.
  - Verification & Timing Breakdown card displaying verification status badge (`VERIFIED (100% matched)` / `FAILED`), discrepancy count, max diff, and overhead decomposition ($T_{spawn}, T_{compute}, T_{merge}$).
  - Worker process table displaying per-chunk status, assigned worker, OS PID, index range, item count, and compute duration.
- **Automated Test Suite Expansion (`tests/test_data_parallel.py`)**:
  - 19 new tests covering even/uneven partitioning, empty datasets, all 5 computational kernels, verification tolerances, automatic worker selection, single-worker and multi-worker execution, prime count reduction, cooperative cancellation with zero orphans, worker Qt isolation, and GUI mode switching.
  - Full test suite now passes with **63 passing tests** (100% pass rate).

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

