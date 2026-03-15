# PyInstaller Packaging Research - Mini-RAG Windows App

**Research Completed:** 2026-03-14
**Domain:** Python desktop application packaging (Windows)
**Focus Stack:** ChromaDB + FastEmbed (ONNX) + PyMuPDF + FastAPI + Uvicorn

## Documents

### 0. **researcher-01-tauri-sidecar.md** (Tauri Integration)
Comprehensive technical report on Tauri v2 Python sidecar integration:
- `tauri.conf.json` configuration with `externalBin` array
- Binary naming convention: `name-<target-triple>.exe` (e.g., `api-server-x86_64-pc-windows-msvc.exe`)
- Rust API: `tauri_plugin_shell::ShellExt` trait for spawning/killing
- Sidecar lifecycle management (start on app open, kill on close)
- Port passing patterns (hardcoded, command response, config file)
- Windows-specific gotchas (path issues, antivirus, permissions, one-file PyInstaller limitations)
- Tauri v1 vs v2 differences and migration guide
- Capability permissions system configuration

**~650 lines | ~16KB | Prerequisite for integration**

### 0a. **RESEARCH-FINDINGS.md** (Tauri Quick Reference)
Quick lookup guide with code snippets for:
- Configuration snippets (tauri.conf.json, Cargo.toml, capabilities)
- Binary naming conventions
- Rust skeleton code
- Key gotchas table
- Checklist for sidecar registration

**Use when:** You need quick answers on Tauri integration without reading full report

### 1. **researcher-02-pyinstaller-packaging.md** (Main Report)
Comprehensive technical report covering:
- Hidden imports requirements for ChromaDB, FastAPI, Uvicorn, PyMuPDF
- ONNX Runtime DLL bundling strategies
- FastEmbed model file bundling (all-MiniLM-L6-v2)
- Windows multiprocessing & uvloop/winloop handling
- Complete .spec file template
- Known issues & runtime fixes
- Binary size optimization techniques
- Build & test workflow

**730 lines | ~19KB | Primary reference**

### 2. **RESEARCH-SUMMARY.md** (Quick Reference)
Executive summary with:
- Key findings (7 critical areas)
- Common failures & fixes table
- Next implementation steps

**Use when:** You need quick answers before deep-diving into full research

### 3. **IMPLEMENTATION-CHECKLIST.md** (Execution Guide)
Step-by-step checklist for:
- Pre-build setup (model files, dependencies, entry point)
- Spec file creation with code snippets
- Build & test procedures
- Troubleshooting guide
- Distribution packaging

**Use when:** Actually implementing the PyInstaller build

## Quick Stats

| Metric | Value |
|--------|-------|
| Hidden Imports Required | 40+ modules |
| ONNX Runtime Size | ~60MB |
| Model File Size | ~35MB |
| Unoptimized Binary | 250-350MB |
| Optimized (UPX) | 130-190MB |
| Build Time | 5-10 minutes |
| Expected Issues | 3-5 (typical troubleshooting) |

## Critical Implementation Notes

### Must-Do Items
1. **`multiprocessing.freeze_support()`** at top of main.py (Windows requirement)
2. **`workers=1`** in uvicorn (prevent spawn loop)
3. **`collect_dynamic_libs('onnxruntime')`** in spec binaries (DLL bundling)
4. **Pre-download model** to `models/all-MiniLM-L6-v2/` (avoid network at runtime)
5. **`local_files_only=True`** when loading embeddings (enforce bundled model)

### Common Traps
- Missing ChromaDB hidden imports → ModuleNotFoundError at runtime
- Missing ONNX Runtime DLLs → "Could not find module" error
- Model files not bundled → FileNotFoundError at startup
- `workers > 1` → Exponential subprocess spawning on Windows
- Forgetting `freeze_support()` → Multiprocessing errors on Windows

## Source Quality

All findings sourced from:
- ✅ Official PyInstaller documentation (6.19.0)
- ✅ PyInstaller GitHub issues & discussions (real-world problems)
- ✅ Package maintainer repos (ChromaDB, ONNX Runtime, FastEmbed, FastAPI)
- ✅ Working implementations from community (iancleary, mohammadhasananisi)

## Next Steps

1. **Pre-Build Phase** (30 min)
   - Set up entry point with `freeze_support()`
   - Download fastembed model
   - Install winloop for Windows event loop

2. **Build Phase** (10 min)
   - Generate .spec file from template
   - Build with `--debug=imports`
   - Verify no analysis errors

3. **Test Phase** (1-2 hours)
   - Run exe and check for import errors
   - Fix missing imports (iterate)
   - Test RAG functionality

4. **Optimize Phase** (30 min)
   - Enable UPX compression
   - Measure binary size
   - Test performance on target system

---

**Total Implementation Time:** 2-4 hours (first build)

See `researcher-02-pyinstaller-packaging.md` for all technical details.
