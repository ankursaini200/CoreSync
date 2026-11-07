#!/usr/bin/env bash
# CoreSync Linux Standalone Packaging Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building CoreSync for Linux ==="
echo "Project Root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# Check Python environment
if [ ! -d ".venv" ]; then
    echo "Virtual environment .venv not found. Please create it first:"
    echo "  python3 -m venv .venv && source .venv/bin/activate"
    exit 1
fi

# Ensure PyInstaller is installed
if ! .venv/bin/python -m pyinstaller --version &>/dev/null; then
    echo "Installing PyInstaller..."
    .venv/bin/pip install pyinstaller
fi

# Clean previous build artifacts
rm -rf build/ dist/

# Run PyInstaller build
echo "Running PyInstaller..."
.venv/bin/pyinstaller --noconfirm coresync.spec

echo "=== Linux Build Complete ==="
echo "Output executable located at: dist/coresync/coresync"
echo "Test execution: ./dist/coresync/coresync --test-startup"

