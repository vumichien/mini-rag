# Research Summary: PyInstaller Packaging

**Status:** Complete
**Date:** 2026-03-14
**Lead Research Document:** `researcher-02-pyinstaller-packaging.md`

## Key Findings

### 1. Hidden Imports (Critical)
- **40+ modules** required for full ChromaDB functionality
- Dynamic import chains in ChromaDB require explicit listing
- Must include: `chromadb.segment.impl.*`, `chromadb.db.impl.*`, `chromadb.execution.executor.local`

### 2. ONNX Runtime DLLs (Critical)
- Use `collect_dynamic_libs('onnxruntime')` in binaries
- Common failure: `onnxruntime_pybind11_state` missing → DLL bundling issue
- Solution: Explicit DLL collection via PyInstaller hooks

### 3. Model Files (Critical)
- Pre-download all-MiniLM-L6-v2 (~35MB) to `models/` directory
- Bundle in spec: `datas += [('models/all-MiniLM-L6-v2', 'fastembed_models')]`
- Use `local_files_only=True` at runtime to prevent network calls

### 4. FastAPI/Uvicorn on Windows
- **MUST:** `multiprocessing.freeze_support()` at top of main entry
- Set `workers=1` (spawn mode, not fork)
- Disable `reload=False`
- Replace uvloop with winloop

### 5. Binary Size
- **Unoptimized:** 250-350MB
- **With UPX:** 130-190MB
- **Strategy:** Use `--onedir` (faster), enable UPX compression

### 6. Common Failures & Fixes
| Failure | Cause | Fix |
|---------|-------|-----|
| ModuleNotFoundError | Missing hidden import | Add to hiddenimports list |
| FileNotFoundError DLL | ONNX Runtime not bundled | Use collect_dynamic_libs() |
| Model file not found | Path misconfigured | Use sys._MEIPASS for frozen apps |
| Worker spawn loop | workers > 1 on Windows | Set workers=1 |
| uvloop incompatible | uvloop doesn't support Windows | Install winloop instead |

### 7. Recommended .spec Structure
- ✅ Comprehensive hiddenimports list (see research doc)
- ✅ Dynamic lib collection for ONNX
- ✅ Data file collection for all packages
- ✅ Pre-bundled model directory
- ✅ Strip + UPX enabled

## Next Steps
1. Create `main.py` with `multiprocessing.freeze_support()` + proper model path handling
2. Pre-download fastembed model to `models/all-MiniLM-L6-v2/`
3. Generate .spec file using research recommendations
4. Build with `--debug=imports` flag
5. Test exe for import errors & model loading
6. Optimize with UPX if acceptable

---

**Full Details:** See `researcher-02-pyinstaller-packaging.md`
