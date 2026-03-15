#!/usr/bin/env bash
# Build Python backend into standalone binary using PyInstaller (macOS/Linux)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV="$SCRIPT_DIR/.venv"
OUTPUT_DIR="$SCRIPT_DIR/../src-tauri/binaries"

if [ ! -f "$VENV/bin/activate" ]; then
    echo "ERROR: venv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# Get target triple for binary naming
TARGET_TRIPLE=$(rustc --print host-tuple 2>/dev/null || true)
if [ -z "$TARGET_TRIPLE" ]; then
    echo "ERROR: rustc not found or returned empty target triple."
    echo "Ensure Rust is installed and rustup is on PATH before running this script."
    exit 1
fi
echo "Building for target: $TARGET_TRIPLE"

pyinstaller api-server.spec --distpath "$OUTPUT_DIR" --clean

# Kill any running sidecar so the file is not locked during rename
pkill -f "api-server-$TARGET_TRIPLE" 2>/dev/null || true
pkill -f "api-server" 2>/dev/null || true

# Delete existing target
if [ -f "$OUTPUT_DIR/api-server-$TARGET_TRIPLE" ]; then
    rm -f "$OUTPUT_DIR/api-server-$TARGET_TRIPLE"
fi

# Rename to include target triple
if [ -f "$OUTPUT_DIR/api-server" ]; then
    mv "$OUTPUT_DIR/api-server" "$OUTPUT_DIR/api-server-$TARGET_TRIPLE"
    echo "Binary: $OUTPUT_DIR/api-server-$TARGET_TRIPLE"
fi

echo "Build complete!"
