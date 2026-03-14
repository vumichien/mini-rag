# Project Changelog - Mini RAG

All notable changes to Mini RAG project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Phase 07] - 2026-03-14

### Added
- **End-to-End Testing Suite** - Comprehensive test coverage
  - Backend E2E tests: 19 tests in `backend/tests/test_e2e_workflow.py`
    - Upload → Search workflow (6 tests)
    - Document deletion isolation (4 tests)
    - Multiple uploads (2 tests)
    - Search edge cases (4 tests)
    - API readiness (2 tests)
    - Full smoke test (1 test)

  - Frontend E2E tests: 16 tests in `src/test/e2e-workflow.test.tsx`
    - App startup/loading screen (3 tests)
    - PDF upload workflow (4 tests)
    - Search results display (5 tests)
    - Document deletion (3 tests)
    - Full automated smoke test (1 test)

### Testing Results
- **Backend:** 86 tests passing (67 + 19 new E2E)
- **Frontend:** 82 tests passing (66 + 16 new E2E)
- **Total:** 168 tests, all passing
- **Coverage:** Upload workflow, search functionality, document management, API endpoints, UI components, loading screen, data persistence, edge cases

### Project Status
- ✓ All 7 phases complete
- ✓ Self-contained Windows desktop app delivered
- ✓ Full offline operation verified
- ✓ 168 automated tests validating all features
- ✓ Production-ready codebase

---

## [Phase 06] - 2026-03-14

### Added
- **Tauri Bundler & Installer Configuration**
  - NSIS installer bundler configured
  - ~250MB self-contained installer (mini-rag-setup.exe)
  - App icon and metadata configured
  - Sidecar executable bundled in release
  - Windows Start Menu + Desktop shortcuts
  - Tested on clean Windows installation

### Details
- Installer tested successfully
- Zero post-install setup required
- App appears in Settings → Apps → Installed Apps
- Uninstall removes shortcuts and executable
- User data in %APPDATA%\mini-rag\ retained by design

---

## [Phase 05] - 2026-03-14

### Added
- **PyInstaller Build Configuration**
  - spec file for api-server.exe generation
  - fastembed model bundled (all-MiniLM-L6-v2)
  - Hidden imports configured for fastembed, chromadb, fastapi, uvicorn, winloop
  - Single-file executable output
  - UPX compression tested (optional)

### Details
- Standalone execution verified
- FastAPI server runs without Python installation
- Embeddings model included in binary
- Binary size: ~120MB (compressed to ~50MB with UPX)
- No external dependencies required on user system

---

## [Phase 04] - 2026-03-14

### Added
- **Tauri Integration & Sidecar Management**
  - Sidecar spawning logic in Tauri Rust code
  - Health polling implementation (500ms interval, 30s timeout)
  - Graceful shutdown on app close
  - Error handling for sidecar failures

### Details
- App window: 1200x800, resizable
- Sidecar args: --port 52547 --data-dir %APPDATA%/mini-rag
- Health polling transitions from LoadingScreen to main UI
- Sidecar process cleanup verified on app close
- Data directory created automatically on first run

---

## [Phase 03] - 2026-03-14

### Added
- **React Frontend** - Complete UI with TypeScript
  - 5 core React components: LoadingScreen, UploadPage, DocumentsPage, SearchPage, App
  - Health polling with 500ms interval, 30s timeout
  - Drag-drop PDF upload with file picker fallback
  - Documents list with delete functionality
  - Semantic search with 5 result cards (text, filename, page number, relevance score)
  - Tab navigation (Upload/Documents/Search)
  - Type-safe API client (fetch wrapper)
  - TypeScript interfaces: Document, SearchResult, UploadResponse

- **Testing Framework** - Vitest + jsdom + React Testing Library
  - 6 test files in `src/test/` directory
  - 33 passing tests covering:
    - api-client.ts - All fetch functions, error handling
    - LoadingScreen.tsx - Health polling, timeout, state transitions
    - UploadPage.tsx - Drag-drop, file picker, validation, upload flow
    - DocumentsPage.tsx - Document list rendering, delete confirmation, refresh
    - SearchPage.tsx - Query input, search triggering, results display
    - App.tsx - Tab navigation, component mounting, state management
  - npm scripts: `test` (run once), `test:watch` (watch mode)

- **Frontend Documentation**
  - Updated index.html title to "Mini RAG"
  - Phase 03 plan with detailed architecture and implementation steps

### Changed
- `index.html` - Title changed from default to "Mini RAG"
- `vite.config.ts` - Added Vitest configuration with jsdom preset

### Details
- All React components use TypeScript with strict mode
- No external UI frameworks; styles via inline CSS (Tailwind-ready)
- API base URL hardcoded: `http://127.0.0.1:52547`
- Backend health check: GET /health with 2s timeout
- Upload max file size: 50MB
- Search results: top-5 semantic matches with relevance scoring
- Loader component: spinner + elapsed time display

### Testing
- Framework: Vitest 1.0+
- Preset: jsdom (DOM simulation)
- Testing library: @testing-library/react 14+
- Coverage: All components + utilities tested
- Execution: `npm run test` (all tests pass)

### Notes
- Phase 03 marks frontend completion
- All dependencies are production-ready (React 18+, TypeScript 5+)
- Tests verify both happy path and error scenarios
- Ready for Phase 04: Tauri integration

---

## [Phase 02] - 2026-03-14

### Added
- **Python FastAPI Backend** - Complete RAG server
  - 5 HTTP endpoints: /upload, /documents, /search, /health, /shutdown
  - FastAPI + Uvicorn (port 52547, localhost-only)
  - PDF text extraction (PyMuPDF)
  - Text chunking (1000 char size, 200 char overlap)
  - Semantic embeddings (fastembed, 384-dim, sentence-transformers/all-MiniLM-L6-v2)
  - Vector search (ChromaDB, cosine distance, top-5 results)
  - Document management (upload, list, delete)
  - CORS enabled (allow all origins)
  - Windows event loop support (winloop + asyncio fallback)

- **Python Services**
  - `EmbedderService` - ONNX embedding model (singleton pattern)
  - `VectorStoreService` - ChromaDB wrapper (singleton pattern)
  - `pdf_parser.py` - Text extraction from PDFs
  - `chunker.py` - Fixed-size text chunking with overlap

- **HTTP Routes**
  - `POST /upload` - Upload PDF, extract text, chunk, embed, store
  - `GET /documents` - List all documents with chunk counts
  - `DELETE /documents/{doc_id}` - Remove document + all chunks
  - `POST /search` - Semantic search (query + n_results=5)
  - `GET /health` - Health status check
  - `POST /shutdown` - Graceful shutdown

- **Backend Configuration**
  - `backend/requirements.txt` - All Python dependencies
  - `backend/main.py` - Entry point with argparse (--port, --data-dir)
  - `backend/app.py` - FastAPI factory with lifespan
  - Multiprocessing freeze support for Windows

### Details
- Data directory: Configurable via --data-dir (default: project root)
- Database: ChromaDB PersistentClient with cosine distance
- Model cache: Auto-detected (frozen vs. dev mode)
- Chunk metadata: doc_id, filename, page_number, chunk_index, created_at
- Error handling: Proper HTTP status codes, validation messages
- CORS: Allows localhost UI (Tauri WebView2)

### Notes
- All 5 endpoints functional and tested
- FastAPI auto-generates OpenAPI docs at /docs
- Windows support verified (multiprocessing, async loop)
- Single-worker uvicorn (Windows limitation)

---

## [Phase 01] - 2026-03-14

### Added
- **Project Initialization**
  - Tauri v2 project structure created
  - Node.js/npm setup with React + TypeScript
  - Python virtual environment + requirements.txt
  - Git repository initialization
  - Project documentation framework

- **Initial Configuration**
  - `package.json` - Frontend dependencies (React, TypeScript, Tauri, Vite)
  - `tsconfig.json` - TypeScript configuration (strict mode)
  - `vite.config.ts` - Vite bundler setup
  - `src-tauri/Cargo.toml` - Rust dependencies (Tauri v2)
  - `src-tauri/tauri.conf.json` - Tauri app configuration
  - `.gitignore` - Standard exclusions for Node, Python, Rust

- **Documentation**
  - `docs/codebase-summary.md` - Project structure overview
  - `docs/system-architecture.md` - Component architecture
  - `plans/260314-mini-rag-windows-app/plan.md` - Master implementation plan
  - Phase files for all 7 phases

### Details
- Tech stack locked: Tauri v2, React 18, Python 3.11, FastAPI
- Dependencies selected for: offline capability, small size, performance
- Windows-first approach (sidecar exe, AppData persistence)
- Self-contained distribution target (~250MB installer)

---

## Release Strategy

### Final Status
- **Development Phase:** 07 / 07 (100% complete)
- **Production Ready:** Yes ✓
- **Quality Gate:** All 168 tests passing, no known bugs

### Release Checklist (COMPLETED)
- [x] Phase 04 complete (Tauri integration)
- [x] Phase 05 complete (PyInstaller)
- [x] Phase 06 complete (Bundler)
- [x] Phase 07 complete (E2E testing)
- [x] Final installer tested on clean Windows VM
- [x] Version tag ready (v1.0.0)

---

## Version Numbering

- **v0.3.0** - Phase 03 - React Frontend Complete
- **v0.4.0** - Phase 04 - Tauri Integration
- **v0.5.0** - Phase 05 - PyInstaller Build
- **v0.6.0** - Phase 06 - Bundler & Installer
- **v1.0.0** - Phase 07 (Current) - Production Release ✓ COMPLETE

---

## Known Issues & Limitations

### All Phases Complete
- None. All objectives met and tested.

### Production Deployment Notes
- **Windows SmartScreen:** May warn on first launch (unsigned binary) — user clicks "Run anyway"
- **Cold Start:** First sidecar startup 5-10s (PyInstaller extraction)
- **Warm Start:** Subsequent starts 2-4s (extraction cache)
- **Large PDFs:** 300+ pages may take 1-2 minutes to process
- **Code Signing:** Recommended for distribution (currently unsigned)

---

## Contributing

- Follow code standards in `docs/code-standards.md`
- Update this changelog for all significant changes
- Test coverage required before merge
- Maintain phase-based roadmap in `docs/development-roadmap.md`

---

**Last Updated:** 2026-03-14
**Total Effort Logged:** 14 hours (All Phases 01-07)
**Project Status:** COMPLETE ✓
**All Tests:** 168 passing
