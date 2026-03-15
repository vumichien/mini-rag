# Mini RAG — Local PDF Semantic Search

A self-contained desktop app for Windows and macOS. Upload PDFs → search them semantically with local AI embeddings. No internet required after setup.

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

**Windows:**
```bat
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cd ..
```

**macOS/Linux:**
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ..
```

### 3. Download the embedding model

The app uses `sentence-transformers/all-MiniLM-L6-v2` via fastembed. Download it once into `models/`:

**Windows:**
```bat
cd backend
.venv\Scripts\python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='../models')"
cd ..
```

**macOS/Linux:**
```bash
cd backend
.venv/bin/python3 -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='../models')"
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

**Windows:**
```bat
cd backend
.venv\Scripts\python main.py --port 52547
```

**macOS/Linux:**
```bash
cd backend
.venv/bin/python3 main.py --port 52547
```

The app's loading screen polls `/health` every 500ms until the backend responds.

---

## Configuration

No `.env` or config files needed. The app uses these defaults:

| Setting | Default | Override |
|---------|---------|----------|
| API port | `52547` | `python main.py --port <port>` |
| Data directory | Windows: `%APPDATA%\mini-rag\` · macOS: `~/Library/Application Support/mini-rag/` | `python main.py --data-dir <path>` |
| Embedding model | `all-MiniLM-L6-v2` | Hardcoded in `backend/services/embedder.py` |
| Frontend API base | `http://127.0.0.1:52547` | Hardcoded in `src/lib/api-client.ts` |

ChromaDB data (vectors + metadata) is persisted in the platform data directory (`%APPDATA%\mini-rag\chroma\` on Windows, `~/Library/Application Support/mini-rag/chroma/` on macOS) and survives app restarts.

---

## Building the Production Installer

### Option A — Full build in one step

**Windows:**
```bat
scripts\build-all.bat
```
Output: `src-tauri\target\release\bundle\nsis\mini-rag_x.x.x_x64-setup.exe`

**macOS:**
```bash
bash scripts/build-all.sh
```
Output: `src-tauri/target/release/bundle/dmg/mini-rag_x.x.x_x64.dmg`

### Option B — Step by step

**Step 1: Build the Python backend sidecar**

Windows:
```bat
cd backend
build.bat
```

macOS:
```bash
cd backend
bash build.sh
```

This runs PyInstaller using `api-server.spec`, producing `src-tauri/binaries/api-server-<target-triple>` (~200MB bundled with model + ChromaDB).

**Step 2: Build Tauri + React**

```bash
npm run tauri build
```

> **Requirements for build:**
> - Rust toolchain must be installed (`rustup`)
> - The `models/` directory must exist with the downloaded model (Step 3 above)
> - Python venv must exist at `backend/.venv` (or `backend\.venv` on Windows)

---

## Running Tests

### Frontend tests

```bash
npm test
```

### Backend tests

**Windows:**
```bat
cd backend
.venv\Scripts\python -m pytest tests/ -v
```

**macOS/Linux:**
```bash
cd backend
.venv/bin/python3 -m pytest tests/ -v
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
[Installer ~250MB]
  └─ Tauri App (mini-rag / mini-rag.exe)
       ├─ WebView2/WebKit → React UI
       └─ Sidecar: api-server (PyInstaller)
               ├─ FastAPI + Uvicorn  (127.0.0.1:52547)
               ├─ fastembed ONNX     (bundled model)
               ├─ ChromaDB embedded  (local vector store)
               └─ Data: platform app-data dir
```

## Known Limitations

- **Windows SmartScreen** may warn on first launch (unsigned binary) → click "More info" → "Run anyway"
- **macOS Gatekeeper** may block on first launch (unsigned binary) → System Settings → Privacy & Security → "Open Anyway"
- **Cold start:** First launch takes 8–15s (PyInstaller extraction). Subsequent starts: 2–4s
- **Very large PDFs** (300+ pages): processing may take 1–2 minutes
