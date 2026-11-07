# ==============================================================================
# CoreSync Windows Standalone Packaging Script (PyInstaller - PowerShell)
# ==============================================================================

Write-Host "=== Building CoreSync Standalone Executable for Windows ===" -ForegroundColor Cyan

Set-Location "$PSScriptRoot\.."

$venvPyinstaller = ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $venvPyinstaller)) {
    Write-Error "[ERROR] PyInstaller not found in .venv. Run: .venv\Scripts\pip install pyinstaller"
    exit 1
}

Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "Executing PyInstaller with coresync.spec..." -ForegroundColor Cyan
& $venvPyinstaller --noconfirm coresync.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host "=== Windows Build Complete ===" -ForegroundColor Green
    Write-Host "Executable: dist\coresync\coresync.exe" -ForegroundColor Green
    Write-Host "Verify startup: .\dist\coresync\coresync.exe --test-startup" -ForegroundColor Yellow
} else {
    Write-Error "[ERROR] PyInstaller compilation failed with code $LASTEXITCODE."
    exit $LASTEXITCODE
}

