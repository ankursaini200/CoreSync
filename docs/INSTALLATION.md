# CoreSync Installation & Setup Guide

This guide details instructions for installing, configuring, and launching CoreSync across **Linux**, **Microsoft Windows**, and **Apple macOS**.

---

## 1. System Requirements

### Supported Operating Systems
- **Linux**: Kernel 5.4+ (Ubuntu 22.04+, Arch Linux, Fedora 38+, Debian 12+)
- **Windows**: Windows 10 (Build 19041+) or Windows 11 (64-bit x86_64)
- **macOS**: macOS 12 (Monterey), 13 (Ventura), 14 (Sonoma), or 15 (Sequoia) (Intel x86_64 or Apple Silicon arm64)

### Software Prerequisites
- **Python**: Version 3.11, 3.12, 3.13, or 3.14 (64-bit required)
- **Graphics / Display**:
  - Linux: Wayland or X11 server (or offscreen mode for headless servers/CI)
  - Windows: Desktop display session
  - macOS: Quartz display session

---

## 2. Linux Installation

### Step 1: Install System Dependencies
On Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv libxcb1 libxkbcommon-x11-0
```

On Arch Linux:
```bash
sudo pacman -S python python-pip
```

On Fedora:
```bash
sudo dnf install -y python3 python3-pip python3-virtualenv
```

### Step 2: Clone the Repository
```bash
git clone https://github.com/academicos/coresync.git
cd coresync
```

### Step 3: Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install Dependencies & CoreSync
```bash
pip install --upgrade pip
pip install -e .
```

To install development dependencies (testing and building):
```bash
pip install -e .[dev,build]
```

### Step 5: Launch the Application
```bash
coresync
```
Or directly via Python:
```bash
python main.py
```

---

## 3. Microsoft Windows Installation (Windows 10 / 11)

### Option A: Automated One-Click Setup (Recommended)

1. Open **Command Prompt (`cmd.exe`)** or **PowerShell** as your regular user.
2. Clone the repository and navigate into it:
   ```cmd
   git clone https://github.com/academicos/coresync.git
   cd coresync
   ```
3. Run the automated setup script:
   - In Command Prompt:
     ```cmd
     setup_windows.bat
     ```
   - In PowerShell:
     ```powershell
     .\setup_windows.ps1
     ```
   *This script automatically verifies Python 3.11+, provisions the `.venv` virtual environment, installs CoreSync in editable mode with development/packaging tools, and executes `utils\check_deps.py`.*

4. Launch the application:
   - In Command Prompt:
     ```cmd
     run_windows.bat
     ```
   - In PowerShell:
     ```powershell
     .\run_windows.ps1
     ```

5. Run the automated test suite:
   ```cmd
   test_windows.bat
   REM Or PowerShell: .\test_windows.ps1
   ```

### Option B: Manual Setup

#### Step 1: Install Python
Download and install Python 3.11+ from [python.org](https://www.python.org/downloads/).
> [!IMPORTANT]
> Ensure you check the box **"Add python.exe to PATH"** during installation.

#### Step 2: Create and Activate Virtual Environment
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```
*(In PowerShell: `Set-ExecutionPolicy -Scope Process RemoteSigned` then `.venv\Scripts\Activate.ps1`)*

#### Step 3: Install CoreSync
```cmd
python -m pip install --upgrade pip setuptools wheel
pip install -e .[dev,build]
```

#### Step 4: Verify Installation
```cmd
python utils\check_deps.py
```

#### Step 5: Launch CoreSync
```cmd
python main.py
```

---

## 4. Apple macOS Installation

### Step 1: Install Python
Using [Homebrew](https://brew.sh/):
```bash
brew install python@3.12
```

### Step 2: Clone the Repository
```bash
git clone https://github.com/academicos/coresync.git
cd coresync
```

### Step 3: Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install CoreSync
```bash
pip install --upgrade pip
pip install -e .
```

### Step 5: Launch the Application
```bash
coresync
```
Or:
```bash
python main.py
```

---

## 5. Headless / Continuous Integration (CI) Setup

CoreSync supports fully headless execution for automated test pipelines, server environments, and CI runners:

```bash
export QT_QPA_PLATFORM=offscreen
pytest tests/
```

Verify startup in headless mode:
```bash
coresync --test-startup
```
This launches the application, renders the workstation offscreen, verifies initialization, and exits automatically after 1000ms with exit code 0.

---

## 6. Troubleshooting Common Issues

### Issue 1: `Could not load the Qt platform plugin "wayland"`
**Cause**: Linux display environment missing Wayland plugin libraries.  
**Resolution**: CoreSync automatically detects invalid Wayland sockets and falls back to offscreen or X11. To force X11 mode:
```bash
QT_QPA_PLATFORM=xcb coresync
```

### Issue 2: `PermissionError: [Errno 1] Operation not permitted` on CPU Affinity
**Cause**: Restrictive Linux cgroup, container sandbox, or unprivileged user permissions.  
**Resolution**: CoreSync's `AffinityManager` detects restricted affinity permissions and gracefully falls back to unpinned execution across all available logical cores without crashing.

### Issue 3: `ModuleNotFoundError: No module named 'PySide6'`
**Cause**: Virtual environment not activated.  
**Resolution**: Activate your virtual environment (`source .venv/bin/activate` or `.venv\Scripts\activate`) before launching.

