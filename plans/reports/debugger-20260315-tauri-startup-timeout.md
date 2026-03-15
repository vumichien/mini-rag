# Debugger Report — Tauri Startup Timeout
**Date:** 2026-03-15
**Severity:** Critical (app unusable on launch)

---

## Executive Summary

The "Startup timeout. Please restart the app." message appears because the Python sidecar (`api-server.exe`) never starts — Tauri cannot find the binary under the name it looks for. The sidecar resolves on disk to `api-server-.exe` (empty target triple), but Tauri's shell plugin looks for `api-server-x86_64-pc-windows-msvc.exe` (the platform target triple). The correct full-size binary (`api-server-x86_64-pc-windows-msvc.exe`, 344 KB) is also present but is 344 KB vs the 152 MB real build — indicating it is a stale/wrong binary. The actual PyInstaller output ended up named `api-server-.exe`.

---

## Root Cause Analysis

### Primary Root Cause: `rustc` not on PATH during `backend/build.bat` → empty target triple

`build.bat` line 19:
```bat
for /f "tokens=*" %%i in ('rustc --print host') do set TARGET_TRIPLE=%%i
```

If `rustc` is **not on PATH** when this script runs (e.g. if the shell used by `build-all.bat` doesn't inherit the Rustup environment), `rustc --print host` returns nothing. `TARGET_TRIPLE` stays empty.

Line 31:
```bat
move "%OUTPUT_DIR%\api-server.exe" "%OUTPUT_DIR%\api-server-%TARGET_TRIPLE%.exe"
```

With `TARGET_TRIPLE=""` this becomes:
```bat
move "...\api-server.exe" "...\api-server-.exe"
```

**Evidence from filesystem:**
```
src-tauri/binaries/api-server-.exe          → 152 MB  (the real PyInstaller build, wrong name)
src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe  → 344 KB  (stale/wrong, from prior build attempt)
```

The 152 MB binary is the correct PyInstaller bundle. The 344 KB one is clearly not a PyInstaller bundle (those are ~150-250 MB).

### How Tauri Resolves the Sidecar

`tauri.conf.json` (line 44):
```json
"externalBin": ["binaries/api-server"]
```

At runtime, `tauri-plugin-shell` appends the current platform target triple automatically. On Windows x64 it looks for:
```
binaries/api-server-x86_64-pc-windows-msvc.exe
```

The stale 344 KB file at that name either fails to run (wrong format) or crashes immediately, so port 52547 never opens.

### Secondary Contributing Factor: `is_port_open` check could mask sidecar failure

`src-tauri/src/lib.rs` lines 32–35:
```rust
if is_port_open(52547) {
    println!("[sidecar] backend already running on :52547, skipping sidecar spawn");
    return;
}
```

If something else occupied port 52547 from a prior dev session, the sidecar spawn is skipped entirely. This is unlikely to be the primary cause here but is worth noting.

### Timeout Mechanism (Frontend)

`src/components/LoadingScreen.tsx` lines 16–19:
```tsx
if (secs > 30) {
  setStatus("Startup timeout. Please restart the app.");
  clearInterval(interval);
  return;
}
```

`src/lib/api-client.ts` line 7:
```ts
const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
```

The health poll runs every 500ms with a 2s fetch timeout. After 30 seconds without a `200 OK` from `http://127.0.0.1:52547/health`, the timeout message appears. This is correct behavior — the problem is upstream (sidecar never starts).

---

## Affected Files

| File | Issue |
|------|-------|
| `backend/build.bat:19` | `rustc --print host` fails silently if rustc not on PATH |
| `backend/build.bat:31` | Move with empty triple → `api-server-.exe` |
| `src-tauri/binaries/api-server-.exe` | Correct binary, wrong name (152 MB) |
| `src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe` | Stale/wrong binary (344 KB) |

---

## Recommended Fixes

### Fix 1 (Immediate): Rename the binary manually

Delete the stale file and rename the correct one:
```bat
del "src-tauri\binaries\api-server-x86_64-pc-windows-msvc.exe"
ren "src-tauri\binaries\api-server-.exe" "api-server-x86_64-pc-windows-msvc.exe"
```

Then rebuild Tauri only (no need to re-run PyInstaller):
```bash
npm run tauri build
```

### Fix 2 (Permanent): Harden `build.bat` to detect empty triple

In `backend/build.bat`, after line 19, add a guard:

```bat
for /f "tokens=*" %%i in ('rustc --print host') do set TARGET_TRIPLE=%%i
if "%TARGET_TRIPLE%"=="" (
    echo ERROR: rustc not found or returned empty target triple.
    echo Ensure Rust is installed and rustup is on PATH.
    exit /b 1
)
```

This fails fast instead of silently producing a wrongly-named binary.

### Fix 3 (Belt-and-suspenders): Add sidecar spawn error logging to UI

Currently if `spawn_sidecar` fails (lib.rs line 74), the error goes to stderr only — invisible to the end user. Consider surfacing sidecar spawn failures via a Tauri event or dialog so the user gets an actionable error instead of the generic timeout.

---

## PyInstaller / app.py Notes (no issues found)

- `main.py`: correct — `multiprocessing.freeze_support()` first, `if __name__ == "__main__"` guard, `workers=1` for PyInstaller compatibility.
- `app.py`: correct — `lifespan` initializes `EmbedderService` and `VectorStoreService` on startup.
- `api-server.spec`: correct — `console=True` lets Tauri read stdout; model path `../models/all-MiniLM-L6-v2` bundled as `fastembed_models`.

---

## Unresolved Questions

1. Why does `src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe` exist at only 344 KB? Was it a placeholder committed to git, or output of a failed prior build? If it was in the git history, it should be removed and `.gitignore` updated for `src-tauri/binaries/*.exe`.
2. Does the installed `.exe` (from the NSIS installer) correctly bundle the sidecar? The NSIS installer packages whatever was in `binaries/` at build time — if the stale 344 KB file was used during `npm run tauri build`, the installer is also broken and must be rebuilt after Fix 1.
