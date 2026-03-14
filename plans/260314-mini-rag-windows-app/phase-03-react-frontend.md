# Phase 03: React Frontend

**Context:** [plan.md](./plan.md) · [phase-02](./phase-02-python-backend.md)

## Overview

- **Priority:** P1
- **Status:** Complete
- **Effort:** 3h
- **Description:** Build React + TypeScript UI with 3 views: Upload, Documents, Search. Includes loading screen that polls /health until backend is ready.

## Key Insights

- Backend URL is hardcoded: `http://127.0.0.1:52547` (fixed port, simplest approach)
- Loading screen MUST show while sidecar starts (3-8s cold start)
- Health polling: retry every 500ms, timeout after 30s
- UI is inside Tauri WebView2 — no browser security restrictions (localhost is allowed)
- Keep UI simple: 3 tabs, drag-drop upload, result cards

## Requirements

**Functional:**
- Loading screen: spinner + "Starting up..." while health check pending
- Upload tab: drag-drop or file picker for PDFs, upload progress
- Documents tab: list uploaded docs, delete button per doc
- Search tab: text input, search button, 5 result cards with text/source
- Toast/alert for errors

**Non-functional:**
- No UI framework (plain Tailwind or CSS modules) — avoid heavy deps
- TypeScript strict mode
- Mobile-friendly layout not required (desktop app)

## Architecture

```
src/
├── main.tsx                    # App mount
├── App.tsx                     # Router: LoadingScreen → MainApp
├── lib/
│   └── api-client.ts          # All fetch calls to FastAPI
├── components/
│   ├── LoadingScreen.tsx       # Spinner + health polling
│   ├── NavBar.tsx              # Tab navigation
│   ├── UploadPage.tsx          # PDF drag-drop + upload
│   ├── DocumentsPage.tsx       # Doc list + delete
│   └── SearchPage.tsx          # Query + results
└── types.ts                    # Shared TypeScript types
```

## Related Code Files

- Create: all files in `src/`
- Modify: `src/App.tsx` (replace Tauri default)
- Modify: `index.html` title → "Mini RAG"

## Implementation Steps

### Step 1: types.ts

```typescript
// src/types.ts
export interface Document {
  doc_id: string;
  filename: string;
  chunk_count: number;
}

export interface SearchResult {
  text: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  score: number;
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  chunk_count: number;
}
```

### Step 2: api-client.ts

```typescript
// src/lib/api-client.ts
const API_BASE = "http://127.0.0.1:52547";

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function uploadPDF(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`);
  const data = await res.json();
  return data.documents;
}

export async function deleteDocument(doc_id: string): Promise<void> {
  await fetch(`${API_BASE}/documents/${doc_id}`, { method: "DELETE" });
}

export async function search(query: string): Promise<SearchResult[]> {
  const res = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, n_results: 5 }),
  });
  const data = await res.json();
  return data.results;
}
```

### Step 3: LoadingScreen.tsx

```typescript
// src/components/LoadingScreen.tsx
import { useEffect, useState } from "react";
import { checkHealth } from "../lib/api-client";

interface Props { onReady: () => void; }

export function LoadingScreen({ onReady }: Props) {
  const [status, setStatus] = useState("Starting up...");
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(async () => {
      const secs = Math.floor((Date.now() - start) / 1000);
      setElapsed(secs);

      if (secs > 30) {
        setStatus("Startup timeout. Please restart the app.");
        clearInterval(interval);
        return;
      }

      const ok = await checkHealth();
      if (ok) {
        clearInterval(interval);
        onReady();
      } else {
        setStatus(`Starting up... (${secs}s)`);
      }
    }, 500);
    return () => clearInterval(interval);
  }, [onReady]);

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", height: "100vh", gap: "16px" }}>
      <div className="spinner" />
      <p>{status}</p>
    </div>
  );
}
```

### Step 4: UploadPage.tsx

```typescript
// src/components/UploadPage.tsx
import { useState, useCallback } from "react";
import { uploadPDF } from "../lib/api-client";

export function UploadPage({ onUploaded }: { onUploaded: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");

  const handleFile = useCallback(async (file: File) => {
    if (!file.name.endsWith(".pdf")) {
      setMessage("Only PDF files are supported.");
      return;
    }
    setUploading(true);
    setMessage("Uploading and processing...");
    try {
      const result = await uploadPDF(file);
      setMessage(`✓ "${result.filename}" uploaded. ${result.chunk_count} chunks created.`);
      onUploaded();
    } catch (err) {
      setMessage(`Error: ${err}`);
    } finally {
      setUploading(false);
    }
  }, [onUploaded]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  return (
    <div>
      <h2>Upload PDF</h2>
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        style={{ border: "2px dashed #ccc", padding: "40px", textAlign: "center",
                 cursor: "pointer", borderRadius: "8px" }}
        onClick={() => document.getElementById("file-input")?.click()}
      >
        <p>Drag & drop a PDF here, or click to select</p>
        <input
          id="file-input" type="file" accept=".pdf" style={{ display: "none" }}
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>
      {uploading && <p>Processing...</p>}
      {message && <p>{message}</p>}
    </div>
  );
}
```

### Step 5: DocumentsPage.tsx

```typescript
// src/components/DocumentsPage.tsx
import { useEffect, useState } from "react";
import { getDocuments, deleteDocument } from "../lib/api-client";
import type { Document } from "../types";

export function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);

  const load = async () => setDocs(await getDocuments());
  useEffect(() => { load(); }, []);

  const handleDelete = async (doc_id: string) => {
    if (!confirm("Delete this document and all its chunks?")) return;
    await deleteDocument(doc_id);
    await load();
  };

  return (
    <div>
      <h2>Documents ({docs.length})</h2>
      {docs.length === 0 && <p>No documents uploaded yet.</p>}
      <ul>
        {docs.map((doc) => (
          <li key={doc.doc_id} style={{ display: "flex", justifyContent: "space-between",
                                        padding: "8px 0", borderBottom: "1px solid #eee" }}>
            <span>{doc.filename} <small>({doc.chunk_count} chunks)</small></span>
            <button onClick={() => handleDelete(doc.doc_id)}>Delete</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

### Step 6: SearchPage.tsx

```typescript
// src/components/SearchPage.tsx
import { useState } from "react";
import { search } from "../lib/api-client";
import type { SearchResult } from "../types";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      setResults(await search(query));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Search</h2>
      <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Ask a question..."
          style={{ flex: 1, padding: "8px" }}
        />
        <button onClick={handleSearch} disabled={loading}>
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
      {results.map((r, i) => (
        <div key={i} style={{ border: "1px solid #ddd", borderRadius: "8px",
                              padding: "12px", marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "#888", marginBottom: "8px" }}>
            {r.filename} · Page {r.page_number} · Score: {(r.score * 100).toFixed(1)}%
          </div>
          <p style={{ margin: 0 }}>{r.text}</p>
        </div>
      ))}
    </div>
  );
}
```

### Step 7: App.tsx

```typescript
// src/App.tsx
import { useState } from "react";
import { LoadingScreen } from "./components/LoadingScreen";
import { UploadPage } from "./components/UploadPage";
import { DocumentsPage } from "./components/DocumentsPage";
import { SearchPage } from "./components/SearchPage";

type Tab = "upload" | "documents" | "search";

export function App() {
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<Tab>("upload");
  const [refreshDocs, setRefreshDocs] = useState(0);

  if (!ready) return <LoadingScreen onReady={() => setReady(true)} />;

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "16px" }}>
      <h1>Mini RAG</h1>
      <nav style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {(["upload", "documents", "search"] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
                  style={{ fontWeight: tab === t ? "bold" : "normal" }}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>
      {tab === "upload" && <UploadPage onUploaded={() => setRefreshDocs(r => r + 1)} />}
      {tab === "documents" && <DocumentsPage key={refreshDocs} />}
      {tab === "search" && <SearchPage />}
    </div>
  );
}
```

## Todo List

- [x] Create `src/types.ts`
- [x] Create `src/lib/api-client.ts` with all fetch functions
- [x] Create `src/components/LoadingScreen.tsx` with health polling
- [x] Create `src/components/UploadPage.tsx` with drag-drop
- [x] Create `src/components/DocumentsPage.tsx` with delete
- [x] Create `src/components/SearchPage.tsx` with result cards
- [x] Create `src/App.tsx` with tab navigation
- [x] Update `index.html` title
- [x] Test UI against live FastAPI backend (from phase 2)
- [x] Verify loading screen transitions to main UI when backend ready
- [x] Set up Vitest + jsdom + @testing-library/react testing framework
- [x] Create 6 test files with 33 passing tests

## Success Criteria

- Loading screen shows while backend starts
- PDF upload works (file picker + drag-drop)
- Documents list shows uploaded files
- Search returns 5 result cards with source info
- All transitions are smooth, no broken state

## Risk Assessment

- **CORS**: FastAPI allows `*` — no issue from Tauri WebView2
- **Loading screen timeout**: 30s should be sufficient even for slow machines

## Next Steps

→ Phase 4: Tauri integration (sidecar spawn, AppData path, shutdown)
