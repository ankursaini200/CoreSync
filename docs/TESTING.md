# CoreSync Testing & Verification Suite

This document details the automated testing framework, test inventory, regression checklist, and verification protocols for CoreSync.

---

## 1. Test Architecture & Runner Setup

CoreSync uses `pytest` and `pytest-qt` for full-stack unit, integration, and graphical testing:

```bash
# Run the entire test suite
pytest tests/

# Run with verbose output and timing summary
pytest -v --durations=10 tests/

# Run specific subsystem test module
pytest tests/test_comparison_runner.py
```

### Windows Test Execution
On Windows 10/11, execute the test suite using Command Prompt:
```cmd
test_windows.bat
```
Or via PowerShell:
```powershell
.\test_windows.ps1
```

### Headless Environment Execution (Linux CI/CD)
For CI/CD servers, headless workstations, or containerized build environments where no X11 or Wayland display server is running:
```bash
QT_QPA_PLATFORM=offscreen pytest tests/
```

---

## 2. Test Inventory by Subsystem

The test suite contains **272 passing tests** across 25 test modules:

| Subsystem | Test Module | Test Count | Focus & Coverage |
| :--- | :--- | :--- | :--- |
| **System Info & CPU Topology** | `test_system_info.py`<br>`test_cpu_topology.py` | 11 | Sysfs parsing, core range parsing, hybrid P/E core identification, hyperthread sibling pairs |
| **Hardware Providers & Fallbacks** | `test_hardware_providers.py`<br>`test_platform_compatibility.py` | 10 | Cross-platform hardware factory, Windows/macOS mock detection, platform capabilities |
| **Windows Native Compatibility** | `test_windows_native_compat.py` | 11 | Windows Registry parsing, WMIC/PowerShell fallback, Win32 `OpenProcess(SYNCHRONIZE)` handle watchdog, Win32 processor numbers, startup race guard, `freeze_support` |
| **Background CPU Monitor** | `test_cpu_monitor.py` | 4 | `CPUMonitorService` QThread lifecycle, sampling signal propagation, clean thread teardown |
| **Real CPU Stress Generator** | `test_real_stress.py` | 3 | 30-second safety clamp, immediate halt within 500ms, duty-cycle throttling, zero orphans |
| **Process Management & Affinity** | `test_process_manager.py` | 19 | Parent-death protection (`PR_SET_PDEATHSIG`, Win32 `SYNCHRONIZE`, reparenting watchdog), CPU affinity policies |
| **Data Parallelism** | `test_data_parallel.py` | 16 | Array partitioning, 5 computational kernels, output verification, interval union timing, zero orphans |
| **Task Parallelism & DAGs** | `test_task_parallel.py` | 27 | Task state transitions, priority queues, DAG topological sort, cycle detection, retry cascades, fault isolation |
| **Process Scheduler Simulation** | `test_process_scheduler.py`<br>`test_process_scheduler_audit.py` | 41 | FCFS, SJF, SRTF, Preemptive/Non-preemptive Priority with starvation aging, Round Robin quantum boundary tests |
| **Virtual Lab Engine** | `test_virtual_lab.py` | 7 | `VirtualCPU` homogeneous and hybrid models, `VirtualScheduler`, discrete tick isolation from real hardware |
| **Performance Analytics & Amdahl** | `test_performance_analytics.py`<br>`test_interval_timing.py`<br>`test_input_isolation.py` | 38 | Amdahl theoretical curves, asymptotic bounds, history persistence, deep input cloning immutability |
| **Real vs Virtual Comparison** | `test_comparison_models.py`<br>`test_comparison_workload_mapper.py`<br>`test_comparison_runner.py`<br>`test_comparison_metrics.py`<br>`test_comparison_gui.py` | 23 | Comparison models, DP/DAG mapping, sequential runner, order concordance, resource ratio, dual canvases |
| **GUI & Navigation** | `test_gui_navigation.py`<br>`test_performance_gui.py`<br>`test_process_scheduler_gui.py`<br>`test_settings_gui.py` | 62 | 13-page navigation switching, breadcrumbs, zoom/canvas rendering, comparative dialogs, settings persistence |
| **Total Test Suite** | **25 Test Modules** | **272 Tests** | **100% Passing (0 failures, 0 errors)** |

> [!NOTE]
> Physical test runs in our primary development environment are executed on Arch Linux (`Linux 7.2.14-arch1-1 x86_64`). Windows native subsystems (WinReg hardware detection, Win32 `OpenProcess(SYNCHRONIZE)` handle wait, Win32 processor numbers, `freeze_support` lifecycle, and path safety) are tested via dedicated unit test suites (`tests/test_windows_native_compat.py`). To validate natively on a Windows 10/11 workstation, execute `test_windows.bat` or `.\test_windows.ps1`.

---

## 3. Orphan Process Verification Protocol

CoreSync enforces a strict **Zero Orphan Guarantee**:
After running benchmarks, stress tests, or the test suite, no lingering child worker processes may remain running in the OS.

### Automated Orphan Check Command
```bash
python -c "
import psutil, os
current_pid = os.getpid()
orphans = []
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmd = ' '.join(p.info['cmdline'] or [])
        if 'coresync' in cmd.lower() or 'multiprocessing' in cmd.lower():
            if p.info['pid'] != current_pid and p.status() != psutil.STATUS_ZOMBIE:
                orphans.append(p.info)
    except Exception:
        pass
assert len(orphans) == 0, f'Orphan processes detected: {orphans}'
print('Zero orphan processes confirmed.')
"
```

---

## 4. Regression Checklist for Releases

Before tagging any release:
- [ ] Run full pytest suite: `pytest tests/` (All 255 tests must pass).
- [ ] Verify clean startup and shutdown: `coresync --test-startup` (Exit code 0).
- [ ] Verify zero orphans via the process check script above.
- [ ] Verify no personal machine paths exist in repository: `grep -rn "/home/" --exclude-dir={.git,.venv,docs} .`.
- [ ] Verify packaging builds successfully on supported platform.

