# Mini RAG Windows App - System Architecture

## Overview

The Mini RAG (Retrieval-Augmented Generation) system is a self-contained Windows desktop application delivering semantic search over PDF documents. Users install once (~250MB), click the app shortcut, upload PDFs, and search across all chunks semantically.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   Windows Installer (~250MB)                    │
│                     mini-rag-setup.exe                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
        ┌───────▼────────┐          ┌────────▼────────┐
        │  Tauri v2 App  │          │  FastAPI Server │
        │ (WebView2 UI)  │          │  (PyInstaller)  │
        └───────┬────────┘          └────────┬────────┘
                │                            │
        ┌───────▼────────┐          ┌────────▼────────┐
        │  React Frontend│          │ Python Services │
        │  TypeScript    │          │  ├─ PDF Parser  │
        │ (localhost:1420)          │  ├─ Chunker     │
        │                │          │  ├─ Embedder    │
        │  Components:   │          │  └─ VectorStore │
        │  ├─ Upload Form│          │                 │
        │  ├─ DocList    │          │ (localhost:52547)
        │  └─ SearchUI   │          └────────┬────────┘
        └────────────────┘                   │
                                     ┌───────▼────────┐
                                     │ Data Directory │
                                     │  %APPDATA%/    │
                                     │  mini-rag/     │
                                     │  ├─ chroma/    │
                                     │  └─ models/    │
                                     └────────────────┘
```

## Component Architecture

### 1. Frontend Layer (Tauri React App)

**Technology Stack:**
- Tauri v2: Desktop framework bridging WebView2 (Windows native)
- React 18: UI framework
- TypeScript: Type-safe JavaScript
- Vite: Fast build tooling

**Responsibilities:**
- Render UI in WebView2 (native Windows rendering)
- Capture user interactions (upload, search)
- Communicate with FastAPI backend via HTTP
- Display search results in real-time

**Key Files:**
- `src/`: React components
- `src-tauri/`: Tauri configuration, sidecar launch logic

### 2. Backend Layer (FastAPI + Python Services)

**Technology Stack:**
- FastAPI: Async HTTP server
- uvicorn: ASGI server (1 worker on Windows)
- Python 3.11+: Core runtime
- PyInstaller: Binary packaging

**Responsibilities:**
- Expose HTTP API (6 endpoints)
- Coordinate PDF upload, parsing, chunking
- Embed text chunks using fastembed
- Store/search vectors in ChromaDB
- Gracefully shutdown on app close

**API Endpoints:**
```
POST   /upload              - Upload & process PDF
GET    /documents           - List documents
DELETE /documents/{doc_id}  - Remove document
POST   /search              - Semantic search
GET    /health              - Health check
POST   /shutdown            - Graceful shutdown
```

### 3. Data Services

#### PDF Parser (`backend/services/pdf_parser.py`)
- **Library:** PyMuPDF (fitz)
- **Input:** PDF bytes
- **Output:** [{page_number, text}, ...]
- **Features:** Extracts text per page; skips blank pages

#### Chunker (`backend/services/chunker.py`)
- **Algorithm:** Fixed-size sliding window (1000 chars, 200 char overlap)
- **Input:** Text, filename, page_number
- **Output:** [{text, filename, page_number, chunk_index}, ...]
- **Rationale:** Overlap ensures semantic continuity at boundaries

#### Embedder (`backend/services/embedder.py`)
- **Model:** sentence-transformers/all-MiniLM-L6-v2 (384-dim vectors)
- **Library:** fastembed (ONNX-based, offline-capable)
- **Singleton Pattern:** Single instance per app session
- **Frozen Mode:** Loads model from `sys._MEIPASS/fastembed_models/` in PyInstaller
- **Dev Mode:** Loads from `models/` relative to project root

#### Vector Store (`backend/services/vector_store.py`)
- **Database:** ChromaDB (embedded, no server)
- **Persistence:** `%APPDATA%/mini-rag/chroma/`
- **Collection:** `rag_chunks` with cosine distance metric
- **Schema:**
  ```
  ids:        "{doc_id}_{chunk_index}"
  embeddings: [384-dim float vectors]
  documents:  [chunk text]
  metadatas:  {doc_id, filename, page_number, chunk_index, created_at}
  ```

### 4. Data Flow

#### Upload Flow
```
1. User selects PDF via UI
2. POST /upload with multipart file
3. PDF Parser extracts text per page
4. Chunker splits text (1000 chars, 200 overlap)
5. Embedder generates 384-dim vectors for each chunk
6. VectorStore persists chunks + embeddings + metadata
7. Return {doc_id, filename, chunk_count}
```

#### Search Flow
```
1. User enters query
2. POST /search with query string
3. Embedder generates 384-dim vector for query
4. VectorStore returns top-5 similar chunks (cosine similarity)
5. Return [{text, filename, page_number, chunk_index, score}, ...]
6. UI displays results ranked by relevance (0.0-1.0)
```

## Data Storage

### Directory Structure
```
%APPDATA%/mini-rag/
├── chroma/                    # ChromaDB persistent store
│   ├── chroma.sqlite3         # SQLite index
│   └── ...
└── models/                    # fastembed ONNX models (dev only)
    └── sentence-transformers/all-MiniLM-L6-v2/
        └── ...
```

**Note:** PyInstaller bundle includes models in `_MEIPASS/fastembed_models/`. No network access required after installation.

## Process Architecture

### Entry Point
- **File:** `backend/main.py`
- **Key Steps:**
  1. `multiprocessing.freeze_support()` (Windows + PyInstaller required)
  2. Parse `--data-dir` and `--port` from Tauri sidecar
  3. Set `MINI_RAG_DATA_DIR` environment variable
  4. Create data directory if missing
  5. Start uvicorn factory: `uvicorn.run("app:create_app", factory=True, workers=1)`

### Event Loop Policy (Windows)
```python
if sys.platform == "win32":
    try:
        import winloop
        asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
    except ImportError:
        pass  # Fall back to asyncio default
```

## Windows Compatibility Considerations

### PyInstaller + Multiprocessing
- **Issue:** PyInstaller frozen apps with Windows spawned processes hang
- **Solution:** `multiprocessing.freeze_support()` at module top
- **Impact:** Must be executed BEFORE importing other modules

### Event Loop
- **Issue:** uvloop not compatible with Windows
- **Solution:** Use `winloop` (Windows fork of uvloop) or asyncio default
- **Workers:** Must be 1 on Windows (spawn mode causes issues with >1 worker)

### Path Handling
- **Development:** Models in relative `models/` directory
- **Frozen (PyInstaller):** Models in `sys._MEIPASS/fastembed_models/`
- **Detection:** `getattr(sys, "frozen", False)` checks if running under PyInstaller

### Data Directory
- **Default:** `%APPDATA%/mini-rag/` (e.g., `C:\Users\User\AppData\Roaming\mini-rag\`)
- **Override:** Tauri passes `--data-dir` argument
- **Isolation:** Each Windows user gets own AppData folder

## Security & Isolation

| Concern | Mitigation |
|---------|-----------|
| Network Access | Listen only on `127.0.0.1` (local-only) |
| File Size | Limit uploads to 50MB |
| CORS | Allow `*` (only local UI connects) |
| Data Cleanup | All data stays in `%APPDATA%/mini-rag/` |
| Offline | No internet required after installation |

## Performance Characteristics

| Operation | Typical Duration | Constraints |
|-----------|------------------|------------|
| PDF Parse (100 pages) | ~1-2 seconds | Single-threaded, I/O bound |
| Embedding (100 chunks) | ~3-5 seconds | fastembed ONNX, CPU-bound |
| Search (top-5) | ~0.5 seconds | ChromaDB in-memory cosine distance |
| Startup | ~2-3 seconds | Model loading, DB initialization |

## Deployment & Packaging

### Build Pipeline
1. **Backend:** Python FastAPI sidecar compiled via PyInstaller
2. **Frontend:** React app bundled via Vite
3. **Bundler:** Tauri bundler creates Windows `.msi` or `.exe` installer
4. **Size:** ~250MB (includes Python runtime, ONNX models, all dependencies)

### Distribution
- Single `.exe` installer
- No MSI complexity; runs standalone
- Can be distributed via GitHub Releases, website download, etc.

## Monitoring & Debugging

### Health Check
```bash
curl http://127.0.0.1:52547/health
# Returns: {"status":"ok"}
```

### Logging
- FastAPI logs to stdout (captured by Tauri launcher)
- Log level: `info` (set in `backend/main.py`)
- Errors logged with traceback

### Testing (Dev Mode)
```bash
# Run backend standalone
cd backend
python main.py --port 52547

# Run React frontend
cd .
npm run tauri dev
```

## Future Enhancements

1. **Hybrid Search:** Combine keyword (BM25) + semantic search
2. **LLM Integration:** Chat API using search results as context
3. **Multi-Model Support:** Allow users to choose embedding models
4. **Batch Operations:** Upload multiple PDFs, bulk search
5. **Export Results:** Save search results as PDF/CSV
6. **Web Version:** Deploy same API to web (remove Tauri wrapper)
