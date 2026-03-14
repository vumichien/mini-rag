# Phase 04: Tauri Integration

**Context:** [plan.md](./plan.md) · [Tauri sidecar research](./research/researcher-01-tauri-sidecar.md)

## Overview

- **Priority:** P1
- **Status:** Complete
- **Effort:** 2h
- **Description:** Configure Tauri v2 to spawn Python sidecar on startup, pass AppData path, and gracefully shut down sidecar when app closes.

## Key Insights

- Tauri v2 sidecar config: `bundle.externalBin` (NOT v1's `allowlist.externalBin`)
- Binary must be named: `api-server-x86_64-pc-windows-msvc.exe` (check with `rustc --print host`)
- Use `tauri_plugin_shell` for spawning — `app.shell().sidecar("api-server")`
- `--onefile` PyInstaller: `child.kill()` only kills bootloader, not Python process
  → Use HTTP `POST /shutdown` instead of `child.kill()`
- Pass `%APPDATA%/mini-rag` to sidecar via `--data-dir` arg
- Store `Child` in `AppState` (Arc<Mutex>) for shutdown access

## Requirements

- Sidecar spawns automatically when Tauri app starts
- AppData path passed to sidecar via `--data-dir` CLI arg
- App sends `POST /shutdown` to sidecar on window close
- Capability JSON allows `shell:allow-execute` for sidecar
- No console window visible to user (sidecar is background)

## Architecture

```
main.rs
├── setup() callback:
│   └── spawn sidecar → store Child in AppState
│       └── args: --data-dir %APPDATA%/mini-rag --port 52547
├── on_window_event(CloseRequested):
│   └── POST http://127.0.0.1:52547/shutdown
│       └── wait 2s for graceful stop
│       └── child.kill() as fallback
└── AppState { sidecar: Arc<Mutex<Option<Child>>> }
```

## Related Code Files

- Modify: `src-tauri/src/main.rs`
- Modify: `src-tauri/Cargo.toml`
- Modify: `src-tauri/tauri.conf.json`
- Create: `src-tauri/capabilities/default.json`

## Implementation Steps

### Step 1: tauri.conf.json

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
        "height": 800,
        "resizable": true
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": ["nsis"],
    "identifier": "com.minirag.app",
    "icon": ["icons/32x32.png", "icons/128x128.png", "icons/icon.ico"],
    "externalBin": [
      "binaries/api-server"
    ],
    "windows": {
      "nsis": {
        "displayLanguageSelector": false,
        "shortcutName": "Mini RAG",
        "installerIcon": "icons/installer.ico"
      }
    }
  }
}
```

**Note:** `binaries/api-server` → Tauri looks for `src-tauri/binaries/api-server-x86_64-pc-windows-msvc.exe`

### Step 2: Cargo.toml

```toml
[package]
name = "mini-rag"
version = "0.1.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1", features = ["full"] }
```

### Step 3: capabilities/default.json

```json
{
  "version": 1,
  "identifier": "default",
  "description": "Mini RAG default capabilities",
  "windows": ["main"],
  "permissions": [
    "core:window:allow-create",
    "core:window:allow-close",
    "core:path:allow-resolve",
    "shell:allow-execute",
    "shell:allow-kill"
  ]
}
```

### Step 4: main.rs

```rust
// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::Child;

struct AppState {
    sidecar: Arc<Mutex<Option<Child>>>,
}

fn get_app_data_dir(app: &AppHandle) -> String {
    app.path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| {
            // Fallback
            std::env::var("APPDATA")
                .map(|d| format!("{}/mini-rag", d))
                .unwrap_or_else(|_| "./data".to_string())
        })
}

fn spawn_sidecar(app: &AppHandle) {
    let data_dir = get_app_data_dir(app);
    std::fs::create_dir_all(&data_dir).ok();

    let sidecar_cmd = app
        .shell()
        .sidecar("api-server")
        .expect("Failed to find api-server sidecar")
        .args(["--data-dir", &data_dir, "--port", "52547"]);

    match sidecar_cmd.spawn() {
        Ok((mut rx, child)) => {
            // Store child for later shutdown
            let state = app.state::<AppState>();
            *state.sidecar.lock().unwrap() = Some(child);

            // Log sidecar output in debug builds
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(b) => {
                            if cfg!(debug_assertions) {
                                println!("[sidecar] {}", String::from_utf8_lossy(&b));
                            }
                        }
                        CommandEvent::Stderr(b) => {
                            eprintln!("[sidecar err] {}", String::from_utf8_lossy(&b));
                        }
                        CommandEvent::Terminated(status) => {
                            println!("[sidecar] terminated: {:?}", status);
                            break;
                        }
                        _ => {}
                    }
                }
            });
        }
        Err(e) => {
            eprintln!("Failed to spawn sidecar: {}", e);
        }
    }
}

async fn shutdown_sidecar(state: &Arc<Mutex<Option<Child>>>) {
    // Preferred: graceful HTTP shutdown
    let client = reqwest::Client::new();
    let _ = tokio::time::timeout(
        std::time::Duration::from_secs(3),
        client.post("http://127.0.0.1:52547/shutdown").send(),
    ).await;

    // Fallback: kill process
    if let Some(mut child) = state.lock().unwrap().take() {
        let _ = child.kill();
    }
}

fn main() {
    let app_state = AppState {
        sidecar: Arc::new(Mutex::new(None)),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(app_state)
        .setup(|app| {
            spawn_sidecar(app.handle());
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.app_handle().state::<AppState>();
                let sidecar_ref = Arc::clone(&state.sidecar);
                tauri::async_runtime::block_on(async move {
                    shutdown_sidecar(&sidecar_ref).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Note:** Add `reqwest` to Cargo.toml if using HTTP shutdown:
```toml
reqwest = { version = "0.11", features = ["json"] }
```

Or alternatively: use stdin signal approach (simpler, no extra dep):
```rust
// Send shutdown signal via stdin
if let Some(child) = &mut *state.sidecar.lock().unwrap() {
    let _ = child.write(b"SHUTDOWN\n");
}
tokio::time::sleep(std::time::Duration::from_millis(2000)).await;
```

### Step 5: Test sidecar integration

```bash
# First build the Python sidecar (see phase 5), then:
npm run tauri dev

# Check console for: [sidecar] INFO: Application startup complete
# Then open http://127.0.0.1:52547/health in browser
```

## Todo List

- [x] Update `src-tauri/tauri.conf.json` with `bundle.externalBin` and NSIS config
- [x] Update `src-tauri/Cargo.toml` with `tauri-plugin-shell` + `tokio` + `reqwest`
- [x] Create `src-tauri/capabilities/default.json` with `shell:allow-execute`
- [x] Implement `src-tauri/src/main.rs` with sidecar spawn + graceful shutdown
- [x] Test: sidecar spawns on app start, health check succeeds
- [x] Test: app close triggers /shutdown, sidecar exits cleanly

## Success Criteria

- `npm run tauri dev` → sidecar starts → `/health` returns 200
- React loading screen shows, then transitions to main UI
- App window close → sidecar process stops (verify in Task Manager)

## Risk Assessment

- **Binary naming**: `rustc --print host` output must match the suffix on the .exe file
- **reqwest dependency**: Adds ~5MB to binary — use stdin approach if size is concern
- **Sidecar not found**: Verify `src-tauri/binaries/api-server-{triple}.exe` exists before build

## Security Considerations

- Sidecar listens only on `127.0.0.1` — not accessible from network
- AppData dir created by Tauri Rust code, not Python (safer)

## Next Steps

→ Phase 5: PyInstaller build config
