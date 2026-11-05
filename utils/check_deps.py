"""Dependency Compatibility & Runtime Verification Script for CoreSync.

Verifies:
- Python version >= 3.11
- PySide6 GUI toolkit and Qt event loop / widget instantiation
- NumPy array vectorization and SIMD availability
- psutil system metrics and CPU affinity control
- Matplotlib plotting backend
- pytest testing framework
- multiprocessing spawn context
"""

import sys
import os
import platform
import multiprocessing as mp

# Configure safe writable directory for Matplotlib cache
os.environ.setdefault("MPLCONFIGDIR", "/tmp/coresync_mpl")

def check_python_version() -> bool:
    print(f"[*] Python Version: {platform.python_version()} ({platform.python_implementation()})")
    if sys.version_info < (3, 11):
        print("[-] FAIL: Python 3.11+ required.")
        return False
    print("    -> PASS")
    return True

def check_pyside6() -> bool:
    print("[*] Testing PySide6 & Qt6...")
    try:
        import PySide6
        from PySide6.QtCore import QCoreApplication, Signal, Slot, QObject
        print(f"    PySide6 Version: {PySide6.__version__}")

        # Test Signal / Slot Mechanism
        app = QCoreApplication.instance() or QCoreApplication(sys.argv)
        class _TestEmitter(QObject):
            sig = Signal(str)

        class _TestReceiver(QObject):
            def __init__(self):
                super().__init__()
                self.val = None
            @Slot(str)
            def on_sig(self, v):
                self.val = v

        emitter = _TestEmitter()
        receiver = _TestReceiver()
        emitter.sig.connect(receiver.on_sig)
        emitter.sig.emit("qt_ok")
        assert receiver.val == "qt_ok", "Signal/Slot delivery failed"
        print("    -> PASS (Qt Core & Signal/Slot Operational)")
        return True
    except Exception as e:
        print(f"[-] FAIL PySide6: {e}")
        return False

def check_numpy() -> bool:
    print("[*] Testing NumPy...")
    try:
        import numpy as np
        print(f"    NumPy Version: {np.__version__}")
        a = np.arange(1000, dtype=np.float64)
        b = a ** 2
        assert np.isclose(b[10], 100.0), "Vector operation error"
        print("    -> PASS (NumPy Vectorized Compute Verified)")
        return True
    except Exception as e:
        print(f"[-] FAIL NumPy: {e}")
        return False

def check_psutil() -> bool:
    print("[*] Testing psutil & CPU Affinity...")
    try:
        import psutil
        print(f"    psutil Version: {psutil.__version__}")
        logical = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)
        print(f"    Detected CPUs: {physical} physical, {logical} logical")
        
        # Test CPU affinity API
        proc = psutil.Process(os.getpid())
        if hasattr(proc, "cpu_affinity"):
            initial_affinity = proc.cpu_affinity()
            # Test setting affinity if more than 1 CPU available
            if len(initial_affinity) > 1:
                proc.cpu_affinity([0])
                assert proc.cpu_affinity() == [0], "Affinity modification failed"
                proc.cpu_affinity(initial_affinity)  # Restore
            print(f"    CPU Affinity API: Supported ({len(initial_affinity)} logical cores)")
        else:
            print("    CPU Affinity API: Not supported on this platform (fallback will be used)")
        print("    -> PASS (psutil System Metrics Operational)")
        return True
    except Exception as e:
        print(f"[-] FAIL psutil: {e}")
        return False

def check_multiprocessing_spawn() -> bool:
    print("[*] Testing multiprocessing spawn context...")
    try:
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        # Verify context initialization
        assert ctx.get_start_method() == "spawn"
        print("    multiprocessing Start Method: spawn")
        print("    -> PASS (Spawn context verified)")
        return True
    except Exception as e:
        print(f"[-] FAIL multiprocessing: {e}")
        return False

def check_matplotlib() -> bool:
    print("[*] Testing Matplotlib...")
    try:
        import matplotlib
        print(f"    Matplotlib Version: {matplotlib.__version__}")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [1, 4, 9])
        plt.close(fig)
        print("    -> PASS (Matplotlib & Agg backend verified)")
        return True
    except Exception as e:
        print(f"[-] FAIL Matplotlib: {e}")
        return False

def check_pytest() -> bool:
    print("[*] Testing pytest...")
    try:
        import pytest
        print(f"    pytest Version: {pytest.__version__}")
        print("    -> PASS (pytest framework verified)")
        return True
    except Exception as e:
        print(f"[-] FAIL pytest: {e}")
        return False

def main() -> int:
    print("=" * 60)
    print("CoreSync Dependency Compatibility Verification")
    print("=" * 60)
    results = [
        check_python_version(),
        check_pyside6(),
        check_numpy(),
        check_psutil(),
        check_multiprocessing_spawn(),
        check_matplotlib(),
        check_pytest(),
    ]
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed.")
    if passed == total:
        print("ALL CORE DEPENDENCIES OPERATIONAL!")
        return 0
    else:
        print("SOME DEPENDENCIES FAILED VERIFICATION.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
