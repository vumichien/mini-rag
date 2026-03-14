# PyInstaller Windows Build Implementation Checklist

## Pre-Build Setup

- [ ] **Model Files**
  - [ ] Pre-download all-MiniLM-L6-v2 model
  - [ ] Place in `models/all-MiniLM-L6-v2/` directory
  - [ ] Verify contains: `model.onnx`, `tokenizer.json`, `vocab.txt`, `config.json`

- [ ] **Dependencies**
  - [ ] Create `requirements.txt` with all packages
  - [ ] Install in dev environment: `pip install -r requirements.txt`
  - [ ] Add `winloop` for Windows event loop (conditional: `winloop; sys_platform == 'win32'`)
  - [ ] Remove or conditionally exclude `uvloop`

- [ ] **Entry Point**
  - [ ] Create `main.py` with `multiprocessing.freeze_support()` at the very top
  - [ ] Implement proper model path resolution for frozen apps (check `sys._MEIPASS`)
  - [ ] Set `workers=1` in `uvicorn.run()`
  - [ ] Set `reload=False` in production config

## Spec File Creation

- [ ] **Generate Initial Spec**
  ```bash
  pyi-makespec --onedir --console main.py
  ```

- [ ] **Edit main.spec**
  - [ ] Add imports:
    ```python
    from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
    ```
  - [ ] Configure `binaries` with ONNX DLL collection:
    ```python
    binaries = [*collect_dynamic_libs('onnxruntime')]
    ```
  - [ ] Configure `datas` with all package data + model files:
    ```python
    datas = [
        *collect_data_files('chromadb'),
        *collect_data_files('onnxruntime'),
        *collect_data_files('tokenizers'),
        *collect_data_files('fastapi'),
        *collect_data_files('starlette'),
        ('models/all-MiniLM-L6-v2', 'fastembed_models'),
    ]
    ```
  - [ ] Add complete `hiddenimports` list (see research doc)
  - [ ] Enable UPX: `upx=True`
  - [ ] Enable stripping: `strip=True`
  - [ ] Set `console=True` (False for GUI apps)

## Build & Test

- [ ] **Build with Debug Output**
  ```bash
  pyinstaller main.spec --debug=imports
  ```

- [ ] **Check for Build Errors**
  - [ ] No import analysis errors
  - [ ] All DLL files present in `dist/mini-rag/` folder
  - [ ] Model files bundled in `dist/mini-rag/fastembed_models/`

- [ ] **Runtime Testing**
  - [ ] Execute: `dist/mini-rag/mini-rag.exe`
  - [ ] Check for ModuleNotFoundError (if found, add to hiddenimports)
  - [ ] Check for FileNotFoundError (if DLL related, verify binary collection)
  - [ ] Test RAG functionality (embedding generation, ChromaDB operations)
  - [ ] Test PDF loading (PyMuPDF)
  - [ ] Test FastAPI endpoint at `http://localhost:8000`

- [ ] **Verify Model Loading**
  - [ ] Embedding model loads from bundled path
  - [ ] No network calls to HuggingFace
  - [ ] Model inference works correctly

## Optimization

- [ ] **Binary Size Check**
  - [ ] Record size: `du -sh dist/mini-rag/`
  - [ ] Expected: 150-350MB (depending on UPX)
  - [ ] If too large, identify and exclude unnecessary modules

- [ ] **UPX Verification**
  - [ ] Build completes successfully
  - [ ] Startup time acceptable (may increase by 1-2 seconds)
  - [ ] Test that exe still functions after compression

- [ ] **Performance Testing**
  - [ ] RAG query execution time acceptable
  - [ ] Memory usage reasonable
  - [ ] No obvious memory leaks over extended use

## Troubleshooting Checklist

**If ModuleNotFoundError occurs:**
- [ ] Identify missing module from error message
- [ ] Add to `hiddenimports` list in spec
- [ ] Rebuild and test

**If DLL FileNotFoundError occurs:**
- [ ] Check that ONNX Runtime DLLs exist in dist folder
- [ ] Verify `collect_dynamic_libs('onnxruntime')` is in binaries
- [ ] Try adding runtime hook for LD_LIBRARY_PATH setup

**If model files not found:**
- [ ] Verify model directory exists in source
- [ ] Check datas entry includes model path
- [ ] Use `sys._MEIPASS` for frozen app path detection
- [ ] Verify model files actually copied to dist folder

**If Uvicorn spawns too many workers:**
- [ ] Ensure `workers=1` in uvicorn.run()
- [ ] Verify `multiprocessing.freeze_support()` is called before imports
- [ ] Ensure uvicorn.run() is in `if __name__ == '__main__'` block

**If uvloop error on Windows:**
- [ ] Remove uvloop from requirements
- [ ] Install winloop instead
- [ ] Add event loop policy switch in code for Windows

## Distribution

- [ ] **Packaging**
  - [ ] Create installer (NSIS, InnoSetup) or ZIP archive
  - [ ] Include README with system requirements
  - [ ] Document model/functionality limitations

- [ ] **Testing on Target System**
  - [ ] Test on Windows 10/11 machine without Python installed
  - [ ] Verify no missing dependencies
  - [ ] Test all core functionality

---

**Total Expected Time:** 2-4 hours (first build with troubleshooting)

**Reference:** See `researcher-02-pyinstaller-packaging.md` for detailed explanations and code examples.
