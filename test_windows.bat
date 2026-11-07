@echo off
REM ==============================================================================
REM CoreSync Windows 10/11 Automated Test Runner
REM ==============================================================================
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\pytest.exe" (
    echo [ERROR] Virtual environment with pytest not found. Please run setup_windows.bat first.
    exit /b 1
)

.venv\Scripts\pytest.exe tests\ %*
exit /b %errorlevel%

