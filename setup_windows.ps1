# ==============================================================================
# CoreSync Windows 10/11 Automated Environment Setup Script (PowerShell)
# ==============================================================================

Write-Host "[CoreSync] Initializing Windows Setup (PowerShell)..." -ForegroundColor Cyan

Set-Location $PSScriptRoot

# 1. Detect Python
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCmd = "py -3"
}

if (-not $pythonCmd) {
    Write-Error "[ERROR] Python 3.11+ was not detected in PATH. Please install Python 3.11+ from https://www.python.org/"
    exit 1
}

$pyVer = & ($pythonCmd.Split()[0]) @($pythonCmd.Split()[1..($pythonCmd.Split().Length - 1)]) --version
Write-Host "[CoreSync] Detected Python: $pyVer" -ForegroundColor Green

# 2. Create virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[CoreSync] Creating virtual environment in .venv..." -ForegroundColor Cyan
    & ($pythonCmd.Split()[0]) @($pythonCmd.Split()[1..($pythonCmd.Split().Length - 1)]) -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[ERROR] Failed to create virtual environment."
        exit $LASTEXITCODE
    }
} else {
    Write-Host "[CoreSync] Existing virtual environment found in .venv." -ForegroundColor Green
}

# 3. Upgrade pip and build tools
$venvPython = ".venv\Scripts\python.exe"
$venvPip = ".venv\Scripts\pip.exe"

Write-Host "[CoreSync] Upgrading pip, setuptools, and wheel..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip setuptools wheel --quiet

# 4. Install dependencies
Write-Host "[CoreSync] Installing CoreSync package and dependencies..." -ForegroundColor Cyan
& $venvPip install -e .[dev,build]
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[WARNING] Optional extras install failed, falling back to base requirements..."
    if (Test-Path "requirements.txt") { & $venvPip install -r requirements.txt }
    if (Test-Path "requirements-dev.txt") { & $venvPip install -r requirements-dev.txt }
    & $venvPip install -e . --no-deps
}

# 5. Verify dependencies
Write-Host "[CoreSync] Verifying environment dependencies..." -ForegroundColor Cyan
& $venvPython utils\check_deps.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "==============================================================================" -ForegroundColor Green
    Write-Host "[CoreSync] Windows Setup Completed Successfully!" -ForegroundColor Green
    Write-Host "To launch the application: .\run_windows.ps1" -ForegroundColor Yellow
    Write-Host "To run tests:             .\test_windows.ps1" -ForegroundColor Yellow
    Write-Host "==============================================================================" -ForegroundColor Green
} else {
    Write-Warning "[WARNING] Some dependency checks failed. Please check the logs above."
}

