---
title: PyInstaller Packaging Research - ChromaDB + FastEmbed + FastAPI Stack
date: 2026-03-14
scope: Windows executable packaging for mini-rag
---

# PyInstaller Packaging Research: Mini-RAG Windows Stack

## Executive Summary

Packaging Python apps with ChromaDB (embedded) + fastembed (ONNX) + PyMuPDF + FastAPI + Uvicorn on Windows via PyInstaller requires careful handling of hidden imports, dynamic binaries (ONNX Runtime DLLs), model files, and multiprocessing setup. This report synthesizes findings from authoritative sources and real-world implementations.

**Critical Success Factors:**
- Comprehensive `hiddenimports` list (40+ modules for full ChromaDB)
- Explicit ONNX Runtime DLL collection via `collect_dynamic_libs()`
- Model file bundling for fastembed (all-MiniLM-L6-v2)
- `multiprocessing.freeze_support()` in main entry point
- Runtime hooks for path resolution
- Expected binary size: 250-350MB (unoptimized)

---

## 1. ChromaDB Hidden Imports & Collection

### Complete Hidden Imports List

**Critical for Functionality:**
```python
hiddenimports = [
    # Core API & segment management
    'chromadb.api.segment',
    'chromadb.api.impl.composite.composite_api',

    # Database implementations
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',

    # Vector segment implementations
    'chromadb.segment.impl.vector',
    'chromadb.segment.impl.vector.local_hnsw',
    'chromadb.segment.impl.vector.local_persistent_hnsw',
    'chromadb.segment.impl.vector.brute_force_index',
    'chromadb.segment.impl.vector.hnsw_params',
    'chromadb.segment.impl.vector.batch',

    # Metadata segment implementations
    'chromadb.segment.impl.metadata',
    'chromadb.segment.impl.metadata.sqlite',

    # Manager & execution layer
    'chromadb.segment.impl.manager',
    'chromadb.segment.impl.manager.local',
    'chromadb.execution.executor.local',

    # Migrations
    'chromadb.migrations',
    'chromadb.migrations.embeddings_queue',

    # Quota & rate limiting
    'chromadb.quota.simple_quota_enforcer',
    'chromadb.rate_limit.simple_rate_limit',

    # Telemetry (often dynamic)
    'chromadb.telemetry.product.posthog',

    # Common dependencies
    'onnxruntime',
    'tokenizers',
    'tqdm',
    'google.generativeai',  # if using embedding functions
]
```

### Data Files Collection

**In .spec file:**
```python
from PyInstaller.utils.hooks import collect_data_files

datas = [
    (collect_data_files('chromadb'), 'chromadb'),
    (collect_data_files('tokenizers'), 'tokenizers'),
    (collect_data_files('onnxruntime'), 'onnxruntime'),
]
```

### Best Practices

**`--collect-all` vs. explicit lists:**
- `--collect-all chromadb` bundles everything (safer but larger) ~+50MB
- Explicit lists provide control but risk missing modules
- **Recommendation:** Use explicit lists + runtime hooks for debugging

**Source:** [ChromaDB PyInstaller issue #4092](https://github.com/chroma-core/chroma/issues/4092), [PyInstaller Hooks documentation](https://pyinstaller.org/en/stable/hooks.html)

---

## 2. FastEmbed (ONNX Runtime) Packaging

### ONNX Runtime DLL Issues on Windows

**Known Problem:**
PyInstaller-packaged apps fail with `onnxruntime_pybind11_state` import errors due to missing DLLs: `onnxruntime.dll`, `onnxruntime_providers_shared.dll`, and provider-specific DLLs (CUDA, TensorRT, etc. if applicable).

**Root Cause:**
ONNX Runtime uses compiled C++ extensions. PyInstaller's static analysis misses dynamic DLL loading.

### Solution: Custom DLL Collection

**Spec file approach:**
```python
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Collect ONNX Runtime binaries + data
binaries = [
    *collect_dynamic_libs('onnxruntime'),
]

datas = [
    (collect_data_files('onnxruntime'), 'onnxruntime'),
]
```

**Alternative: Runtime hook**
Create `runtime-hook-onnx.py`:
```python
import sys
import os
from onnxruntime import __file__ as ort_path

# Ensure ONNX Runtime can find its DLLs
sys.path.insert(0, os.path.dirname(ort_path))
```

Add to PyInstaller command:
```bash
--runtime-hook=runtime-hook-onnx.py
```

### Model Files Bundling: all-MiniLM-L6-v2

**Key Files Required:**
- `model.onnx` (~33MB)
- `tokenizer.json` (~200KB)
- `vocab.txt` (~110KB)
- `config.json`

**Setup in code:**
```python
import os
from pathlib import Path

# For PyInstaller bundled app
if getattr(sys, 'frozen', False):
    model_cache = os.path.join(sys._MEIPASS, 'fastembed_models')
else:
    model_cache = Path.home() / '.cache' / 'fastembed_models'

embedding_model = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_dir=str(model_cache),
    local_files_only=True  # Prevent network calls
)
```

**Bundle in spec file:**
```python
import shutil
from pathlib import Path

# Pre-download model or include from your repo
model_src = Path("models/all-MiniLM-L6-v2")
datas += [(str(model_src), 'fastembed_models')]
```

**Estimated Size:**
- Model files: ~35MB
- ONNX Runtime package: ~50-70MB
- Total fastembed footprint: ~100MB

**Source:** [FastEmbed GitHub #229](https://github.com/qdrant/fastembed/issues/229), [ONNX Runtime DLL issue #25193](https://github.com/microsoft/onnxruntime/issues/25193), [PyPI fastembed](https://pypi.org/project/fastembed/)

---

## 3. FastAPI + Uvicorn on Windows

### Critical: Multiprocessing Setup

**Windows-specific requirement:**
```python
# main.py - MUST be at top level before any async code
import multiprocessing
multiprocessing.freeze_support()  # Required for PyInstaller on Windows

import uvicorn
from fastapi import FastAPI

app = FastAPI()

if __name__ == '__main__':
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for bundled apps (spawn-based on Windows)
        reload=False  # Disable reload in production bundled app
    )
```

**Why `workers=1`:**
- Windows uses `spawn` (full process restart), not `fork`
- Multiple workers with PyInstaller can spawn uncontrollable subprocess chains
- If you need concurrency, use `workers=1` + async tasks, not `workers>1`

### uvloop / Winloop Consideration

**Status:**
- `uvloop` is **not compatible with Windows**
- Standard FastAPI extras include uvloop
- Windows needs `winloop` (Windows-compatible fork)

**Action:**
```bash
# In requirements.txt or setup.py
# Remove: uvloop
# Add: winloop; sys_platform == 'win32'
```

**In code:**
```python
import sys
if sys.platform == 'win32':
    import winloop
    asyncio.set_event_loop_policy(winloop.WindowsSelectorEventLoopPolicy())
```

### Hidden Imports for FastAPI Stack

```python
hiddenimports += [
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
    'h11',  # HTTP/1.1 protocol
]
```

**Source:** [PyInstaller FastAPI examples](https://github.com/iancleary/pyinstaller-fastapi), [Uvicorn discussions #1820](https://github.com/Kludex/uvicorn/discussions/1820), [Winloop PyPI](https://pypi.org/project/winloop/)

---

## 4. PyMuPDF (fitz) Packaging

### Hidden Import

```python
hiddenimports += [
    'fitz',  # or 'pymupdf' depending on import style
]
```

**Note:** fitz is the internal module name; pymupdf is the package name.

### Data Files (if needed)

Most PyMuPDF functionality is in compiled binaries. Only add data if custom fonts are used:

```python
datas += [
    # Only if using custom fonts
    # ('path/to/fonts', 'pymupdf/fonts'),
]
```

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'fitz'` at runtime
- **Fix:** Ensure hidden import is correctly listed
- **Verify:** `--debug=imports` flag shows fitz being analyzed

**Source:** [PyMuPDF PyInstaller issue #712](https://github.com/pymupdf/PyMuPDF/issues/712), [PyInstaller spec file docs](https://pyinstaller.org/en/stable/spec-files.html)

---

## 5. Complete Recommended .spec File

### Basic Template

```python
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
import os
import sys

block_cipher = None

a = Analysis(
    ['main.py'],  # Your entry point
    pathex=[],
    binaries=[
        *collect_dynamic_libs('onnxruntime'),
    ],
    datas=[
        *collect_data_files('chromadb'),
        *collect_data_files('onnxruntime'),
        *collect_data_files('tokenizers'),
        *collect_data_files('fastapi'),
        *collect_data_files('starlette'),
        ('models/all-MiniLM-L6-v2', 'fastembed_models'),  # Pre-downloaded model
    ],
    hiddenimports=[
        # ChromaDB
        'chromadb.api.segment',
        'chromadb.db.impl',
        'chromadb.db.impl.sqlite',
        'chromadb.segment.impl.vector',
        'chromadb.segment.impl.vector.local_hnsw',
        'chromadb.segment.impl.vector.local_persistent_hnsw',
        'chromadb.segment.impl.vector.brute_force_index',
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

        # Dependencies
        'onnxruntime',
        'tokenizers',
        'tqdm',

        # FastAPI stack
        'fastapi',
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.server',
        'uvicorn.protocols.http.h11_impl',
        'starlette.applications',
        'starlette.routing',
        'h11',

        # PyMuPDF
        'fitz',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='mini-rag',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # Remove debug symbols
    upx=True,  # Enable UPX compression (Windows only)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set False for GUI apps (hides console)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### PyInstaller Command Equivalent

```bash
pyinstaller \
  --onefile \
  --console \
  --windowed=false \
  --collect-all chromadb \
  --collect-all onnxruntime \
  --collect-all tokenizers \
  --collect-all fastapi \
  --collect-all starlette \
  --hidden-import=fitz \
  --hidden-import=uvicorn.protocols.http.h11_impl \
  --add-data "models/all-MiniLM-L6-v2:fastembed_models" \
  --strip \
  --upx \
  main.py
```

---

## 6. Known Issues & Runtime Fixes

### Issue 1: ModuleNotFoundError at Runtime

**Symptom:**
```
ModuleNotFoundError: No module named 'chromadb.segment.impl.vector.local_hnsw'
```

**Root Cause:** Missing hidden import due to dynamic imports in ChromaDB.

**Fixes (in order):**
1. Add missing module to `hiddenimports`
2. Use `--debug=imports` flag to see what PyInstaller analyzes
3. Create runtime hook (`--runtime-hook=debug.py`) to log imports

**Debug Runtime Hook:**
```python
# runtime-hook-debug.py
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug(f"sys.path: {sys.path}")
logger.debug(f"Frozen: {getattr(sys, 'frozen', False)}")
```

### Issue 2: FileNotFoundError for ONNX DLLs

**Symptom:**
```
FileNotFoundError: Could not find module 'onnxruntime.dll' (or one of its dependencies)
```

**Root Cause:** ONNX Runtime DLLs not in bundle or path misconfiguration.

**Fixes:**
1. Verify `collect_dynamic_libs('onnxruntime')` in binaries
2. Check build output for DLL files in dist folder
3. Add to PATH in runtime hook (fallback):
```python
# runtime-hook-onnx.py
import sys, os
ort_dll_dir = os.path.join(sys._MEIPASS, 'onnxruntime')
if ort_dll_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = ort_dll_dir + os.pathsep + os.environ.get('PATH', '')
```

### Issue 3: Model Files Not Found (fastembed)

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: '.../cache/fastembed_models/...'
```

**Root Cause:** Model directory path incorrect or not bundled.

**Fix:**
```python
# In your app initialization
import sys
from pathlib import Path

def get_model_path():
    if getattr(sys, 'frozen', False):
        # Running from PyInstaller bundle
        return Path(sys._MEIPASS) / 'fastembed_models'
    else:
        # Development
        return Path.home() / '.cache' / 'fastembed_models'

model_cache = get_model_path()
model_cache.mkdir(parents=True, exist_ok=True)

embedding = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_dir=str(model_cache),
    local_files_only=True
)
```

### Issue 4: Uvicorn Worker Spawn Loop on Windows

**Symptom:** Executable spawns exponentially more processes.

**Root Cause:** `workers > 1` with Windows spawn mode.

**Fix:**
- Set `workers=1` in uvicorn.run()
- Move uvicorn.run() to `if __name__ == '__main__'` block
- Call `multiprocessing.freeze_support()` before any async code

### Issue 5: ONNX Runtime Segmentation Fault

**Symptom:**
```
RuntimeError: ONNX Runtime error: OrtPybindThrowException
```

**Root Cause:** Missing provider DLL or incompatible ONNX model version.

**Fixes:**
1. Test with `local_files_only=True` (force local models)
2. Verify model.onnx compatibility with bundled ONNX Runtime version
3. Disable advanced providers:
```python
import onnxruntime as ort
ort.set_default_logger_severity(4)  # Reduce noise
providers = ['CPUExecutionProvider']
session = ort.InferenceSession(model_path, providers=providers)
```

**Source:** [PyInstaller troubleshooting](https://pyinstaller.org/en/stable/when-things-go-wrong.html), [ONNX Runtime issue #25193](https://github.com/microsoft/onnxruntime/issues/25193)

---

## 7. Binary Size Optimization

### Size Breakdown (Unoptimized)

| Component | Size |
|-----------|------|
| Python runtime | ~20MB |
| FastAPI + Starlette | ~10MB |
| Uvicorn + async libs | ~8MB |
| ChromaDB + dependencies | ~50MB |
| ONNX Runtime | ~60MB |
| Tokenizers | ~15MB |
| PyMuPDF | ~20MB |
| fastembed model (all-MiniLM-L6-v2) | ~35MB |
| Other deps (numpy, scipy, etc.) | ~50MB |
| **Total** | **~268MB** |

### Reduction Strategies

**1. UPX Compression (Windows only)**
- Reduces binary by 30-50%
- Final size: ~130-190MB
- May slow startup by 1-2 seconds
- Enable in spec: `upx=True`

**2. Exclude Unused Modules**
```python
excludedimports=[
    'matplotlib',
    'scipy',  # if not used
    'pandas',
    'PIL',
]
```
Potential savings: ~30-50MB

**3. Lazy Loading**
Use `if TYPE_CHECKING` to defer large imports:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
else:
    chromadb = None  # Lazy import at runtime
```

**4. One-file vs One-folder**
- `--onefile`: Single executable (slower startup, more disk i/o)
- `--onedir`: Folder with exe + dependencies (faster startup)

Recommendation: Use `--onedir` for faster startup.

**5. Avoid CUDA/GPU Providers**
Default ONNX Runtime includes CPU-only. Ensure you don't bundle GPU providers unless needed (+100MB+).

**Source:** [PyInstaller size optimization docs](https://pyinstaller.org/en/stable/usage.html), [GitHub issue #3111](https://github.com/pyinstaller/pyinstaller/issues/3111)

---

## 8. Build & Test Workflow

### Step-by-step

1. **Generate initial spec:**
   ```bash
   pyi-makespec --onedir --console main.py
   ```

2. **Customize spec** with complete hidden imports list and data files

3. **Build:**
   ```bash
   pyinstaller main.spec --debug=imports
   ```

4. **Test with debug output:**
   ```bash
   dist/mini-rag/mini-rag.exe 2>&1 | grep -i "error\|not found"
   ```

5. **Fix missing imports:** Add to `hiddenimports` list and rebuild

6. **Package:** Create .zip or installer for distribution

### Debugging Commands

```bash
# Show what PyInstaller collects
pyinstaller --debug=all main.spec

# Analyze imports
pyinstaller --debug=imports main.spec 2>&1 | grep -i "import"

# Check final binary size
du -sh dist/mini-rag/

# Verify DLLs in bundle (Windows)
dir /s dist\mini-rag\*.dll
```

---

## 9. Model File Pre-download Strategy

### Recommended Approach

**Before packaging:**
```bash
python -c "
from fastembed import TextEmbedding
embedding = TextEmbedding(
    model_name='sentence-transformers/all-MiniLM-L6-v2'
)
# Downloads model to ~/.cache/fastembed_models/
print('Model cached at:', embedding.model_dir)
"

# Copy to your repo
mkdir -p models/all-MiniLM-L6-v2
cp ~/.cache/fastembed_models/* models/all-MiniLM-L6-v2/
```

**In spec file:**
```python
datas += [('models/all-MiniLM-L6-v2', 'fastembed_models')]
```

**In app:**
```python
if getattr(sys, 'frozen', False):
    cache_dir = os.path.join(sys._MEIPASS, 'fastembed_models')
else:
    cache_dir = os.path.expanduser('~/.cache/fastembed_models')

embedding = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_dir=cache_dir,
    local_files_only=True
)
```

---

## Recommended Command-line Build

```bash
pyinstaller \
  --onedir \
  --console \
  --windowed=False \
  --name=mini-rag \
  --distpath=./dist \
  --buildpath=./build \
  --specpath=./build \
  --collect-all=chromadb \
  --collect-all=onnxruntime \
  --collect-all=tokenizers \
  --collect-all=fastapi \
  --collect-all=starlette \
  --collect-all=uvicorn \
  --hidden-import=fitz \
  --hidden-import=h11 \
  --hidden-import=uvicorn.protocols.http.h11_impl \
  --hidden-import=winloop \
  --add-data="models/all-MiniLM-L6-v2:fastembed_models" \
  --strip \
  --upx \
  --debug=imports \
  main.py
```

---

## Unresolved Questions

1. **GPU Support:** Should ONNX Runtime include CUDA/TensorRT providers? (Adds 100-300MB, requires NVIDIA dependencies)
2. **SQLite Bundling:** Does SQLite get bundled correctly by ChromaDB data collection, or needs explicit binaries?
3. **Network Model Fallback:** Should app support downloading models if bundled version missing? (Not recommended for offline use)
4. **Code Signing:** Windows SmartScreen/security implications for unsigned exe?

---

## Sources

- [ChromaDB PyInstaller Issue #4092](https://github.com/chroma-core/chroma/issues/4092)
- [PyInstaller Hooks Documentation](https://pyinstaller.org/en/stable/hooks.html)
- [PyInstaller Spec Files Documentation](https://pyinstaller.org/en/stable/spec-files.html)
- [ONNX Runtime DLL Issue #25193](https://github.com/microsoft/onnxruntime/issues/25193)
- [PyInstaller FastAPI Example](https://github.com/iancleary/pyinstaller-fastapi)
- [Uvicorn Windows Multiprocessing #1820](https://github.com/Kludex/uvicorn/discussions/1820)
- [PyMuPDF PyInstaller Issue #712](https://github.com/pymupdf/PyMuPDF/issues/712)
- [FastEmbed Model Management #229](https://github.com/qdrant/fastembed/issues/229)
- [PyInstaller Troubleshooting](https://pyinstaller.org/en/stable/when-things-go-wrong.html)
- [Winloop PyPI](https://pypi.org/project/winloop/)
- [PyInstaller Size Optimization](https://github.com/pyinstaller/pyinstaller/issues/3111)
