# Codebase Summary - Mini RAG

## Project Structure

```
mini-rag/
├── backend/                              # Python FastAPI backend
│   ├── main.py                           # Entry point: multiprocessing, argparse, uvicorn
│   ├── app.py                            # FastAPI factory: lifespan, CORS, routers
│   ├── requirements.txt                  # Python dependencies
│   ├── routes/                           # HTTP endpoint handlers
│   │   ├── __init__.py                   # Router imports
│   │   ├── upload.py                     # POST /upload (PDF processing)
│   │   ├── documents.py                  # GET /documents, DELETE /documents/{id}
│   │   ├── search.py                     # POST /search (semantic search)
│   │   └── health.py                     # GET /health, POST /shutdown
│   └── services/                         # Core business logic
│       ├── __init__.py                   # Service imports
│       ├── pdf_parser.py                 # PyMuPDF text extraction
│       ├── chunker.py                    # Fixed-size text chunking (1000 chars, 200 overlap)
│       ├── embedder.py                   # fastembed ONNX integration (singleton)
│       └── vector_store.py               # ChromaDB wrapper (singleton)
├── src/                                  # React TypeScript frontend
│   ├── main.tsx                          # App entry
│   ├── App.tsx                           # Root component
│   ├── components/                       # React components
│   │   ├── UploadForm.tsx                # PDF file uploader
│   │   ├── DocumentList.tsx              # List uploaded documents
│   │   └── SearchUI.tsx                  # Search query + results display
│   └── services/                         # Frontend utilities
│       └── api.ts                        # Fetch wrapper for backend API
├── src-tauri/                            # Tauri desktop app configuration
│   ├── tauri.conf.json                   # App config (title, icon, sidecar)
│   ├── Cargo.toml                        # Rust dependencies (Tauri)
│   └── src/main.rs                       # Tauri entry (spawn FastAPI sidecar)
├── docs/                                 # Project documentation
│   ├── system-architecture.md            # This file: component architecture, data flow
│   ├── codebase-summary.md               # File structure, dependencies, quick ref
│   ├── code-standards.md                 # (To be created) Coding conventions
│   ├── development-roadmap.md            # (To be created) Milestones, timeline
│   └── project-changelog.md              # (To be created) Version history
├── plans/                                # Project planning & reports
│   └── 260314-mini-rag-windows-app/      # Main implementation plan
│       ├── plan.md                       # Overview & phase status
│       ├── phase-01-project-setup.md     # (Complete)
│       ├── phase-02-python-backend.md    # (Complete)
│       ├── phase-03-react-frontend.md    # (Pending)
│       ├── phase-04-tauri-integration.md # (Pending)
│       ├── phase-05-pyinstaller-build.md # (Pending)
│       ├── phase-06-tauri-bundler.md     # (Pending)
│       └── phase-07-testing.md           # (Pending)
├── package.json                          # Node.js dependencies
├── tsconfig.json                         # TypeScript config (frontend)
├── tsconfig.node.json                    # TypeScript config (Tauri build)
├── vite.config.ts                        # Vite bundler config
├── index.html                            # HTML entry point
├── .vscode/                              # Editor settings
└── .gitignore                            # Git ignore rules
```

## Python Backend (`backend/`)

### Dependencies

**Core:**
- `fastapi==0.104.1` - Web framework
- `uvicorn==0.24.0` - ASGI server
- `pydantic==2.5.0` - Data validation

**Data Processing:**
- `pymupdf==1.23.8` - PDF text extraction
- `chromadb==0.4.20` - Vector database (embedded)
- `fastembed==0.1.1` - ONNX embeddings (384-dim)

**Windows Support:**
- `winloop==0.1.0` - Windows event loop (optional; falls back to asyncio)

### Key Services

#### `embedder.py`
- **Class:** `EmbedderService` (singleton)
- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- **Output Dim:** 384
- **Methods:**
  - `initialize()`: Load model (first call or startup)
  - `embed(texts: list[str])`: Return list of 384-dim vectors
  - `_get_model_cache_dir()`: Detect frozen vs. dev mode paths

**Frozen Mode Path Logic:**
```python
if getattr(sys, "frozen", False):
    # PyInstaller: models bundled in _MEIPASS
    return Path(sys._MEIPASS) / "fastembed_models"
else:
    # Dev mode: models in project root
    return Path(__file__).parent.parent.parent / "models"
```

#### `vector_store.py`
- **Class:** `VectorStoreService` (singleton)
- **Database:** ChromaDB PersistentClient
- **Collection:** `rag_chunks` with `hnsw:space=cosine`
- **Methods:**
  - `initialize()`: Connect to ChromaDB, get/create collection
  - `add_chunks()`: Persist chunks + embeddings + metadata
  - `search()`: Query top-N results (default 5), return with scores
  - `list_documents()`: Aggregate chunks by doc_id
  - `delete_document()`: Remove all chunks for a doc_id

**Metadata Schema:**
```json
{
  "doc_id": "uuid-string",
  "filename": "example.pdf",
  "page_number": 1,
  "chunk_index": 0,
  "created_at": "2026-03-14T10:30:00Z"
}
```

#### `pdf_parser.py`
- **Function:** `extract_pages(pdf_bytes: bytes)`
- **Returns:** `[{page_number, text}, ...]`
- **Behavior:** Skips blank pages; uses PyMuPDF `get_text("text")`

#### `chunker.py`
- **Function:** `chunk_text(text, filename, page_number)`
- **Algorithm:** Sliding window (1000 char size, 200 char overlap)
- **Returns:** `[{text, filename, page_number, chunk_index}, ...]`

### Routes

#### `upload.py`
- **Endpoint:** `POST /upload`
- **Input:** Multipart form with `file` field (PDF)
- **Validation:**
  - Must be `.pdf` extension
  - Max 50MB
  - Must have extractable text
- **Response:**
  ```json
  {
    "doc_id": "uuid",
    "filename": "example.pdf",
    "chunk_count": 42
  }
  ```

#### `documents.py`
- **Endpoint:** `GET /documents`
- **Response:** `{documents: [{doc_id, filename, chunk_count}, ...]}`

- **Endpoint:** `DELETE /documents/{doc_id}`
- **Response:** `{status: "deleted", doc_id: "uuid"}`
- **Behavior:** Returns 404 if doc_id not found

#### `search.py`
- **Endpoint:** `POST /search`
- **Request:**
  ```json
  {
    "query": "What is RAG?",
    "n_results": 5
  }
  ```
- **Response:**
  ```json
  {
    "results": [
      {
        "text": "chunk text...",
        "filename": "example.pdf",
        "page_number": 1,
        "chunk_index": 0,
        "score": 0.85
      },
      ...
    ]
  }
  ```

#### `health.py`
- **Endpoint:** `GET /health`
- **Response:** `{status: "ok"}`

- **Endpoint:** `POST /shutdown`
- **Behavior:** Defers SIGTERM 200ms to allow response to flush
- **Response:** `{status: "shutting down"}`

### Entry Point (`main.py`)

**Startup Sequence:**
1. `multiprocessing.freeze_support()` (MUST be first line)
2. Import sys, os, asyncio, argparse, uvicorn
3. Set event loop policy for Windows (winloop or asyncio)
4. Parse `--data-dir` and `--port` arguments
5. Create data directory if missing
6. Start uvicorn: `uvicorn.run("app:create_app", factory=True, workers=1)`

**Key Parameters:**
- `host="127.0.0.1"` - Local-only (security)
- `port=52547` - Default (override via `--port`)
- `workers=1` - MUST be 1 on Windows
- `reload=False` - No auto-reload in production

### App Factory (`app.py`)

**Lifespan Context:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize singletons
    EmbedderService.initialize()
    VectorStoreService.initialize()
    yield
    # Shutdown: (cleanup if needed)
```

**Middleware:**
- CORS: Allow all origins (only local UI connects)

**Routers Included:**
- `upload`, `documents`, `search`, `health`

## React Frontend (`src/`)

### Entry Point
- **File:** `main.tsx`
- **Mounts:** React root to `<div id="root">`

### App Component (`App.tsx`)
- **Structure:** Tab-based navigation with 3 views
- **Tabs:** Upload, Documents, Search
- **Behavior:** LoadingScreen guard until backend ready; smooth transitions
- **State Management:** Tab selection, document refresh trigger

### Components

#### `LoadingScreen.tsx`
- **Behavior:** Polls /health every 500ms, 30s timeout
- **Display:** Spinner + "Starting up..." status
- **Transition:** Calls onReady callback when health check succeeds
- **Error Handling:** Timeout message after 30s

#### `UploadPage.tsx`
- **Input:** PDF file via drag-drop or file picker
- **Validation:** .pdf extension check
- **Action:** POST to `/upload`
- **Feedback:** Upload progress, success/error messages
- **Refresh:** Triggers document list reload on success

#### `DocumentsPage.tsx`
- **Data:** Fetch from `GET /documents`
- **Display:** List of {filename, chunk_count, delete button}
- **Delete:** Confirmation dialog + API call
- **Refresh:** Auto-load on mount, after delete

#### `SearchPage.tsx`
- **Input:** Text query
- **Action:** POST to `/search` with n_results=5
- **Results:** Styled cards with {text, filename, page, score}
- **Status:** Loading state during search

### API Client (`lib/api-client.ts`)

**Base URL:** `http://127.0.0.1:52547`

**Methods:**
```typescript
checkHealth(): Promise<boolean>
uploadPDF(file: File): Promise<UploadResponse>
getDocuments(): Promise<Document[]>
deleteDocument(doc_id: string): Promise<void>
search(query: string): Promise<SearchResult[]>
```

### TypeScript Types (`types.ts`)

```typescript
interface Document {
  doc_id: string;
  filename: string;
  chunk_count: number;
}

interface SearchResult {
  text: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  score: number;
}

interface UploadResponse {
  doc_id: string;
  filename: string;
  chunk_count: number;
}
```

## Tauri Desktop Integration (`src-tauri/`)

### Configuration (`tauri.conf.json`)
- **App Title:** "Mini RAG"
- **Window:** 1200x800, always on top disabled
- **Sidecar:** `api-server.exe` (Windows binary)
- **Sidecar Args:** `--port 52547`

### Rust Entry (`main.rs`)
- **Responsibilities:**
  1. Spawn FastAPI sidecar process
  2. Wait for health check (polling `GET /health`)
  3. Open WebView to `localhost:1420` (dev) or built frontend (production)
  4. Kill sidecar on app close

## Development Workflow

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run standalone
python main.py --port 52547

# Run with data dir override
python main.py --data-dir /tmp/test-data --port 52547
```

### Frontend Development
```bash
npm install
npm run tauri dev  # Launches Tauri dev server (React HMR + backend)
```

### Build
```bash
npm run tauri build  # Creates installer (src-tauri/target/release/)
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| **Python Backend** | Rich ML ecosystem, fast to implement RAG |
| **FastAPI** | Async, Pydantic validation, auto OpenAPI docs |
| **ChromaDB Embedded** | No external DB server, persistence out-of-box |
| **fastembed** | ONNX-based, offline, fast inference |
| **Tauri v2** | Native Windows integration, Rust security, small footprint |
| **React + TypeScript** | Type safety, fast UI updates, broad adoption |
| **1000-char chunks** | Balance: not too granular, captures context |
| **workers=1** | Windows multiprocessing safety, uvicorn limitation |

## Common Maintenance Tasks

### Update Embeddings Model
1. Download new model in dev: `python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='...')"`
2. Copy to `models/` for dev testing
3. Update PyInstaller hook to include new model path
4. Test: `python backend/main.py && curl http://127.0.0.1:52547/health`

### Reset App Data
```bash
# Remove all documents + search history
rm -rf %APPDATA%\mini-rag\chroma
# App will recreate on next startup
```

### Debug Sidecar Communication
```bash
# Terminal 1: Run backend standalone
cd backend && python main.py --port 52547

# Terminal 2: Test endpoints
curl http://127.0.0.1:52547/health
curl -X POST http://127.0.0.1:52547/search -H "Content-Type: application/json" -d '{"query":"test"}'
```

## Dependencies Overview

### Python (`backend/requirements.txt`)
| Package | Purpose | Version |
|---------|---------|---------|
| fastapi | HTTP server | 0.104+ |
| uvicorn | ASGI runner | 0.24+ |
| pydantic | Validation | 2.5+ |
| pymupdf | PDF extraction | 1.23+ |
| chromadb | Vector DB | 0.4+ |
| fastembed | Embeddings | 0.1+ |
| winloop | Windows async | 0.1+ (optional) |

### JavaScript (`package.json`)
| Package | Purpose | Version |
|---------|---------|---------|
| react | UI framework | 18+ |
| typescript | Type safety | 5+ |
| @tauri-apps/api | Tauri bindings | 2+ |
| vite | Build tool | 5+ |

### Rust (`src-tauri/Cargo.toml`)
| Crate | Purpose |
|-------|---------|
| tauri | Desktop framework |
| tauri-plugin-shell | Sidecar spawning |
| tokio | Async runtime |

## Testing Strategy

### Final Status (Phase 07) - COMPLETE
**Unit Tests + E2E Tests - ALL PASSING**
- **Frontend:** 82 tests total (66 unit + 16 E2E)
- **Backend:** 86 tests total (67 unit + 19 E2E)
- **Total:** 168 tests, all passing

**Framework:** Vitest + jsdom + @testing-library/react
**Scripts:** `npm run test` (run once), `npm run test:watch` (watch mode)

**Backend Tests** (`backend/tests/test_e2e_workflow.py`)
- Upload → Search workflow (6 tests)
- Document deletion isolation (4 tests)
- Multiple uploads (2 tests)
- Search edge cases (4 tests)
- API readiness (2 tests)
- Full smoke test (1 test)
- **Total:** 19 E2E tests

**Frontend Tests** (`src/test/e2e-workflow.test.tsx`)
- App startup/loading screen (3 tests)
- PDF upload workflow (4 tests)
- Search results display (5 tests)
- Document deletion (3 tests)
- Full automated smoke test (1 test)
- **Total:** 16 E2E tests

**Coverage**
- Upload workflow with chunking, embedding, persistence
- Semantic search with query embedding and cosine similarity
- Document management (CRUD operations)
- All 6 API endpoints
- All UI components and navigation
- Loading screen health polling
- Data persistence across restarts
- Edge cases and error scenarios

---

**Last Updated:** 2026-03-14
**Project Status:** Phase 07 (End-to-End Testing) Complete
**Overall Status:** ALL PHASES COMPLETE ✓
**Test Count:** 168 tests, all passing
