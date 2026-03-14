# Mini RAG — Local PDF Semantic Search

A self-contained Windows desktop app. Upload PDFs → search them semantically with local AI embeddings. No internet required after setup.

**Stack:** Tauri v2 · React + TypeScript · Python FastAPI sidecar · fastembed (ONNX) · ChromaDB · PyMuPDF

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Node.js | 18+ | |
| Rust (stable) | latest | `rustup install stable` |
| Python | 3.11+ | |
| Tauri CLI v2 | latest | `npm install -g @tauri-apps/cli` |

---

## Local Development

### 1. Install Node dependencies

```bash
npm install
```

### 2. Set up Python backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

### 3. Download the embedding model

The app uses `sentence-transformers/all-MiniLM-L6-v2` via fastembed. Download it once into `models/`:

```bash
cd backend
.venv\Scripts\python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='../models')"
cd ..
```

> **Note:** This downloads ~90MB into `models/`. The `models/` directory is required for both dev mode and PyInstaller builds.

### 4. Run in development mode

In development, Tauri starts the React frontend (Vite on port 1420) and launches the Python sidecar separately. Run:

```bash
npm run tauri dev
```

Tauri will:
- Start Vite dev server at `http://localhost:1420`
- Compile and launch the Tauri shell
- The app expects the Python API at `http://127.0.0.1:52547`

> **Note:** In dev mode, the Python sidecar is **not** auto-started by Tauri (it's only bundled in the production build). Start it manually in a separate terminal:

```bash
cd backend
.venv\Scripts\python main.py --port 52547
```

The app's loading screen polls `/health` every 500ms until the backend responds.

---

## Configuration

No `.env` or config files needed. The app uses these defaults:

| Setting | Default | Override |
|---------|---------|----------|
| API port | `52547` | `python main.py --port <port>` |
| Data directory | `%APPDATA%\mini-rag\` | `python main.py --data-dir <path>` |
| Embedding model | `all-MiniLM-L6-v2` | Hardcoded in `backend/services/embedder.py` |
| Frontend API base | `http://127.0.0.1:52547` | Hardcoded in `src/lib/api-client.ts` |

ChromaDB data (vectors + metadata) is persisted in `%APPDATA%\mini-rag\chroma\` and survives app restarts.

---

## Building the Production Installer

### Option A — Full build in one step

```bat
scripts\build-all.bat
```

This runs both steps below in sequence. Output: `src-tauri\target\release\bundle\nsis\mini-rag_x.x.x_x64-setup.exe`

### Option B — Step by step

**Step 1: Build the Python backend sidecar**

```bat
cd backend
build.bat
```

This runs PyInstaller using `api-server.spec`, producing `src-tauri\binaries\api-server-<target-triple>.exe` (~200MB bundled with model + ChromaDB).

**Step 2: Build Tauri + React**

```bash
npm run tauri build
```

Output installer: `src-tauri\target\release\bundle\nsis\mini-rag_x.x.x_x64-setup.exe`

> **Requirements for build:**
> - Rust toolchain must be installed (`rustup`)
> - The `models/` directory must exist with the downloaded model (Step 3 above)
> - Python venv must exist at `backend\.venv`

---

## Running Tests

### Frontend tests

```bash
npm test
```

### Backend tests

```bash
cd backend
.venv\Scripts\python -m pytest tests/ -v
```

> Tests use a temporary ChromaDB directory and the pre-downloaded model in `models/`. No running server needed.

---

## Project Structure

```
mini-rag/
├── src/                    # React + TypeScript frontend
│   ├── components/         # UploadPage, SearchPage, DocumentsPage, LoadingScreen
│   ├── lib/api-client.ts   # HTTP client → Python API
│   └── test/               # Vitest unit + E2E tests
├── backend/                # Python FastAPI sidecar
│   ├── app.py              # FastAPI app factory
│   ├── main.py             # Entry point (uvicorn)
│   ├── routes/             # upload, search, documents, health
│   ├── services/           # pdf_parser, chunker, embedder, vector_store
│   └── tests/              # pytest unit + E2E tests
├── models/                 # fastembed ONNX model (git-ignored, download once)
├── src-tauri/              # Tauri shell + Rust config
│   └── binaries/           # Built api-server-<triple>.exe goes here
└── scripts/
    └── build-all.bat       # Full build pipeline
```

---

## Architecture

```
[Windows Installer ~250MB]
  └─ Tauri App (mini-rag.exe)
       ├─ WebView2 → React UI
       └─ Sidecar: api-server.exe (PyInstaller)
               ├─ FastAPI + Uvicorn  (127.0.0.1:52547)
               ├─ fastembed ONNX     (bundled model)
               ├─ ChromaDB embedded  (local vector store)
               └─ Data: %APPDATA%\mini-rag\
```

## Known Limitations

- **Windows SmartScreen** may warn on first launch (unsigned binary) → click "More info" → "Run anyway"
- **Cold start:** First launch takes 8–15s (PyInstaller extraction). Subsequent starts: 2–4s
- **Very large PDFs** (300+ pages): processing may take 1–2 minutes
