# Phase 02: Python Backend

**Context:** [plan.md](./plan.md) · [PyInstaller research](./research/researcher-02-pyinstaller-packaging.md)

## Overview

- **Priority:** P1
- **Status:** Complete
- **Effort:** 3h (completed)
- **Description:** Implement FastAPI backend with PDF parsing, chunking, embedding, ChromaDB storage, and search endpoints. All Windows-compatible (winloop, workers=1, freeze_support).

## Key Insights

- `multiprocessing.freeze_support()` MUST be at top of main.py (Windows + PyInstaller requirement)
- `workers=1` in uvicorn.run() — Windows spawn mode causes loop with workers>1
- `winloop` replaces `uvloop` (incompatible with Windows)
- fastembed model path must use `sys._MEIPASS` when frozen
- ChromaDB persistent dir must go to `%APPDATA%/mini-rag/chroma/`
- Sidecar receives `--data-dir` arg from Tauri with AppData path

## Requirements

**Functional:**
- POST /upload: accept PDF, parse, chunk, embed, store
- GET /documents: list all docs (id, filename, chunk_count, created_at)
- DELETE /documents/{doc_id}: remove doc + all its chunks
- POST /search: embed query, top-5 ChromaDB search, return chunks with metadata
- GET /health: simple 200 OK for startup polling
- POST /shutdown: graceful exit (for Tauri kill signal)

**Non-functional:**
- All endpoints return JSON
- Max PDF size: 50MB
- Chunking: 1000 chars, 200 char overlap
- Search returns: [{text, filename, page_number, chunk_index, score}]

## Architecture

### Data Flow

```
Upload:
POST /upload (multipart PDF)
  → PyMuPDF: extract text per page
  → chunker: split 1000 chars, 200 overlap
  → fastembed: encode each chunk → vector[384]
  → ChromaDB: store(vectors, docs metadata)
  → return {doc_id, chunk_count}

Search:
POST /search {query: str}
  → fastembed: encode query → vector[384]
  → ChromaDB: query(n_results=5)
  → return [{text, filename, page_number, chunk_index, score}]
```

### File Structure

```
backend/
├── main.py                     # Entry: freeze_support, uvicorn.run
├── app.py                      # FastAPI app instance + lifespan
├── routes/
│   ├── upload.py               # POST /upload
│   ├── documents.py            # GET /documents, DELETE /documents/{id}
│   ├── search.py               # POST /search
│   └── health.py               # GET /health, POST /shutdown
└── services/
    ├── pdf-parser.py           # PyMuPDF text extraction
    ├── chunker.py              # Fixed-size chunking with overlap
    ├── embedder.py             # fastembed singleton
    └── vector-store.py         # ChromaDB client singleton
```

## Related Code Files

- Create: `backend/main.py`
- Create: `backend/app.py`
- Create: `backend/routes/upload.py`
- Create: `backend/routes/documents.py`
- Create: `backend/routes/search.py`
- Create: `backend/routes/health.py`
- Create: `backend/services/pdf-parser.py`
- Create: `backend/services/chunker.py`
- Create: `backend/services/embedder.py`
- Create: `backend/services/vector-store.py`

## Implementation Steps

### Step 1: main.py — Entry Point

```python
# backend/main.py
import multiprocessing
multiprocessing.freeze_support()  # MUST be first — Windows + PyInstaller

import sys
import os
import argparse
import uvicorn

if sys.platform == "win32":
    import winloop
    asyncio.set_event_loop_policy(winloop.WindowsSelectorEventLoopPolicy())

def get_data_dir() -> str:
    """Get data directory from --data-dir arg or default to AppData."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--port", type=int, default=52547)
    args, _ = parser.parse_known_args()

    if args.data_dir:
        return args.data_dir

    # Fallback: APPDATA/mini-rag
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "mini-rag")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--port", type=int, default=52547)
    args, _ = parser.parse_known_args()

    data_dir = get_data_dir()
    os.environ["MINI_RAG_DATA_DIR"] = data_dir
    os.makedirs(data_dir, exist_ok=True)

    uvicorn.run(
        "app:create_app",
        factory=True,
        host="127.0.0.1",
        port=args.port,
        workers=1,       # MUST be 1 on Windows with PyInstaller
        reload=False,
        log_level="info",
    )
```

### Step 2: app.py — FastAPI App

```python
# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.embedder import EmbedderService
from services.vector_store import VectorStoreService
from routes import upload, documents, search, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: init services
    EmbedderService.initialize()
    VectorStoreService.initialize()
    yield
    # Shutdown cleanup if needed

def create_app() -> FastAPI:
    app = FastAPI(title="Mini RAG API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(upload.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(health.router)
    return app
```

### Step 3: services/embedder.py

```python
# backend/services/embedder.py
import sys
import os
from pathlib import Path
from fastembed import TextEmbedding

class EmbedderService:
    _instance: "EmbedderService" = None
    _model: TextEmbedding = None

    @classmethod
    def initialize(cls):
        if cls._model is None:
            cache_dir = cls._get_model_cache_dir()
            cls._model = TextEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                cache_dir=str(cache_dir),
                local_files_only=True,  # Offline — no network calls
            )

    @classmethod
    def _get_model_cache_dir(cls) -> Path:
        if getattr(sys, "frozen", False):
            # Running in PyInstaller bundle
            return Path(sys._MEIPASS) / "fastembed_models"
        else:
            # Development mode
            return Path(__file__).parent.parent.parent / "models"

    @classmethod
    def embed(cls, texts: list[str]) -> list[list[float]]:
        if cls._model is None:
            cls.initialize()
        return [v.tolist() for v in cls._model.embed(texts)]
```

### Step 4: services/vector-store.py

```python
# backend/services/vector_store.py
import os
import chromadb
from chromadb.config import Settings

class VectorStoreService:
    _client: chromadb.Client = None
    _collection = None
    COLLECTION_NAME = "rag_chunks"

    @classmethod
    def initialize(cls):
        data_dir = os.environ.get("MINI_RAG_DATA_DIR", ".")
        chroma_dir = os.path.join(data_dir, "chroma")
        os.makedirs(chroma_dir, exist_ok=True)

        cls._client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        cls._collection = cls._client.get_or_create_collection(
            name=cls.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    @classmethod
    def add_chunks(cls, doc_id: str, chunks: list[dict], embeddings: list[list[float]]):
        """chunks: [{text, filename, page_number, chunk_index}]"""
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        docs = [c["text"] for c in chunks]
        metadatas = [{"doc_id": doc_id, "filename": c["filename"],
                      "page_number": c["page_number"], "chunk_index": c["chunk_index"]}
                     for c in chunks]
        cls._collection.add(ids=ids, embeddings=embeddings,
                            documents=docs, metadatas=metadatas)

    @classmethod
    def search(cls, query_embedding: list[float], n_results: int = 5) -> list[dict]:
        results = cls._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "text": results["documents"][0][i],
                "filename": results["metadatas"][0][i]["filename"],
                "page_number": results["metadatas"][0][i]["page_number"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "score": 1 - results["distances"][0][i],  # cosine similarity
            })
        return output

    @classmethod
    def list_documents(cls) -> list[dict]:
        """Return unique documents with chunk counts."""
        all_items = cls._collection.get(include=["metadatas"])
        docs = {}
        for meta in all_items["metadatas"]:
            doc_id = meta["doc_id"]
            if doc_id not in docs:
                docs[doc_id] = {"doc_id": doc_id, "filename": meta["filename"], "chunk_count": 0}
            docs[doc_id]["chunk_count"] += 1
        return list(docs.values())

    @classmethod
    def delete_document(cls, doc_id: str):
        all_ids = cls._collection.get(where={"doc_id": doc_id})["ids"]
        if all_ids:
            cls._collection.delete(ids=all_ids)
```

### Step 5: services/pdf-parser.py

```python
# backend/services/pdf_parser.py
import fitz  # PyMuPDF

def extract_pages(pdf_bytes: bytes) -> list[dict]:
    """Returns [{page_number, text}]"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page_number": i + 1, "text": text})
    doc.close()
    return pages
```

### Step 6: services/chunker.py

```python
# backend/services/chunker.py

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def chunk_text(text: str, filename: str, page_number: int) -> list[dict]:
    """Fixed-size chunks with overlap."""
    chunks = []
    start = 0
    chunk_index = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "text": chunk_text,
                "filename": filename,
                "page_number": page_number,
                "chunk_index": chunk_index,
            })
        start += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_index += 1
    return chunks
```

### Step 7: routes/upload.py

```python
# backend/routes/upload.py
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.pdf_parser import extract_pages
from services.chunker import chunk_text
from services.embedder import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()

@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    doc_id = str(uuid.uuid4())
    pages = extract_pages(pdf_bytes)
    if not pages:
        raise HTTPException(status_code=422, detail="No extractable text in PDF")

    all_chunks = []
    for page in pages:
        all_chunks.extend(chunk_text(page["text"], file.filename, page["page_number"]))

    embeddings = EmbedderService.embed([c["text"] for c in all_chunks])
    VectorStoreService.add_chunks(doc_id, all_chunks, embeddings)

    return {"doc_id": doc_id, "filename": file.filename, "chunk_count": len(all_chunks)}
```

### Step 8: routes/search.py

```python
# backend/routes/search.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.embedder import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    n_results: int = 5

@router.post("/search")
async def search(req: SearchRequest):
    embedding = EmbedderService.embed([req.query])[0]
    results = VectorStoreService.search(embedding, n_results=req.n_results)
    return {"results": results}
```

### Step 9: routes/documents.py + health.py

```python
# backend/routes/documents.py
from fastapi import APIRouter, HTTPException
from services.vector_store import VectorStoreService

router = APIRouter()

@router.get("/documents")
async def list_documents():
    return {"documents": VectorStoreService.list_documents()}

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    VectorStoreService.delete_document(doc_id)
    return {"status": "deleted", "doc_id": doc_id}
```

```python
# backend/routes/health.py
import os
import signal
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.post("/shutdown")
async def shutdown():
    """Graceful shutdown — called by Tauri before app closes."""
    os.kill(os.getpid(), signal.SIGTERM)
    return {"status": "shutting down"}
```

## Todo List

- [x] Create `backend/main.py` with `freeze_support`, winloop, argparse
- [x] Create `backend/app.py` with FastAPI lifespan, CORS, routers
- [x] Create `backend/services/embedder.py` with frozen-path logic
- [x] Create `backend/services/vector-store.py` with ChromaDB embedded
- [x] Create `backend/services/pdf-parser.py` with PyMuPDF
- [x] Create `backend/services/chunker.py` (1000 chars, 200 overlap)
- [x] Create `backend/routes/upload.py`
- [x] Create `backend/routes/search.py`
- [x] Create `backend/routes/documents.py`
- [x] Create `backend/routes/health.py` with /shutdown
- [x] Test all endpoints with `uvicorn app:create_app --factory --port 52547`
- [x] Verify ChromaDB persists across restarts

## Success Criteria

- All 6 endpoints return correct JSON
- Upload 1 PDF → ChromaDB persists chunks
- Search returns ≤5 results with score, filename, page_number
- Restart server → previous data still searchable

## Risk Assessment

- **ChromaDB collection schema**: Keep `doc_id`, `filename`, `page_number`, `chunk_index` as metadata keys
- **fastembed first run**: Downloads model if not in cache — in dev mode only, bundled mode uses `sys._MEIPASS`
- **Large PDF chunking**: 500-page PDF could produce 5000+ chunks, embedding takes time

## Security Considerations

- Listen only on `127.0.0.1` (not 0.0.0.0) — local only
- File size limit: 50MB
- CORS: allow `*` (only local UI connects)

## Next Steps

→ Phase 3: React frontend
