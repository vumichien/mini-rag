---
type: review
date: 2026-03-14
phase: phase-02-python-backend
score: 8.2/10
---

# Code Review: Phase 02 — Python Backend

## Scope

- Files: `main.py`, `app.py`, `services/embedder.py`, `services/vector_store.py`, `services/pdf_parser.py`, `services/chunker.py`, `routes/upload.py`, `routes/search.py`, `routes/documents.py`, `routes/health.py`
- LOC: ~190 total (all files well under 200-line limit)
- Focus: correctness vs phase-02 spec, Windows/PyInstaller compat, security, edge cases

## Overall Assessment

Implementation is clean, minimal, and faithful to the plan. All 6 required endpoints are present. Windows-critical requirements (`freeze_support`, `workers=1`, `127.0.0.1`) are correctly applied. Code is readable and follows KISS/DRY well. Several medium/high issues need attention before shipping.

---

## Critical Issues

None.

---

## High Priority

### 1. `winloop` import uses wrong event loop policy class

**File:** `main.py` line 13

```python
asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
```

The plan spec shows `winloop.WindowsSelectorEventLoopPolicy()`. The actual class name in the `winloop` package is `winloop.EventLoopPolicy` (it wraps the selector loop internally), so this may be correct — but it differs from the plan example. Verify against the installed `winloop` version to avoid a silent no-op or AttributeError at startup.

**Impact:** If wrong class is used, the event loop may fall back to the default ProactorEventLoop, causing compatibility issues with some async libs on Windows.

### 2. `search` crashes when collection is empty

**File:** `services/vector_store.py` lines 51-58

ChromaDB returns `results["ids"][0]` as an empty list `[]` when no chunks exist — that is handled correctly by the loop. However, if `n_results` is larger than the total number of stored chunks, ChromaDB raises a `ValueError` internally. This will surface as an unhandled 500 to the frontend on a freshly installed app with few documents.

**Fix:** Clamp `n_results` to `min(n_results, total_chunk_count)` before querying, or wrap the query in a try/except returning `[]` on that error.

### 3. `local_files_only=True` will crash on first dev run

**File:** `services/embedder.py` line 18

In development mode the model is expected at `<repo_root>/models/`. If that directory or the model files don't exist, `fastembed` raises immediately because `local_files_only=True` prevents download. There is no README/setup note to run the model download step first, and no fallback.

**Impact:** Silent breakage for any developer cloning the repo fresh. Consider making `local_files_only` conditional: `True` only when frozen, `False` in dev mode, or document the required `python -m fastembed download` step prominently.

---

## Medium Priority

### 4. `upload_pdf` does no filename sanitization

**File:** `routes/upload.py` line 16

```python
if not file.filename.lower().endswith(".pdf"):
```

`file.filename` is attacker-controlled. A path like `../../etc/passwd.pdf` passes the extension check. The filename is stored verbatim as metadata in ChromaDB and returned in API responses. While no file is written to disk here, the unsanitized name could cause issues in future phases (e.g., if Tauri displays or saves with it) and is misleading metadata.

**Fix:** Apply `os.path.basename(file.filename)` before using it.

### 5. `/shutdown` endpoint unauthenticated and responds before killing process

**File:** `routes/health.py` lines 13-17

`POST /shutdown` has no token/secret check. Any process on the machine that can reach `127.0.0.1:52547` can kill the backend. On a shared or multi-user Windows machine this is a DoS vector.

The response `{"status": "shutting down"}` is returned after `os.kill(os.getpid(), signal.SIGTERM)` — on Windows, `SIGTERM` may terminate the process immediately before the response is flushed, leaving the Tauri caller with a connection-reset error rather than the JSON.

**Fix for auth:** Accept a shared secret from `--shutdown-key` arg, require it in the request body.
**Fix for race:** Use `asyncio.get_event_loop().call_later(0.1, lambda: os.kill(...))` to let the response flush first.

### 6. `list_documents` missing `created_at` field required by spec

**File:** `services/vector_store.py` lines 62-75 / `routes/documents.py`

Phase-02 spec: `GET /documents` returns `{id, filename, chunk_count, created_at}`. `created_at` is not stored in chunk metadata and not returned. The frontend (phase 03) will likely expect it.

**Fix:** Store `created_at` (ISO timestamp string) as a metadata field during `add_chunks`, then surface it in `list_documents`.

### 7. `pdf_parser.py` leaks fitz document on exception

**File:** `services/pdf_parser.py` lines 6-13

If `page.get_text()` raises (e.g., corrupted page), `doc.close()` is never called. Use a `try/finally` or `with fitz.open(...) as doc:` (PyMuPDF supports context manager).

### 8. `delete_document` returns 200 even if `doc_id` not found

**File:** `routes/documents.py` lines 13-16

Deleting a non-existent `doc_id` silently returns `{"status": "deleted"}`. Should return 404 to let the frontend show meaningful feedback.

**Fix:** Check `all_ids` is non-empty in `VectorStoreService.delete_document` and raise `HTTPException(404)` if not.

---

## Low Priority

### 9. `chunker.py` — `chunk_index` counts across the whole document loop, not per-call

**File:** `services/chunker.py` / `routes/upload.py` lines 29-31

Each call to `chunk_text` resets `chunk_index` to 0. When multiple pages are chunked, all pages produce `chunk_index` starting at 0. The metadata stored is `{page_number: 3, chunk_index: 0}` etc., which is fine as a (page, chunk_index) composite key, but `chunk_index` in search results will be ambiguous without the page context. Not a bug per the current spec, but worth noting for UI display.

### 10. `requirements.txt` is a full `pip freeze` dump

Includes `pyinstaller`, `build`, `watchfiles`, `kubernetes`, `pefile` and many dev/build tools. Should be split into `requirements.txt` (runtime only) and `requirements-dev.txt` (build tools). The `kubernetes` dependency is surprising — likely a transitive dep of `chromadb`'s optional gRPC support; confirm it is actually needed for the embedded client path.

### 11. `winloop` absent from `requirements.txt`

`winloop` is used in `main.py` but not listed in `requirements.txt`. The `try/except ImportError` fallback means it won't crash, but the Windows event loop optimization will silently not apply if the package isn't installed. Add `winloop` to requirements.

### 12. No input validation on `SearchRequest.query`

**File:** `routes/search.py` lines 10-12

Empty string `""` or very long query (10k+ chars) will be embedded without error. An empty embedding is semantically meaningless. Add `query: str = Field(..., min_length=1, max_length=2000)`.

### 13. `EmbedderService.initialize()` is synchronous but called from async lifespan

`fastembed` model loading can take 1-5s. It blocks the event loop during startup. For `workers=1` this is acceptable, but worth a comment explaining the deliberate choice.

---

## Positive Observations

- `freeze_support()` is the absolute first line before any imports — correct and important.
- `127.0.0.1` binding enforced — no exposure risk.
- `workers=1` with comment — clear rationale preserved.
- `factory=True` pattern with `create_app` is clean and testable.
- `local_files_only=True` intent is correct for production bundle; model cache path via `sys._MEIPASS` is the right approach.
- `anonymized_telemetry=False` on ChromaDB — good privacy default.
- File size checked after read (not stream-based) — acceptable given 50MB limit and local-only context.
- Cosine similarity score conversion (`1 - distance`) is correct for HNSW cosine space.
- All files well under 200-line limit.
- Extension check uses `.lower()` — handles `file.PDF` correctly.

---

## Todo List Completion Check (phase-02-python-backend.md)

| Task | Status |
|------|--------|
| `backend/main.py` with freeze_support, winloop, argparse | Done |
| `backend/app.py` with lifespan, CORS, routers | Done |
| `backend/services/embedder.py` with frozen-path logic | Done |
| `backend/services/vector_store.py` with ChromaDB embedded | Done (named `vector_store.py`, plan says `vector-store.py`) |
| `backend/services/pdf_parser.py` with PyMuPDF | Done (named `pdf_parser.py`, plan says `pdf-parser.py`) |
| `backend/services/chunker.py` | Done |
| `backend/routes/upload.py` | Done |
| `backend/routes/search.py` | Done |
| `backend/routes/documents.py` | Done |
| `backend/routes/health.py` with /shutdown | Done |
| Test endpoints with uvicorn | Not verified (runtime test) |
| Verify ChromaDB persists across restarts | Not verified |

Note: File naming uses `snake_case` (`pdf_parser.py`, `vector_store.py`) instead of the plan's `kebab-case` (`pdf-parser.py`, `vector-store.py`). Snake_case is correct for Python modules — the plan naming was aspirational/docs-only. No action needed.

---

## Recommended Actions (prioritized)

1. **[High]** Fix `local_files_only` dev/prod split or document model download step.
2. **[High]** Guard `VectorStoreService.search` against `n_results > collection size` error.
3. **[Medium]** Add `created_at` to chunk metadata and `list_documents` response.
4. **[Medium]** Sanitize `file.filename` with `os.path.basename`.
5. **[Medium]** Fix `/shutdown` race condition (defer kill) and add basic auth token.
6. **[Medium]** Return 404 from `DELETE /documents/{doc_id}` when not found.
7. **[Medium]** Wrap `fitz.open` in try/finally or context manager.
8. **[Low]** Add `winloop` to `requirements.txt`.
9. **[Low]** Add `Field(min_length=1, max_length=2000)` to `SearchRequest.query`.
10. **[Low]** Split `requirements.txt` into runtime vs dev dependencies.

---

## Score: 8.2 / 10

Deductions: missing `created_at` field (-0.5), unguarded empty-collection search crash (-0.5), `local_files_only` dev UX breakage (-0.5), unauthenticated shutdown (-0.3).

## Unresolved Questions

- Is `winloop.EventLoopPolicy()` the correct class name in the installed version, or should it be `winloop.WindowsSelectorEventLoopPolicy()`? Verify with `python -c "import winloop; print(dir(winloop))"`.
- Is `kubernetes` actually required at runtime for ChromaDB's embedded (non-HTTP) client, or is it a transitive dep that can be excluded from the PyInstaller bundle?
- Should `created_at` be stored at chunk level or tracked separately (e.g., a doc registry)? Chunk-level is simplest given the current ChromaDB-only storage strategy.
