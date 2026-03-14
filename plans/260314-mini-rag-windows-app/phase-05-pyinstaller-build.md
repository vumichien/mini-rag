# Phase 05: PyInstaller Build Config

**Context:** [plan.md](./plan.md) · [PyInstaller research](./research/researcher-02-pyinstaller-packaging.md)

## Overview

- **Priority:** P1
- **Status:** Pending
- **Effort:** 2h
- **Description:** Create PyInstaller .spec file with all hidden imports, ONNX DLL collection, fastembed model bundling. Build api-server.exe and place it in src-tauri/binaries/.

## Key Insights

- Use `--onefile` (single exe) — easier Tauri sidecar bundling
- `collect_dynamic_libs('onnxruntime')` — critical for ONNX DLLs
- Bundle fastembed model from `models/all-MiniLM-L6-v2/` (pre-downloaded in phase 1)
- Runtime path detection: `sys._MEIPASS` when frozen, local path in dev
- Final binary name MUST have target triple suffix: `api-server-x86_64-pc-windows-msvc.exe`
- Expected binary size: ~250-320MB unoptimized → ~130-180MB with UPX

## Requirements

- Single `api-server.exe` with all deps bundled
- Offline operation (model files + DLLs all inside)
- Place output in `src-tauri/binaries/` with correct naming

## Related Code Files

- Create: `backend/api-server.spec`
- Create: `backend/build.bat`
- Create: `scripts/build-all.bat`

## Implementation Steps

### Step 1: Determine target triple

```bat
rustc --print host
REM Should output: x86_64-pc-windows-msvc
```

Save this — used in naming the output binary.

### Step 2: api-server.spec

```python
# backend/api-server.spec
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os

block_cipher = None

# All hidden imports needed for the stack
hidden_imports = [
    # ChromaDB — dynamic imports
    'chromadb.api.segment',
    'chromadb.api.impl.composite.composite_api',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.segment.impl.vector',
    'chromadb.segment.impl.vector.local_hnsw',
    'chromadb.segment.impl.vector.local_persistent_hnsw',
    'chromadb.segment.impl.vector.brute_force_index',
    'chromadb.segment.impl.vector.hnsw_params',
    'chromadb.segment.impl.vector.batch',
    'chromadb.segment.impl.metadata',
    'chromadb.segment.impl.metadata.sqlite',
    'chromadb.segment.impl.manager',
    'chromadb.segment.impl.manager.local',
    'chromadb.execution.executor.local',
    'chromadb.migrations',
    'chromadb.migrations.embeddings_queue',
    'chromadb.quota.simple_quota_enforcer',
    'chromadb.rate_limit.simple_rate_limit',
    'chromadb.telemetry.product.posthog',

    # ONNX + tokenizers
    'onnxruntime',
    'tokenizers',
    'tqdm',

    # FastAPI stack
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.server',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websocket',
    'uvicorn.protocols.websocket.auto',
    'starlette.applications',
    'starlette.routing',
    'starlette.responses',
    'starlette.middleware',
    'starlette.middleware.cors',
    'h11',

    # PyMuPDF
    'fitz',

    # Windows event loop
    'winloop',

    # App modules
    'app',
    'routes.upload',
    'routes.documents',
    'routes.search',
    'routes.health',
    'services.pdf_parser',
    'services.chunker',
    'services.embedder',
    'services.vector_store',
]

# Data files to bundle
datas = [
    *collect_data_files('chromadb'),
    *collect_data_files('onnxruntime'),
    *collect_data_files('tokenizers'),
    *collect_data_files('fastapi'),
    *collect_data_files('starlette'),
    # Bundle pre-downloaded fastembed model
    ('../models/all-MiniLM-L6-v2', 'fastembed_models'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        *collect_dynamic_libs('onnxruntime'),
    ],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PIL', 'cv2',
        'notebook', 'IPython', 'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='api-server-x86_64-pc-windows-msvc',  # MUST match Tauri target triple
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Don't strip on Windows (breaks things)
    upx=True,    # UPX compression — reduces size ~40%
    upx_exclude=['vcruntime140.dll', 'msvcp140.dll'],  # Don't compress VC runtime
    runtime_tmpdir=None,
    console=True,  # Keep console for logging (Tauri reads stdout)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Important:** If target triple differs from `x86_64-pc-windows-msvc`, update the `name` field.

### Step 3: build.bat

```bat
@echo off
REM backend/build.bat
REM Build PyInstaller sidecar and copy to src-tauri/binaries/

SET SCRIPT_DIR=%~dp0
SET PROJECT_ROOT=%SCRIPT_DIR%..
SET BINARIES_DIR=%PROJECT_ROOT%\src-tauri\binaries

echo [1/4] Activating Python venv...
call %SCRIPT_DIR%.venv\Scripts\activate.bat

echo [2/4] Building PyInstaller binary...
cd %SCRIPT_DIR%
pyinstaller api-server.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo [3/4] Copying binary to src-tauri/binaries/...
if not exist "%BINARIES_DIR%" mkdir "%BINARIES_DIR%"
copy /Y "%SCRIPT_DIR%dist\api-server-x86_64-pc-windows-msvc.exe" "%BINARIES_DIR%\"

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to copy binary
    exit /b 1
)

echo [4/4] Done! Binary at: %BINARIES_DIR%\api-server-x86_64-pc-windows-msvc.exe
dir "%BINARIES_DIR%\api-server-x86_64-pc-windows-msvc.exe"
```

### Step 4: scripts/build-all.bat (full pipeline)

```bat
@echo off
REM scripts/build-all.bat
REM Full build pipeline: Python sidecar → Tauri installer

SET PROJECT_ROOT=%~dp0..

echo ============================================
echo  Mini RAG Full Build Pipeline
echo ============================================

echo.
echo [Step 1] Building Python sidecar...
call %PROJECT_ROOT%\backend\build.bat
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo [Step 2] Building Tauri installer...
cd %PROJECT_ROOT%
call npm run tauri build
if %ERRORLEVEL% NEQ 0 exit /b 1

echo.
echo ============================================
echo  Build complete!
echo  Installer: src-tauri\target\release\bundle\nsis\
echo ============================================
```

### Step 5: Test the binary

```bat
REM Test without Tauri first
cd backend
dist\api-server-x86_64-pc-windows-msvc.exe --data-dir "C:\Temp\mini-rag-test" --port 52547

REM In another terminal:
curl http://127.0.0.1:52547/health
REM Expected: {"status":"ok"}
```

### Step 6: Debug common issues

If binary fails at runtime:
```bat
REM Run with debug output
dist\api-server-x86_64-pc-windows-msvc.exe 2>&1 | findstr /i "error module not found"

REM Re-build with debug imports visible
pyinstaller api-server.spec --debug=imports 2>&1 | findstr /i "hidden"
```

## Todo List

- [ ] Run `rustc --print host` and confirm target triple
- [ ] Create `backend/api-server.spec` with all hidden imports
- [ ] Verify `models/all-MiniLM-L6-v2/` has model files (from phase 1)
- [ ] Create `backend/build.bat`
- [ ] Create `scripts/build-all.bat`
- [ ] Run `build.bat` and verify no errors
- [ ] Test standalone binary: `--data-dir` + `GET /health`
- [ ] Test standalone binary: upload PDF + search
- [ ] Confirm binary exists in `src-tauri/binaries/`
- [ ] Check binary size (expect ~200-320MB)

## Success Criteria

- `api-server-x86_64-pc-windows-msvc.exe` exists in `src-tauri/binaries/`
- Standalone binary: `GET /health` → 200 OK
- Standalone binary: upload PDF, GET /documents shows it, POST /search returns 5 results
- Binary is fully offline (no network access after start)

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Missing ChromaDB hidden import | Run with `--debug=imports`, add to list |
| ONNX DLL not found | Verify `collect_dynamic_libs('onnxruntime')` in binaries |
| fastembed model not found | Check `sys._MEIPASS` path + `datas` in spec |
| UPX breaks DLLs | Exclude ONNX/VC runtime DLLs from UPX compression |
| Build fails with 'models not found' | Ensure `models/all-MiniLM-L6-v2/` exists |

## Security Considerations

- No secrets bundled in binary
- Model files are open-source ONNX weights

## Next Steps

→ Phase 6: Tauri bundler config + installer
