# Research Index - Mini-RAG Windows App

**Research Phase:** Complete (2026-03-14)
**Location:** `plans/260314-mini-rag-windows-app/research/`

## Navigation

### For Quick Decision-Making
→ **[README.md](research/README.md)** — Overview, stats, critical notes

### For Detailed Technical Reference
→ **[researcher-02-pyinstaller-packaging.md](research/researcher-02-pyinstaller-packaging.md)** — Full technical analysis (730 lines)

### For Quick Lookup
→ **[RESEARCH-SUMMARY.md](research/RESEARCH-SUMMARY.md)** — Key findings table & next steps

### For Implementation Work
→ **[IMPLEMENTATION-CHECKLIST.md](research/IMPLEMENTATION-CHECKLIST.md)** — Step-by-step checklist with code snippets

---

## Summary Table

| Document | Size | Use Case | Time to Read |
|----------|------|----------|--------------|
| README.md | 3KB | Overview & decision making | 5 min |
| RESEARCH-SUMMARY.md | 2KB | Quick reference | 3 min |
| researcher-02-pyinstaller-packaging.md | 19KB | Deep technical dive | 30 min |
| IMPLEMENTATION-CHECKLIST.md | 5KB | Execute the build | 5 min |

---

## Key Findings at a Glance

### 1. Critical PyInstaller Requirements
- ✅ 40+ hidden imports for ChromaDB
- ✅ ONNX Runtime DLL collection via `collect_dynamic_libs()`
- ✅ Pre-bundled fastembed model files (~35MB)
- ✅ `multiprocessing.freeze_support()` in main.py
- ✅ `workers=1` in uvicorn (Windows spawn limitation)

### 2. Expected Challenges
| Issue | Solution | Difficulty |
|-------|----------|-----------|
| ModuleNotFoundError | Add to hiddenimports | Low |
| DLL FileNotFoundError | Use collect_dynamic_libs() | Low |
| Model not found | Use sys._MEIPASS path detection | Medium |
| Spawn loop on Windows | Set workers=1 | Low |
| uvloop incompatible | Switch to winloop | Low |

### 3. Binary Size
- **Base:** 250-350MB
- **Optimized (UPX):** 130-190MB
- **Build time:** 5-10 minutes
- **First troubleshooting:** 1-3 hours typical

---

## Start Here

**Option A: "Just tell me what to do"**
1. Read: `IMPLEMENTATION-CHECKLIST.md` (5 min)
2. Start building with the .spec template

**Option B: "I want to understand the full picture"**
1. Read: `README.md` (5 min)
2. Read: `researcher-02-pyinstaller-packaging.md` (30 min)
3. Reference: `IMPLEMENTATION-CHECKLIST.md` during build

**Option C: "I got an error, what do I do?"**
1. Go to: `RESEARCH-SUMMARY.md` → "Common Failures & Fixes" table
2. Or search: `researcher-02-pyinstaller-packaging.md` → Section 6 "Known Issues"

---

## Adjacent Research

Other mini-rag research documents:
- [researcher-01-tauri-sidecar.md](research/researcher-01-tauri-sidecar.md) — Alternative: Tauri desktop framework

---

**Status:** Research complete and ready for implementation planning

See: `plans/260314-mini-rag-windows-app/plan.md` for full project context
