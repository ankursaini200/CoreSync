# ==============================================================================
# CoreSync Windows 10/11 Launcher (PowerShell)
# ==============================================================================

Set-Location $PSScriptRoot

$venvPython = ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "[ERROR] Virtual environment not found. Please run .\setup_windows.ps1 first."
    exit 1
}

& $venvPython main.py @args
exit $LASTEXITCODE

