use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

pub struct AppState {
    pub sidecar: Arc<Mutex<Option<CommandChild>>>,
}

/// Resolve data dir from APPDATA env var with fallback (pure fn, testable).
pub fn get_data_dir_fallback(appdata_env: Option<String>) -> String {
    appdata_env
        .map(|d| format!("{}/mini-rag", d))
        .unwrap_or_else(|| "./data".to_string())
}

fn get_app_data_dir(app: &AppHandle) -> String {
    app.path()
        .app_data_dir()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| get_data_dir_fallback(std::env::var("APPDATA").ok()))
}

fn spawn_sidecar(app: &AppHandle) {
    let data_dir = get_app_data_dir(app);
    std::fs::create_dir_all(&data_dir).ok();

    let sidecar_cmd = match app.shell().sidecar("api-server") {
        Ok(cmd) => cmd.args(["--data-dir", &data_dir, "--port", "52547"]),
        Err(e) => {
            eprintln!("Failed to find api-server sidecar: {}", e);
            return;
        }
    };

    match sidecar_cmd.spawn() {
        Ok((mut rx, child)) => {
            let state = app.state::<AppState>();
            *state.sidecar.lock().unwrap() = Some(child);

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

async fn shutdown_sidecar(sidecar: &Arc<Mutex<Option<CommandChild>>>) {
    // Preferred: graceful HTTP shutdown with timeout
    let client = reqwest::Client::new();
    let _ = tokio::time::timeout(
        std::time::Duration::from_secs(3),
        client.post("http://127.0.0.1:52547/shutdown").send(),
    )
    .await;

    // Fallback: kill the process
    if let Some(child) = sidecar.lock().unwrap().take() {
        let _ = child.kill();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app_state = AppState {
        sidecar: Arc::new(Mutex::new(None)),
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_data_dir_fallback_with_appdata() {
        let result =
            get_data_dir_fallback(Some("C:\\Users\\user\\AppData\\Roaming".to_string()));
        assert_eq!(result, "C:\\Users\\user\\AppData\\Roaming/mini-rag");
    }

    #[test]
    fn test_data_dir_fallback_without_appdata() {
        let result = get_data_dir_fallback(None);
        assert_eq!(result, "./data");
    }

    #[test]
    fn test_data_dir_fallback_empty_string() {
        // Empty string is treated as a valid path
        let result = get_data_dir_fallback(Some(String::new()));
        assert_eq!(result, "/mini-rag");
    }

    #[test]
    fn test_app_state_initializes_empty() {
        let state = AppState {
            sidecar: Arc::new(Mutex::new(None)),
        };
        let lock = state.sidecar.lock().unwrap();
        assert!(lock.is_none());
    }

    #[test]
    fn test_app_state_arc_clone() {
        let state = AppState {
            sidecar: Arc::new(Mutex::new(None)),
        };
        let cloned: Arc<Mutex<Option<CommandChild>>> = Arc::clone(&state.sidecar);
        // Both arcs point to the same Mutex
        assert!(cloned.lock().unwrap().is_none());
        assert_eq!(Arc::strong_count(&state.sidecar), 2);
    }
}
