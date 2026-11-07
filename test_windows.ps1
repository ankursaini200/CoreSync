# ==============================================================================
# CoreSync Windows 10/11 Automated Test Runner (PowerShell)
# ==============================================================================

Set-Location $PSScriptRoot

$venvPytest = ".venv\Scripts\pytest.exe"
if (-not (Test-Path $venvPytest)) {
    Write-Error "[ERROR] Virtual environment with pytest not found. Please run .\setup_windows.ps1 first."
    exit 1
}

& $venvPytest tests\ @args
exit $LASTEXITCODE

