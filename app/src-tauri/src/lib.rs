use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Manager, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct ServerProcess(Arc<Mutex<Option<CommandChild>>>);

#[tauri::command]
fn get_backend_port() -> u16 {
    8000
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let server_child: Arc<Mutex<Option<CommandChild>>> = Arc::new(Mutex::new(None));
    let server_child_clone = server_child.clone();

    tauri::Builder::default()
        .manage(ServerProcess(server_child.clone()))
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .plugin(tauri_plugin_shell::init())
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let app_handle: AppHandle = app.handle().clone();
            let child_holder = server_child_clone.clone();

            // Spawn the Python FastAPI Sidecar
            match app_handle.shell().sidecar("planetarium-ai-server") {
                Ok(command) => {
                    let cmd_with_args = command.args(["--port", "8000"]);
                    match cmd_with_args.spawn() {
                        Ok((mut rx, child)) => {
                            println!("[Tauri Orchestrator] Python sidecar spawned successfully (PID: {})", child.pid());
                            *child_holder.lock().unwrap() = Some(child);

                            tauri::async_runtime::spawn(async move {
                                while let Some(event) = rx.recv().await {
                                    match event {
                                        CommandEvent::Stdout(bytes) => {
                                            let line = String::from_utf8_lossy(&bytes);
                                            println!("[Server STDOUT] {}", line.trim_end());
                                        }
                                        CommandEvent::Stderr(bytes) => {
                                            let line = String::from_utf8_lossy(&bytes);
                                            eprintln!("[Server STDERR] {}", line.trim_end());
                                        }
                                        CommandEvent::Error(err) => {
                                            eprintln!("[Server Error] {}", err);
                                        }
                                        CommandEvent::Terminated(payload) => {
                                            println!("[Server Terminated] code: {:?}", payload.code);
                                        }
                                        _ => {}
                                    }
                                }
                            });
                        }
                        Err(e) => {
                            eprintln!("[Tauri Orchestrator] Warning: Failed to spawn sidecar directly: {}. If running in dev without compiled sidecar, ensure local server is active.", e);
                        }
                    }
                }
                Err(e) => {
                    eprintln!("[Tauri Orchestrator] Sidecar configuration note: {}. Ensure binary exists in src-tauri/binaries.", e);
                }
            }

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                println!("[Tauri Orchestrator] Window close requested. Terminating sidecar process...");
                let state: State<ServerProcess> = window.state();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                        println!("[Tauri Orchestrator] Sidecar terminated cleanly. VRAM/CPU released.");
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while building tauri application");
}
