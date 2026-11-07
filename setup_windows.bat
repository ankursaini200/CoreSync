@echo off
REM ==============================================================================
REM CoreSync Windows 10/11 Automated Environment Setup Script
REM ==============================================================================
setlocal enabledelayedexpansion

echo [CoreSync] Initializing Windows Setup...
cd /d "%~dp0"

REM 1. Check for Python executable (try python, then py -3)
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
) else (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py -3
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.11+ was not detected in PATH.
    echo Please install Python 3.11 or newer from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set PY_VER=%%v
echo [CoreSync] Detected Python version: !PY_VER!

REM 2. Create virtual environment if not present
if not exist ".venv\Scripts\python.exe" (
    echo [CoreSync] Creating Python virtual environment in .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment in .venv.
        exit /b 1
    )
    echo [CoreSync] Virtual environment created successfully.
) else (
    echo [CoreSync] Existing virtual environment found in .venv.
)

REM 3. Activate virtual environment
call .venv\Scripts\activate.bat

REM 4. Upgrade pip and build tools
echo [CoreSync] Upgrading pip, setuptools, and wheel...
python -m pip install --upgrade pip setuptools wheel --quiet

REM 5. Install CoreSync dependencies in editable mode
echo [CoreSync] Installing CoreSync package and dependencies...
pip install -e .[dev,build]
if errorlevel 1 (
    echo [WARNING] Optional extras install failed, falling back to base requirements...
    if exist "requirements.txt" pip install -r requirements.txt
    if exist "requirements-dev.txt" pip install -r requirements-dev.txt
    pip install -e . --no-deps
)

REM 6. Verify installation via check_deps.py
echo [CoreSync] Verifying environment dependencies...
python utils\check_deps.py
if errorlevel 1 (
    echo [WARNING] Some dependency checks failed. Please check the logs above.
) else (
    echo ==============================================================================
    echo [CoreSync] Windows Setup Completed Successfully!
    echo.
    echo To launch the application:
    echo   run_windows.bat
    echo.
    echo To execute the automated test suite:
    echo   test_windows.bat
    echo ==============================================================================
)

