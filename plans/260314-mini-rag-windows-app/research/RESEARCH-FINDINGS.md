# Quick Reference: Tauri v2 Sidecar Key Findings

## Configuration Snippet

**tauri.conf.json:**
```json
{
  "bundle": {
    "externalBin": ["binaries/api-server"]
  }
}
```

**src-tauri/capabilities/default.json:**
```json
{
  "permissions": [
    "shell:allow-execute"
  ]
}
```

**Cargo.toml:**
```toml
tauri-plugin-shell = "2"
```

---

## Binary Naming Convention

```
<name>-<target-triple><.exe>
```

**Windows Examples:**
- 64-bit: `api-server-x86_64-pc-windows-msvc.exe`
- 32-bit: `api-server-i686-pc-windows-msvc.exe`

Find your triple: `rustc --print host`

---

## Rust Code Skeleton

```rust
use tauri_plugin_shell::ShellExt;

#[tauri::command]
async fn start_server(app: tauri::AppHandle) -> Result<u16, String> {
    let (mut rx, mut child) = app
        .shell()
        .sidecar("api-server")
        .map_err(|e| e.to_string())?
        .spawn()
        .map_err(|e| e.to_string())?;

    // Handle output in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                tauri_plugin_shell::process::CommandEvent::Stdout(bytes) => {
                    println!("[SIDECAR] {}", String::from_utf8_lossy(&bytes));
                }
                _ => {}
            }
        }
    });

    Ok(8008)  // Return port
}
```

---

## Key Gotchas

| Issue | Windows-Specific | Fix |
|---|---|---|
| One-file PyInstaller can't be killed | Yes | Use `-F` with stdin shutdown signal or multi-file mode |
| Antivirus warnings | Yes | Code-sign binaries; build reputation over time |
| Path separators | Yes | Use forward slashes in JSON; Tauri converts internally |
| Permission denied on file write | Partial | Write to `AppData`/`AppConfig` only |
| Binary not found | Yes | Verify target triple matches `rustc --print host` |

---

## Lifecycle: Starting on App Open, Killing on App Close

**Pattern 1 (Automatic):** Tauri tries to clean up spawned children on app exit.

**Pattern 2 (Explicit):**
```rust
fn stop_server(state: tauri::State<AppState>) -> Result<(), String> {
    if let Some(mut child) = state.sidecar.lock().unwrap().take() {
        child.kill().map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

**Pattern 3 (Graceful):** For one-file PyInstaller:
```rust
// Signal shutdown via stdin, don't call kill()
child.write(b"SHUTDOWN\n").ok();
```

---

## Passing Port to Frontend

**Simplest:** Hardcode `localhost:8008`

**Flexible:** Rust command returns port:
```rust
#[tauri::command]
async fn init_app(app: tauri::AppHandle) -> Result<u16, String> {
    start_server(app).await
}
```

Frontend:
```typescript
const port = await invoke("init_app");
const API_URL = `http://localhost:${port}`;
```

---

## PyInstaller Command for Windows

```bash
pyinstaller \
  --onefile \
  --distpath src-tauri/bin/api \
  --name api-server-x86_64-pc-windows-msvc \
  src/api/main.py
```

Output: `src-tauri/bin/api/api-server-x86_64-pc-windows-msvc.exe`

---

## Tauri v1 → v2 Migration

| Change | Impact |
|---|---|
| `allowlist.externalBin` → `bundle.externalBin` | Config restructure |
| Permissions system replaces allowlist | Must create capability files |
| `Command::new_sidecar()` → `app.shell().sidecar()` | Rust code rewrite |
| `process-command-api` feature removed | Simplifies Cargo.toml |

---

## Complete Registration Checklist

- [ ] Build PyInstaller executable with correct target triple suffix
- [ ] Place in `src-tauri/binaries/` or subdirectory
- [ ] Add to `bundle.externalBin` in `tauri.conf.json`
- [ ] Add `tauri-plugin-shell = "2"` to `Cargo.toml`
- [ ] Create `src-tauri/capabilities/default.json` with `shell:allow-execute`
- [ ] Implement Rust commands for spawn/kill with `ShellExt` trait
- [ ] Test with `cargo tauri dev`
- [ ] Verify binary presence in `src-tauri/target/` after build

---

**Full Details:** See `researcher-01-tauri-sidecar.md`
