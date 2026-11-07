@echo off
REM ==============================================================================
REM CoreSync Windows 10/11 Launcher
REM ==============================================================================
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup_windows.bat first.
    exit /b 1
)

.venv\Scripts\python.exe main.py %*
exit /b %errorlevel%

