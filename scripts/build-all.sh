#!/usr/bin/env bash
# Full build pipeline: Python backend → Tauri bundle → macOS/Linux installer
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "===== Step 1: Build Python backend ====="
bash "$ROOT/backend/build.sh"

echo "===== Step 2: Build Tauri + React ====="
cd "$ROOT"
npm run tauri build

echo "===== Build complete ====="
echo "Bundle: $ROOT/src-tauri/target/release/bundle/"
