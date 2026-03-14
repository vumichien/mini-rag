---
title: "Mini RAG Windows Desktop App"
description: "Self-contained Windows .exe installer for RAG system: upload PDFs, chunk, embed, search top-5 similar chunks."
status: complete
priority: P1
effort: 14h
issue:
branch: main
tags: [feature, frontend, backend, infra]
created: 2026-03-14
completed: 2026-03-14
---

# Mini RAG Windows Desktop App

## Overview

Build a fully self-contained Windows desktop app for RAG. User installs once (~250MB), no setup required. Click shortcut → app opens → upload PDFs → semantic search over all chunks.

**Stack:** Tauri v2 + React + TypeScript (UI) · Python FastAPI sidecar (PyInstaller) · fastembed ONNX (embedding) · ChromaDB embedded (vector store) · PyMuPDF (PDF parsing)

## Phases

| # | Phase | Status | Effort | Link |
|---|-------|--------|--------|------|
| 1 | Project Setup | Complete | 1h | [phase-01](./phase-01-project-setup.md) |
| 2 | Python Backend | Complete | 3h | [phase-02](./phase-02-python-backend.md) |
| 3 | React Frontend | Complete | 3h | [phase-03](./phase-03-react-frontend.md) |
| 4 | Tauri Integration | Complete | 2h | [phase-04](./phase-04-tauri-integration.md) |
| 5 | PyInstaller Build Config | Complete | 2h | [phase-05](./phase-05-pyinstaller-build.md) |
| 6 | Tauri Bundler & Installer | Complete | 1h | [phase-06](./phase-06-tauri-bundler.md) |
| 7 | End-to-End Testing | Complete | 2h | [phase-07-testing.md](./phase-07-testing.md) |

## Dependencies

- Node.js 18+ · Rust (stable) · Python 3.11 · Tauri CLI v2
- `tauri-plugin-shell = "2"` Cargo dependency
- PyInstaller 6+ · UPX (optional compression)
- fastembed model pre-downloaded before build: `sentence-transformers/all-MiniLM-L6-v2`

## Key Architecture

```
[installer: mini-rag-setup.exe ~250MB]
  └─ Tauri App
       ├─ WebView2 → React UI (localhost:1420 in dev)
       └─ Sidecar: api-server.exe (PyInstaller --onefile)
               ├─ FastAPI + Uvicorn (localhost:52547)
               ├─ fastembed ONNX (bundled model)
               ├─ ChromaDB embedded
               └─ Data: %APPDATA%/mini-rag/
```

## Research

- Tauri sidecar: [researcher-01](./research/researcher-01-tauri-sidecar.md)
- PyInstaller packaging: [researcher-02](./research/researcher-02-pyinstaller-packaging.md)
- Brainstorm report: [brainstorm report](../reports/brainstorm-260314-mini-rag-windows-app.md)
