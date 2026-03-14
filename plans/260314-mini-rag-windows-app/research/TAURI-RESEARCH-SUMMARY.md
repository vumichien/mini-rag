# Tauri v2 Sidecar Integration Research Summary

**Research Completed:** 2026-03-14
**Primary Document:** `researcher-01-tauri-sidecar.md` (618 lines)
**Quick Reference:** `RESEARCH-FINDINGS.md`
**Domain:** Tauri v2 Python sidecar integration for Windows

---

## Overview

Successfully researched and documented complete integration pattern for bundling a PyInstaller-compiled Python executable as a Tauri v2 sidecar on Windows. Report covers configuration, binary naming, Rust API, lifecycle management, and Windows-specific gotchas.

---

## Key Deliverables

### 1. Configuration Files
- **tauri.conf.json** snippet with `bundle.externalBin` array
- **Cargo.toml** dependencies (`tauri-plugin-shell = "2"`)
- **src-tauri/capabilities/default.json** with `shell:allow-execute` permission

### 2. Binary Naming Convention
- Pattern: `<name>-<target-triple><.exe>`
- Windows x64 (MSVC): `api-server-x86_64-pc-windows-msvc.exe`
- Windows x32 (MSVC): `api-server-i686-pc-windows-msvc.exe`
- Discovery command: `rustc --print host`

### 3. Rust Implementation
- Complete code examples for spawning sidecar with `tauri_plugin_shell::ShellExt`
- Pattern for storing child process in `Arc<Mutex<>>` for lifecycle management
- Output handling via `CommandEvent::Stdout` and `CommandEvent::Stderr`
- Graceful shutdown implementation (avoiding kill() on one-file PyInstaller)

### 4. Port/Config Communication
- **Pattern 1:** Hardcoded `localhost:8008` (simplest)
- **Pattern 2:** Rust command returns port to frontend
- **Pattern 3:** Config file written by Python sidecar
- **Pattern 4:** Environment variable at build time (static)

### 5. Windows-Specific Gotchas
| Issue | Root Cause | Mitigation |
|---|---|---|
| Antivirus prompts | PyInstaller heuristic scanning | Code-sign binaries, build reputation |
| Permission denied | Sidecar writes to protected dirs | Use AppData/AppConfig only |
| Path not found | Target triple mismatch | Match `rustc --print host` output |
| Cannot kill process | One-file PyInstaller bootloader | Use stdin signal or multi-file mode |
| .exe not found | Backslashes in JSON | Use forward slashes consistently |

### 6. Tauri v1 vs v2 Breaking Changes
- Config: `allowlist.externalBin` → `bundle.externalBin`
- Rust API: `Command::new_sidecar()` → `app.shell().sidecar()`
- Permissions: Allowlist → Capability system (ACL with permission files)
- Feature flag: `process-command-api` → removed (not needed in v2)

---

## Critical Implementation Steps

1. **Build PyInstaller binary:**
   ```bash
   pyinstaller --onefile --distpath src-tauri/bin/api \
     --name api-server-x86_64-pc-windows-msvc src/api/main.py
   ```

2. **Configure tauri.conf.json:**
   ```json
   { "bundle": { "externalBin": ["bin/api/api-server"] } }
   ```

3. **Add capability permission:**
   Create `src-tauri/capabilities/default.json` with `"permissions": ["shell:allow-execute"]`

4. **Implement Rust commands:**
   - `start_server()` - spawns sidecar with `app.shell().sidecar(name)`
   - `stop_server()` - gracefully shuts down child process

5. **Test with:**
   ```bash
   cargo tauri dev
   ```

---

## One-File PyInstaller Limitation (Critical!)

⚠️ **Cannot use `process.kill()` with `-F` (one-file) compiled executables**

- Tauri only has PID of bootloader, not actual Python process
- **Workaround:** Signal shutdown via stdin instead:
  ```rust
  child.write(b"SHUTDOWN\n").ok();
  ```
- **Alternative:** Use multi-file mode (without `-F` flag) for easier cleanup

---

## Information Quality

All findings sourced from:
✅ Official Tauri v2 documentation (v2.tauri.app)
✅ Tauri GitHub issues & discussions (real implementations)
✅ Working example repositories (dieharders/example-tauri-v2-python-server-sidecar)
✅ Community tutorials & blog posts

---

## Unresolved Questions

1. **Build pipeline optimization** - Should PyInstaller run in `beforeBuildCommand` or as pre-build step?
2. **Health checks** - Best pattern for frontend to verify sidecar readiness? (Retry logic, heartbeat?)
3. **Logging integration** - Route sidecar logs to Tauri's logging system or separate file?
4. **Multi-instance sidecars** - Can we spawn multiple instances on different ports? (Not documented)

---

## Usage Guide

### For Quick Answers
→ Read `RESEARCH-FINDINGS.md` (quick reference with code snippets)

### For Implementation
→ Follow `IMPLEMENTATION-CHECKLIST.md` step-by-step

### For Deep Technical Details
→ Study `researcher-01-tauri-sidecar.md` (sections 1-9)

### For Architecture Decisions
→ Review section 7 (Windows Pitfalls) and section 6 (Port/Config Patterns)

---

## Integration with PyInstaller Research

**Complementary Document:** `researcher-02-pyinstaller-packaging.md`

The PyInstaller research covers:
- Hidden imports for ChromaDB, FastAPI, FastEmbed
- ONNX Runtime DLL bundling
- Model file packaging
- Windows multiprocessing handling
- Binary optimization

**Combined Integration Pattern:**
1. PyInstaller builds Python executable (researcher-02)
2. Binary is named with target triple suffix (this research, section 2)
3. Tauri configuration references binary and manages lifecycle (this research, sections 1, 4-5)

---

## Next Phase: Implementation Planning

This research enables the `planner` agent to create detailed implementation tasks:
- Phase 1: Prepare Python entry point with `multiprocessing.freeze_support()`
- Phase 2: Build PyInstaller executable with correct naming
- Phase 3: Configure Tauri sidecar in `tauri.conf.json`
- Phase 4: Implement Rust lifecycle commands
- Phase 5: Test sidecar spawning/communication
- Phase 6: Integrate frontend API communication

---

**Report Status:** ✅ Complete & Production-Ready
**Confidence Level:** High (official documentation + verified examples)
**Tokens Used:** ~45K (research + report generation)
