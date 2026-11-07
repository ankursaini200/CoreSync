#!/usr/bin/env bash
# CoreSync macOS Standalone Application Bundle Script
# NOTE: Must be run on a macOS host machine with Python 3.11+ installed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Building CoreSync for macOS ==="
echo "Project Root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    echo "[ERROR] Virtual environment .venv not found."
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -e .[build]"
    exit 1
fi

rm -rf build/ dist/

echo "Running PyInstaller..."
.venv/bin/pyinstaller --noconfirm coresync.spec

echo "=== macOS Build Complete ==="
echo "Output application bundle: dist/CoreSync.app"
echo "Test execution: open dist/CoreSync.app --args --test-startup"

