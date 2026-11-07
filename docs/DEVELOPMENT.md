# CoreSync Developer Guide

This document outlines architecture rules, development setup, module conventions, and contribution workflows for developers working on CoreSync.

---

## 1. Development Setup

### Python Environment
CoreSync requires **Python 3.11+** (tested through Python 3.14 on Linux, macOS, and Windows).

```bash
git clone https://github.com/academicos/coresync.git
cd coresync

python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .[dev,build]
```

### Running Test Suite
```bash
pytest tests/
```

For headless GUI test execution:
```bash
QT_QPA_PLATFORM=offscreen pytest tests/
```

---

## 2. Strict Architectural Boundaries

### Rule 1: No Qt Imports in Worker Modules
Worker processes are executed in separate OS processes using Python's `spawn` start method. To prevent crashes, symbol conflicts, and thread deadlocks, worker modules **MUST NOT** import `PySide6` or any Qt symbol:
- ✅ Allowed in workers: `numpy`, `psutil`, `math`, `time`, standard library.
- ❌ Forbidden in workers: `PySide6.QtCore`, `PySide6.QtWidgets`, `PySide6.QtGui`.

### Rule 2: Spawn Multiprocessing Context
Always obtain multiprocessing contexts via:
```python
import multiprocessing as mp
ctx = mp.get_context("spawn")
```
Never invoke `fork()` directly or rely on the default start method.

### Rule 3: Clock Domain Separation
Never divide physical seconds by virtual clock ticks:
```python
# FORBIDDEN:
speedup = real_wall_clock_s / virtual_makespan_ticks  # VIOLATES CLOCK DOMAINS

# REQUIRED:
from engine.comparison.models import assert_no_cross_domain_ratio
assert_no_cross_domain_ratio(real_wall_clock_s, virtual_makespan_ticks)
```

---

## 3. Subsystem Extension Points

### Adding a New Data Parallel Operation
1. Define the kernel in `engine/data_parallel/operations.py`:
   ```python
   def compute_my_kernel(chunk: np.ndarray) -> np.ndarray:
       return np.log1p(np.abs(chunk))
   ```
2. Register the operation in `SUPPORTED_OPERATIONS`:
   ```python
   SUPPORTED_OPERATIONS["my_kernel"] = compute_my_kernel
   ```
3. Add verification rule in `engine/data_parallel/verification.py`.
4. Register the kernel name in `engine/comparison/workload_mapper.py` (`SUPPORTED_DATA_PARALLEL_OPS`).

### Adding a New Task Parallelism DAG Preset
1. Create preset generator in `engine/task_parallel/presets.py`:
   ```python
   def create_my_custom_dag() -> TaskGraph:
       graph = TaskGraph("MyCustomDAG")
       # add tasks and dependencies...
       return graph
   ```
2. Register preset in `SUPPORTED_PRESETS`.
3. Add matching virtual task mapping in `engine/comparison/workload_mapper.py` (`SUPPORTED_TASK_PARALLEL_PRESETS`).

### Adding a CPU Scheduling Algorithm
1. Define algorithm class in `engine/process_scheduler/algorithms.py` inheriting from `SchedulingAlgorithmBase`.
2. Implement `step(self, current_tick: int, ready_queue: List[ScheduledProcess]) -> Optional[ScheduledProcess]`.
3. Register enum in `engine/process_scheduler/models.py`.
4. Add comprehensive mathematical hand-calculated tests in `tests/test_process_scheduler.py`.

---

## 4. Code Quality & Style Standards

- Format with standard PEP 8 conventions.
- Maintain type hints across all public APIs and model definitions.
- Preserve existing comments and docstrings.
- Ensure all subprocess resources are cleaned up cooperatively (zero orphan guarantee).

