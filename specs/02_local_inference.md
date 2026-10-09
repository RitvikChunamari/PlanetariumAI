# Specification 02: Core AI Pipeline Integration

## 1. Objective
Replace the Phase 1 audio echo mechanism with the actual local AI inference pipeline. When Silero VAD detects the end of user speech, the system must transcribe the audio, generate an astronomical response, and stream generated speech back to the client.

## 2. Model Stack
- **ASR (Speech-to-Text):** `faster-whisper` (model: `large-v3-turbo` or `base.en` for testing).
- **LLM (Text Generation):** `AstroMLab/AstroSage-8B-GGUF` running via `llama-cpp-python`.
- **TTS (Text-to-Speech):** `kokoro-onnx` (Kokoro-82M ONNX runtime).

## 3. Pipeline Execution Flow
1. **Audio Capture:** Client streams Opus audio over WebSocket (Completed in Phase 1).
2. **VAD Trigger:** Silero detects silence, closing the audio buffer (Completed in Phase 1).
3. **Transcription:** Pass the closed audio buffer to Faster-Whisper.
4. **Prompt Formatting:** Wrap the transcribed text in the Llama 3.1 Instruct format required by AstroSage-8B.
5. **LLM Streaming:** `llama.cpp` begins generating the response token-by-token.
6. **Sentence Chunking:** The orchestrator buffers the incoming tokens. Whenever a sentence boundary (., !, ?) is hit, the chunk is dispatched to the TTS engine.
7. **Audio Streaming:** Kokoro-82M synthesizes the chunk into audio and streams it down the WebSocket to the client for immediate playback.

## 4. Implementation Steps
1. Create an `inference/` module in the Python backend.
2. Write adapter classes for `WhisperASR`, `AstroSageLLM`, and `KokoroTTS` to ensure they are strictly decoupled and load into memory on server start.
3. Update the existing WebSocket endpoint: instead of echoing the audio buffer, await the transcription, feed it to the LLM generator, and yield the TTS chunks back to the WebSocket connection.
4. Add basic UI state to the React frontend (e.g., "Listening...", "Thinking...", "Speaking...") triggered by WebSocket JSON control messages sent alongside the binary audio frames.