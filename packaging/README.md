# CoreSync Packaging & Distribution Guide

This directory contains standalone packaging recipes for building standalone binary distributions of CoreSync using [PyInstaller](https://pyinstaller.org/).

---

## 1. Verification Matrix

| Platform | Packaging Method | Target Format | Verification Status | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Linux (x86_64)** | PyInstaller Spec | Directory / Binary (`dist/coresync/coresync`) | **VERIFIED ON HOST** | Tested on Arch Linux (Kernel 7.2.14, x86_64). |
| **Windows 10/11** | PyInstaller Spec | Executable (`dist\coresync\coresync.exe`) | **RECIPE PREPARED (Unverified)** | Native Windows build must be executed on a Windows runner or machine. |
| **macOS (Darwin)** | PyInstaller Spec | App Bundle (`dist/CoreSync.app`) | **RECIPE PREPARED (Unverified)** | Native macOS build must be executed on a macOS runner or machine. |

> [!WARNING]
> PyInstaller does not support cross-compiling binaries for different operating systems (e.g., building a Windows `.exe` from a Linux host). Each platform package must be built on its native OS or using a dedicated GitHub Actions CI runner.

---

## 2. Linux Standalone Build

### Prerequisites
- Python 3.11, 3.12, 3.13, or 3.14
- Standard Linux toolchain (gcc, binutils)
- Virtual environment with dependencies installed:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .[build]
  ```

### Build Command
```bash
./packaging/build_linux.sh
```

### Verification
```bash
./dist/coresync/coresync --test-startup
```

---

## 3. Windows Standalone Build

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.11+
- Visual C++ Redistributable (normally pre-installed)
- Setup commands:
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  pip install -e .[build]
  ```

### Build Command
In Command Prompt:
```cmd
packaging\build_windows.bat
```
Or in PowerShell:
```powershell
.\packaging\build_windows.ps1
```

### Verification
```cmd
dist\coresync\coresync.exe --test-startup
```

---

## 4. macOS Standalone Build

### Prerequisites
- macOS 12 (Monterey) or newer (Intel x86_64 or Apple Silicon arm64)
- Python 3.11+ installed via python.org or Homebrew
- Setup commands:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e .[build]
  ```

### Build Command
```bash
./packaging/build_macos.sh
```

### Verification
```bash
open dist/CoreSync.app --args --test-startup
```

