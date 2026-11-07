@echo off
REM CoreSync Windows Standalone Packaging Script (PyInstaller)
REM NOTE: Must be run on a Windows host machine with Python 3.11+ installed.
setlocal enabledelayedexpansion

echo === Building CoreSync for Windows ===
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv not found.
    echo Please run: python -m venv .venv ^&^& .venv\Scripts\pip install -e .[build]
    exit /b 1
)

echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

echo Running PyInstaller...
.venv\Scripts\pyinstaller.exe --noconfirm coresync.spec

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    exit /b %errorlevel%
)

echo === Windows Build Complete ===
echo Output executable located at: dist\coresync\coresync.exe
echo Test execution: dist\coresync\coresync.exe --test-startup

