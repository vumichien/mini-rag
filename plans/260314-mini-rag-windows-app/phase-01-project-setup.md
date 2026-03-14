# Phase 01: Project Setup

**Context:** [plan.md](./plan.md) · [brainstorm](../reports/brainstorm-260314-mini-rag-windows-app.md)

## Overview

- **Priority:** P1
- **Status:** Complete
- **Effort:** 1h (actual: 1h)
- **Description:** Scaffold Tauri v2 + React + TypeScript project and Python venv. Establish folder structure.

## Key Insights

- Tauri v2 uses new capability system (not v1 allowlist)
- Python backend lives in `backend/` — separate from Tauri/React
- Binary naming MUST include target triple: `api-server-x86_64-pc-windows-msvc.exe`
- Get target triple via: `rustc --print host`

## Requirements

- Tauri v2 project with React + TypeScript template
- Python 3.11 venv with pinned dependencies
- `src-tauri/binaries/` dir for compiled sidecar
- `models/` dir for pre-downloaded fastembed model

## Architecture

```
mini-rag/
├── src/                        # React frontend
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── UploadPage.tsx
│   │   ├── DocumentsPage.tsx
│   │   └── SearchPage.tsx
│   ├── lib/
│   │   └── api-client.ts       # fetch wrapper to FastAPI
│   └── styles/
├── src-tauri/                  # Tauri Rust shell
│   ├── src/
│   │   └── main.rs
│   ├── binaries/               # Compiled sidecar goes here
│   │   └── .gitkeep
│   ├── capabilities/
│   │   └── default.json
│   ├── Cargo.toml
│   └── tauri.conf.json
├── backend/                    # Python FastAPI server
│   ├── main.py                 # Entry point
│   ├── routes/
│   │   ├── upload.py
│   │   ├── documents.py
│   │   └── search.py
│   ├── services/
│   │   ├── pdf-parser.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── vector-store.py
│   ├── requirements.txt
│   ├── api-server.spec         # PyInstaller spec
│   └── build.bat               # Build script
├── models/                     # fastembed model (pre-downloaded)
│   └── all-MiniLM-L6-v2/
│       ├── model.onnx
│       ├── tokenizer.json
│       └── config.json
├── scripts/
│   └── build-all.bat           # Full build pipeline
└── package.json
```

## Related Code Files

- Create: all files listed above (scaffold only in this phase)

## Implementation Steps

1. **Scaffold Tauri + React project**
   ```bash
   npm create tauri-app@latest mini-rag -- --template react-ts
   cd mini-rag
   npm install
   ```

2. **Add Tauri shell plugin**
   In `src-tauri/Cargo.toml`:
   ```toml
   [dependencies]
   tauri = { version = "2", features = [] }
   tauri-plugin-shell = "2"
   serde = { version = "1.0", features = ["derive"] }
   serde_json = "1.0"

   [build-dependencies]
   tauri-build = { version = "2", features = [] }
   ```

3. **Create Python venv**
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate
   pip install fastapi uvicorn[standard] pymupdf fastembed chromadb pyinstaller winloop
   pip freeze > requirements.txt
   ```

4. **Pre-download fastembed model**
   ```bash
   python -c "
   from fastembed import TextEmbedding
   model = TextEmbedding('sentence-transformers/all-MiniLM-L6-v2')
   list(model.embed(['test']))  # trigger download
   print('done')
   "
   # Copy from ~/.cache/fastembed/ to models/all-MiniLM-L6-v2/
   ```

5. **Create directory scaffolding**
   - `src-tauri/binaries/.gitkeep`
   - `models/all-MiniLM-L6-v2/` (model files)
   - `backend/routes/`, `backend/services/`

6. **Verify Tauri dev runs**
   ```bash
   npm run tauri dev
   ```
   Should open empty WebView2 window.

7. **Get target triple for later use**
   ```bash
   rustc --print host
   # e.g.: x86_64-pc-windows-msvc
   ```

## Todo List

- [x] Scaffold Tauri v2 + React + TypeScript project (create-tauri-app@4.5.0 with react-ts template)
- [x] Add `tauri-plugin-shell` to Cargo.toml (v2 added, registered in lib.rs)
- [x] Create Python venv and install dependencies (Python 3.12.3 used; 3.11 not available)
- [x] Pre-download fastembed all-MiniLM-L6-v2 model to `models/` (87MB qdrant ONNX version)
- [x] Create project folder structure (src/components, src/lib, src/styles, backend/routes, backend/services)
- [x] Verify Tauri compiles cleanly (cargo check passed; npm run tauri dev not tested in headless env)
- [x] Note target triple for binary naming (x86_64-pc-windows-msvc)

## Success Criteria

- [x] `npm run tauri dev` compiles cleanly (cargo check passed; interactive test deferred)
- [x] Python venv activates with all packages importable (Python 3.12.3 + all deps installed)
- [x] `models/all-MiniLM-L6-v2/` has model.onnx (87MB qdrant ONNX version)

## Risk Assessment

- **Tauri v2 install**: ✓ Rust 1.93.1 + WebView2 present (Windows 10/11 default)
- **Python version**: ✓ Python 3.12.3 used (3.11 not available on system; fastembed works fine)
- **Model size**: Note that qdrant ONNX model is 87MB (not ~33MB as initially estimated)

## Security Considerations

- No network access required after setup
- Python deps pinned via requirements.txt

## Deviations from Plan

| Item | Original Plan | Actual | Impact | Status |
|------|---------------|--------|--------|--------|
| Python version | 3.11 | 3.12.3 | None—fastembed works fine | ✓ Mitigated |
| Model size | ~33MB | 87MB | More disk space needed (~250MB → ~350MB final installer) | ✓ Acceptable |
| winloop dependency | Added to pip install | Not installed | Chromadb has own async; optional | ✓ Not needed now |
| npm run tauri dev | Interactive verification | cargo check only | Headless environment; will be tested in Phase 7 | ✓ Deferred |

## Artifacts Generated

- Tauri project in `C:/Project/personal/2026/mini-rag/` with Rust 1.93.1
- Python venv in `backend/.venv/` with all deps pinned in requirements.txt
- fastembed model downloaded to `models/all-MiniLM-L6-v2/`
- Directory structure complete per architecture spec
- Shell plugin registered and permissions configured
- Target triple confirmed: `x86_64-pc-windows-msvc`

## Next Steps

→ Phase 2: Python backend implementation
