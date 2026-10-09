# Specification 08: Offline Portability & Tauri Packaging

## 1. Objective
Package the PlanetariumAI React frontend and Python FastAPI backend into a single, self-contained executable using Tauri v2. The final build must be completely portable, requiring no external dependencies, Python installations, or Node.js environments on the Host PC.

## 2. Technology Stack
- **Packaging Framework:** Tauri v2 (Rust-based, native OS webview, incredibly lightweight).
- **Backend Bundler:** PyInstaller (freezes the Python FastAPI backend, LanceDB, and model loaders into a standalone binary).
- **Frontend Bundler:** Vite.

## 3. Architecture & Process
1. **The Sidecar Model:** Tauri allows us to embed external binaries inside the final app. We will compile our Python `core/` folder into an executable named `planetarium-ai-server`.
2. **PyInstaller Freezing:** We will write a PyInstaller `.spec` file that includes the `llama-cpp-python` dynamic libraries (CUDA/Metal), the ONNX runtimes, Silero VAD, LanceDB, and the Python standard library.
3. **Tauri Orchestration:** When the user double-clicks the PlanetariumAI app, Tauri launches. In the background, Tauri automatically spawns the Python executable as a "Sidecar" child process.
4. **IPC / Port Management:** Tauri passes a dynamically assigned port to the Python server via stdout. The React frontend reads this port and establishes the WebSocket connection.
5. **Graceful Shutdown:** When the user closes the Tauri window, it must cleanly terminate the Python sidecar process so models are unloaded from VRAM.

## 4. Implementation Steps
1. **PyInstaller Setup:** Create a `build_backend.py` script that runs PyInstaller with the `--onedir` flag (to prevent extreme unpacking latency on every boot) and correctly maps the `models/` directory.
2. **Tauri Initialization:** Run `pnpm tauri init` inside the React app. Configure `tauri.conf.json` to include the `externalBin` array pointing to our compiled Python backend.
3. **Rust Spawning:** Modify `src-tauri/src/main.rs` to use Tauri's `Command::sidecar()` API to spawn the Python server on app launch.
4. **React Dynamic Port:** Modify the React WebSocket client to fetch the active backend port from Tauri's IPC before connecting.