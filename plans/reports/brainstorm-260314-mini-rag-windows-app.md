# Brainstorm Report: Mini RAG Windows Desktop App

**Date:** 2026-03-14
**Status:** Complete — Ready for implementation planning

---

## Problem Statement

Build a Windows `.exe` installer for a self-contained RAG (Retrieval-Augmented Generation) system. Users upload PDFs, the app chunks and embeds them locally, and returns top 5 semantically similar chunks when queried. Zero setup required — install and run.

## Requirements

- Windows `.exe` one-click installer
- Upload PDF → chunk → embed → store
- Query → return top 5 similar chunks (no LLM answer generation)
- Fully local, fully offline (no API keys, no internet after install)
- All AI models bundled in installer (~230MB acceptable)
- Medium scale: 100-500 PDFs
- Single shortcut launches everything

---

## Approaches Evaluated

### Option A: Electron + Python Sidecar
- Pros: Mature, well-documented
- Cons: +150MB for Chromium, total installer ~400MB+
- **Rejected** — too heavy

### Option B: Pure Electron (JS embeddings)
- Pros: Single tech stack
- Cons: No mature JS embedding libs, need Python anyway for ML
- **Rejected** — not viable

### Option C: Tauri + PyInstaller Sidecar ✅
- Pros: Lean WebView2 shell (~10MB), clean separation, proper sidecar lifecycle management
- Cons: Build pipeline complexity (PyInstaller + Tauri), 3-8s cold start
- **Chosen**

### Option D: Python Desktop (Tkinter/PyQt)
- Pros: Simplest, single process
- Cons: Less polished UI, limited styling
- **Rejected** — user prefers Tauri

---

## Final Architecture

```
[Installer: mini-rag-setup.exe ~230MB]
    ↓
[Tauri App: mini-rag.exe]
├── WebView2 (React + TypeScript UI)
│   ├── Upload page: drag-drop PDFs, processing status
│   ├── Documents list: manage uploaded docs
│   └── Search page: query input, top-5 results cards
│
└── Python Sidecar: api-server.exe (PyInstaller compiled)
    ├── FastAPI + Uvicorn → localhost:52547
    ├── fastembed (all-MiniLM-L6-v2 ONNX, ~40MB)
    ├── PyMuPDF (PDF text extraction)
    ├── ChromaDB embedded (persistent vector store)
    └── Data storage: %APPDATA%/mini-rag/
            ├── chroma/          (vector store files)
            └── uploads/         (original PDFs)
```

---

## Key Technology Decisions

### Embedding: fastembed (not sentence-transformers)
- sentence-transformers requires PyTorch → ~800MB installer
- fastembed uses ONNX Runtime → ~50MB, same model (all-MiniLM-L6-v2)
- **Critical** for hitting ~230MB installer target

### Vector DB: ChromaDB (embedded mode)
- Evaluated Qdrant embedded — too complex for PyInstaller (Rust native bindings)
- ChromaDB embedded: in-process, no separate server, well-tested with PyInstaller
- `chromadb.Client(Settings(persist_directory=path))` — simple, reliable

### Backend: FastAPI
- Python endpoints: `POST /upload`, `GET /documents`, `DELETE /documents/{id}`, `POST /search`
- Communicates with React via localhost HTTP

### Frontend: React + TypeScript
- Tauri WebView2 renders the React app
- Calls Python API via `fetch("http://localhost:52547/...")`
- Tauri shell API used only for: sidecar lifecycle, window controls

---

## Data Flow

```
Upload:
User → drag PDF → React → POST /upload → PyMuPDF extract text
  → chunk (1000 chars, 200 overlap) → fastembed encode
  → ChromaDB store (with metadata: filename, page, chunk_index)

Search:
User → type query → React → POST /search → fastembed encode query
  → ChromaDB top-5 similarity search
  → return [{text, filename, page, score}] → React renders cards
```

## Chunking Strategy
- Fixed-size: 1000 characters per chunk
- Overlap: 200 characters
- Metadata per chunk: `{doc_id, filename, page_number, chunk_index}`

---

## Build Pipeline

```
1. cd backend/ && pyinstaller api-server.spec
   → dist/api-server/api-server.exe (~180MB with all deps)

2. Copy api-server.exe to src-tauri/binaries/

3. cd . && npm run tauri build
   → target/release/bundle/nsis/mini-rag_x.x.x_x64-setup.exe
```

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| PyInstaller hidden imports (ChromaDB, fastembed ONNX) | High | Explicit `--collect-all` in .spec file |
| 3-8s cold start for PyInstaller sidecar | Medium | Loading screen, /health polling |
| WebView2 not on target Windows | Low | Tauri installer bundles WebView2 bootstrapper |
| Port 52547 conflict | Low | Fixed rare port; check on startup |
| ChromaDB collection corruption on force-quit | Low | WAL mode, graceful shutdown signal |

---

## Success Criteria

- [ ] Single `.exe` installer, no prerequisites
- [ ] Install completes in <2 minutes
- [ ] App opens within 10 seconds of clicking shortcut
- [ ] PDF upload + chunking + embedding completes in <30s for 50-page PDF
- [ ] Search returns top 5 results in <2 seconds
- [ ] App works fully offline after install
- [ ] Uninstall via Windows Add/Remove Programs

---

## Unresolved Questions

- Code signing: for personal use, unsigned is fine; Windows SmartScreen will warn first run
- Auto-update mechanism: not in scope for v1
- Multi-language PDF support: PyMuPDF handles most, but non-Latin scripts may need testing
