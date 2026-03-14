# Tauri v2 Python Sidecar Integration on Windows

**Research Date:** 2026-03-14
**Focus:** PyInstaller-compiled Python executable bundled as Tauri sidecar on Windows

---

## Executive Summary

Tauri v2 has robust sidecar support for bundling external binaries (including Python executables). The process involves three key components:
1. **Configuration** in `tauri.conf.json` with `externalBin` array
2. **Binary naming** following target triple convention: `name-x86_64-pc-windows-msvc.exe`
3. **Rust code** using `tauri_plugin_shell::ShellExt` trait to spawn/manage lifecycle

Windows has specific concerns around path handling, permissions, and antivirus prompts that differ from macOS/Linux.

---

## 1. tauri.conf.json Sidecar Configuration

### Basic Configuration Structure

```json
{
  "build": {
    "devUrl": "http://localhost:1420",
    "frontendDist": "../dist"
  },
  "app": {
    "windows": [
      {
        "title": "Mini RAG",
        "width": 1200,
        "height": 800
      }
    ]
  },
  "bundle": {
    "active": true,
    "targets": ["msi", "nsis"],
    "externalBin": [
      "binaries/api-server"
    ]
  }
}
```

### Key Points

- **Relative paths** are resolved from `src-tauri/` directory
- `externalBin` array contains logical names (without target triple)
- Tauri CLI automatically appends target triple + `.exe` extension at build time
- Absolute paths also supported but less portable

### Complete Multi-Platform Example

```json
{
  "bundle": {
    "externalBin": [
      "binaries/api-server",
      "binaries/data-processor"
    ]
  }
}
```

For this config, you must provide:
- `src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe` (Windows 64-bit)
- `src-tauri/binaries/api-server-x86_64-unknown-linux-gnu` (Linux)
- `src-tauri/binaries/api-server-aarch64-apple-darwin` (macOS Apple Silicon)

---

## 2. Binary Naming Convention

### Target Triple Suffix Pattern

```
<binary-name>-<target-triple><.exe-on-windows>
```

### Windows-Specific Examples

| Architecture | Target Triple | Full Binary Name |
|---|---|---|
| 64-bit (MSVC) | `x86_64-pc-windows-msvc` | `api-server-x86_64-pc-windows-msvc.exe` |
| 32-bit (MSVC) | `i686-pc-windows-msvc` | `api-server-i686-pc-windows-msvc.exe` |
| 64-bit (GNU) | `x86_64-pc-windows-gnu` | `api-server-x86_64-pc-windows-gnu.exe` |

### Discovering Your Target Triple

```bash
rustc --print host
# Output: x86_64-pc-windows-msvc
```

### PyInstaller Command to Match Naming

```bash
# Build a one-file PyInstaller bundle for Windows x64
pyinstaller \
  --onefile \
  --distpath src-tauri/bin/api \
  --name api-server-x86_64-pc-windows-msvc \
  api_server.py

# Output: src-tauri/bin/api/api-server-x86_64-pc-windows-msvc.exe
```

Then reference in `tauri.conf.json`:
```json
{
  "bundle": {
    "externalBin": ["bin/api/api-server"]
  }
}
```

### Critical Note on One-File Executables

⚠️ **PyInstaller `-F` (one-file) limitation:** Tauri only knows the PID of the PyInstaller bootloader, not the child process (actual Python interpreter). This breaks direct `process.kill()`.

**Workaround:** Implement shutdown via stdin message or config-file signal, not process termination.

---

## 3. Cargo.toml Capabilities Required

### Minimum Dependencies

```toml
[dependencies]
tauri = { version = "2", features = ["shell-open"] }
tauri-plugin-shell = "2"
tokio = { version = "1", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
```

### Feature Flags

No special feature flags required in Tauri v2 (unlike v1's `process-command-api` feature).

### Build Dependencies

If building the sidecar from Python source during the Tauri build:
```toml
[build-dependencies]
std = "..."  # For executing PyInstaller
```

---

## 4. Rust Code Implementation

### 4.1 Basic Sidecar Spawning

```rust
use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

#[tauri::command]
async fn start_server(app: AppHandle) -> Result<u16, String> {
    // Create sidecar command by filename only (not full path)
    let sidecar_command = app
        .shell()
        .sidecar("api-server")
        .map_err(|e| format!("Failed to create sidecar: {}", e))?;

    // Spawn with optional arguments
    let (mut rx, mut child) = sidecar_command
        .args(["--port", "8008"])
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // Spawn async task to handle output
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let line = String::from_utf8_lossy(&bytes);
                    println!("[SIDECAR] {}", line);
                }
                CommandEvent::Stderr(bytes) => {
                    let err = String::from_utf8_lossy(&bytes);
                    eprintln!("[SIDECAR ERR] {}", err);
                }
                CommandEvent::Terminated(_) => {
                    println!("[SIDECAR] Process terminated");
                }
                _ => {}
            }
        }
    });

    Ok(8008)
}
```

### 4.2 Storing Child Process for Cleanup

```rust
use std::sync::{Arc, Mutex};
use tauri_plugin_shell::process::Child;

struct AppState {
    sidecar: Arc<Mutex<Option<Child>>>,
}

#[tauri::command]
async fn start_server(app: AppHandle) -> Result<u16, String> {
    let sidecar_command = app
        .shell()
        .sidecar("api-server")
        .map_err(|e| format!("Failed to create sidecar: {}", e))?;

    let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("Failed to spawn sidecar: {}", e))?;

    // Store child process handle
    let state = app.state::<AppState>();
    *state.sidecar.lock().unwrap() = Some(child);

    // Handle output in background
    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    println!("[SIDECAR] {}", String::from_utf8_lossy(&bytes));
                }
                _ => {}
            }
        }
    });

    Ok(8008)
}

#[tauri::command]
fn stop_server(state: tauri::State<AppState>) -> Result<(), String> {
    if let Some(mut child) = state.sidecar.lock().unwrap().take() {
        child.kill().map_err(|e| e.to_string())?;
    }
    Ok(())
}
```

### 4.3 App Lifecycle Integration (main.rs)

```rust
#[tauri::command]
async fn init_app(app: AppHandle) -> Result<(), String> {
    // Spawn sidecar on app startup
    start_server(app).await?;
    Ok(())
}

fn main() {
    let app_state = AppState {
        sidecar: Arc::new(Mutex::new(None)),
    };

    tauri::Builder::default()
        .setup(|app| {
            // Spawn sidecar when app starts
            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let _ = start_server(app_handle).await;
            });
            Ok(())
        })
        .on_window_event(|_window, event| {
            // Could add window-specific lifecycle hooks here
        })
        .manage(app_state)
        .invoke_handler(tauri::generate_handler![
            start_server,
            stop_server,
            init_app
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## 5. src-tauri/capabilities/default.json Permissions

### Minimal Permission for Sidecar Execution

```json
{
  "version": 1,
  "identifier": "default",
  "description": "Default Tauri capabilities",
  "windows": ["main"],
  "permissions": [
    "core:window:allow-create",
    "core:window:allow-close",
    "core:path:allow-resolve",
    "shell:allow-execute"
  ]
}
```

### Enhanced Configuration with Sidecar-Specific Rules

```json
{
  "permissions": [
    {
      "identifier": "shell:allow-execute",
      "allow": [
        {
          "name": "api-server",
          "sidecar": true,
          "args": [
            "--port",
            { "validator": "^[0-9]{1,5}$" },
            "--host",
            { "validator": "^(localhost|127\\.0\\.0\\.1)$" }
          ]
        }
      ]
    }
  ]
}
```

---

## 6. Passing Port/Config to Frontend

### Pattern 1: Hardcoded Port (Simplest)

Python sidecar always starts on `localhost:8008`, frontend hardcodes it:

```typescript
// src/lib/api.ts
const API_URL = "http://localhost:8008";

export async function fetchData() {
  const response = await fetch(`${API_URL}/api/data`);
  return response.json();
}
```

### Pattern 2: Tauri Command Response

Return port from Rust startup command:

```rust
#[tauri::command]
async fn init_app(app: AppHandle) -> Result<u16, String> {
    start_server(app).await  // Returns port number
}
```

Frontend:

```typescript
// src/main.ts
async function initApp() {
  const port = await invoke("init_app");
  window.APP_PORT = port;
}

export const API_URL = `http://localhost:${window.APP_PORT}`;
```

### Pattern 3: Config File

Python sidecar writes port to config file on startup:

**Python (api_server.py):**
```python
import json

port = 8008
with open("sidecar.config.json", "w") as f:
    json.dump({"port": port, "host": "127.0.0.1"}, f)
```

**Frontend:**
```typescript
async function loadConfig() {
  const config = await readTextFile("sidecar.config.json", { dir: BaseDirectory.AppConfig });
  return JSON.parse(config);
}

const config = await loadConfig();
export const API_URL = `http://${config.host}:${config.port}`;
```

### Pattern 4: Environment Variable (During Build)

Set at build time, not runtime:

```bash
export VITE_API_PORT=8008
npm run build
```

Frontend (`.env`):
```
VITE_API_URL=http://localhost:8008
```

**⚠️ Not recommended** for dynamic ports. Best for fixed configurations.

---

## 7. Common Windows Pitfalls & Mitigations

### 7.1 Path Issues

**Problem:** Sidecar binary not found on Windows due to path separators.

**Cause:** Mixing forward slashes and backslashes in `tauri.conf.json`.

**Fix:**
```json
{
  "bundle": {
    "externalBin": [
      "binaries/api-server"
    ]
  }
}
```
Use forward slashes consistently. Tauri handles conversion to backslashes internally.

### 7.2 Antivirus & Firewall Prompts

**Problem:** Windows Defender flags sidecar executable as untrusted.

**Cause:** PyInstaller bundles can trigger heuristic antivirus scanning.

**Mitigations:**
1. **Code signing:** Sign the main `.exe` and sidecar binary with a valid certificate
2. **Publisher reputation:** Build track record over time; first release often triggers warnings
3. **Wix configuration:** Add firewall exception rules during MSI installation
4. **User documentation:** Explain that the port is for local communication only

### 7.3 Permission Denied Errors

**Problem:** Sidecar fails with `Error 5: Access Denied` on file write operations.

**Cause:** Sidecar runs in app's privilege context; file write to protected directories fails.

**Fix:**
- Ensure Python sidecar writes to `AppConfig` or `AppData` directories only
- Use Tauri's `path` module to resolve safe directories:

```rust
use tauri::api::path;

#[tauri::command]
fn get_app_data_dir() -> String {
    path::app_data_dir(&tauri::Config::default())
        .unwrap_or_default()
        .to_string_lossy()
        .to_string()
}
```

Pass to Python sidecar:
```bash
--data-dir "C:\\Users\\username\\AppData\\Roaming\\MyApp"
```

### 7.4 One-File Executable Kill Issue

**Problem:** `child.kill()` fails silently on PyInstaller `-F` executables.

**Cause:** Tauri only has bootloader PID, not the actual Python process tree.

**Workaround:** Signal shutdown via IPC instead:

```rust
// Send shutdown command via stdin
child.write("SHUTDOWN\n".as_bytes()).ok();

// Wait for graceful termination (timeout 5s)
tokio::time::timeout(
    std::time::Duration::from_secs(5),
    async { /* wait for process event */ }
)
.await
.ok();
```

Or use PyInstaller multi-file mode:
```bash
pyinstaller api_server.py  # Without -F flag
```

---

## 8. Tauri v1 vs v2 Key Differences

### Configuration Changes

| Aspect | Tauri v1 | Tauri v2 |
|---|---|---|
| **Config location** | `tauri.conf.json` | `tauri.conf.json` (same) |
| **Bin reference** | `allowlist.externalBin` | `bundle.externalBin` |
| **Permissions** | Allowlist | Capability system (ACL) |
| **Feature flag** | `process-command-api` feature required | Not needed |

### API Changes

| Aspect | Tauri v1 | Tauri v2 |
|---|---|---|
| **Rust import** | `use tauri::Command` | `use tauri_plugin_shell::ShellExt` |
| **Spawn call** | `Command::new_sidecar(name)` | `app.shell().sidecar(name)` |
| **Return type** | `(Receiver, Child)` | `(Receiver, Child)` (same) |
| **JS API** | `tauri.invoke("executeCmd", ...)` | `Command.sidecar(name).execute()` |

### Breaking Changes for Migration

1. **Must add `src-tauri/capabilities/` directory** with capability JSON files
2. **Shell plugin must be explicitly enabled** in build
3. **Allowlist patterns no longer work** — use capability permissions instead
4. **JavaScript API completely changed** — use `@tauri-apps/plugin-shell` module

---

## 9. Step-by-Step Registration Checklist

### Step 1: Build Python Sidecar

```bash
pyinstaller \
  --onefile \
  --distpath src-tauri/bin/api \
  --name api-server-x86_64-pc-windows-msvc \
  src/api/main.py
```

### Step 2: Configure tauri.conf.json

```json
{
  "bundle": {
    "externalBin": ["bin/api/api-server"]
  }
}
```

### Step 3: Add Cargo Dependency

```toml
tauri-plugin-shell = "2"
```

### Step 4: Create Capability File

File: `src-tauri/capabilities/default.json`

```json
{
  "permissions": [
    "shell:allow-execute"
  ]
}
```

### Step 5: Rust Implementation (main.rs)

Implement `start_server()` and `stop_server()` commands as shown in section 4.

### Step 6: Frontend Integration

Call Tauri command to start sidecar and get port:

```typescript
import { invoke } from "@tauri-apps/api/core";

const port = await invoke("init_app");
const API_URL = `http://localhost:${port}`;
```

### Step 7: Test

```bash
cargo tauri dev
```

Monitor `src-tauri/target/` for `api-server-*.exe` binary being bundled.

---

## 10. Key Sources & References

- [Tauri v2 Sidecar Docs](https://v2.tauri.app/develop/sidecar/)
- [Tauri v2 Shell Plugin](https://v2.tauri.app/plugin/shell/)
- [Example: Tauri v2 Python Sidecar](https://github.com/dieharders/example-tauri-v2-python-server-sidecar)
- [Discussion: Embedding Python for Sidecar](https://github.com/tauri-apps/tauri/discussions/2759)
- [Tauri Migration Guide (v1→v2)](https://v2.tauri.app/start/migrate/from-tauri-1/)
- [Writing a Pandas Sidecar for Tauri](https://mclare.blog/posts/writing-a-pandas-sidecar-for-tauri/)

---

## 11. Unresolved Questions

1. **Optimal build pipeline:** Should PyInstaller run as part of Tauri's `beforeBuildCommand`, or as a pre-build step in CI/CD? (Affects build time & reproducibility)
2. **Health checks:** Best pattern for frontend to verify sidecar is running? (Retry logic on init, heartbeat endpoint?)
3. **Logging integration:** Should sidecar logs route to Tauri's logging system or separate file? (Affects debugging experience)
4. **Multi-instance sidecar:** Can we spawn multiple sidecar instances on different ports? (Not documented in v2 examples)

---

**Report Status:** Complete
**Confidence Level:** High (information from official docs + working examples)
