# Specification 01: Host/Client Architecture

## 1. Objective
Build the foundation for PlanetariumAI: a Host/Client system where heavy AI inference runs on a local PC, and the user interacts via a Progressive Web App (PWA) on any remote device (tablet, phone, kiosk) over a secure, low-latency connection.

## 2. System Components

### 2.1 Host Server (The Brain)
- **Framework:** Python + FastAPI.
- **Protocol:** HTTP/2 for static files and SSE (Server-Sent Events) for text streaming; WebSockets for bidirectional low-latency audio.
- **Hardware Acceleration:** Auto-detects CUDA, Metal, Vulkan, or CPU environments to load the optimal `llama-cpp-python` backend.
- **Models Loaded in Memory:**
  - Silero VAD (Voice Activity Detection).
  - Faster-Whisper (ASR).
  - Llama 3.1 8B / Qwen 2.5 7B (GGUF format via `llama.cpp`).
  - Kokoro-82M (TTS via ONNX Runtime).

### 2.2 Thin Client (The Interface)
- **Framework:** React + TypeScript + Vite, configured as a PWA.
- **Audio Capture:** Uses the HTML5 Web Audio API (`MediaRecorder` or `AudioWorklet`) to capture microphone input, encodes it as Opus audio chunks, and streams it over a WebSocket.
- **Audio Playback:** Receives Opus audio chunks from the server and plays them sequentially to achieve continuous speech generation.
- **Visuals:** Implements the Swiss Design System (strict grids, sans-serif typography, high contrast).

### 2.3 Network Layer (Security & Transport)
- **Requirement:** Modern browsers require HTTPS (TLS) to grant microphone access.
- **Local Deployment:** The host server must run behind a local reverse proxy (e.g., Caddy with a local CA certificate) or use a Tailscale mesh network for secure remote access without opening router ports.

## 3. The Low-Latency Streaming Pipeline (Sub-800ms TTFA)
To achieve natural conversation, the system must process data asynchronously:
1. **Mic Stream:** Client streams Opus audio over WebSocket -> Host.
2. **VAD Cutoff:** Host Silero VAD detects the end of the user's speech and closes the capture buffer.
3. **ASR:** Host Faster-Whisper transcribes the audio buffer instantly.
4. **LLM Stream:** Host `llama.cpp` generates text tokens.
5. **Sentence Chunking:** The Python orchestrator buffers text tokens until a sentence boundary (., ?, !) is reached.
6. **TTS Stream:** The complete sentence is sent to Kokoro ONNX. The resulting audio chunk is immediately streamed back to the Client via WebSocket.
7. **Playback & Interrupt:** Client plays the chunk. If the user speaks again, the Client sends an "INTERRUPT" frame over the WebSocket to halt the Host LLM/TTS workers and flush the audio queue.

## 4. Phase 1 Implementation Plan
1. **Initialize Repo:** Create the `/core` (Python) and `/app` (React) directories.
2. **Setup FastAPI:** Create the WebSocket endpoints for `/asr` and `/tts`.
3. **Audio Echo Test:** Write a simple frontend component that captures the mic, streams it to the server, and the server echoes the audio back (proving the Web Audio API, Opus encoding, and WebSocket transport work securely).
4. **VAD Integration:** Add Silero VAD to the server to detect when the echoed speech stops.