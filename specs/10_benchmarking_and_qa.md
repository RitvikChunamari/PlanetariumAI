# Specification 10: Performance Benchmarking & QA Testing

## 1. Objective
Establish an automated benchmarking suite to validate the system's performance metrics against strict production thresholds. The suite will test end-to-end latency, Word Error Rate (WER) on atypical/dysarthric speech, and resource utilization during extended sessions.

## 2. Key Performance Indicators (KPIs) & Thresholds
- **Time-To-First-Audio (TTFA):** Must be < 800ms from the moment Silero VAD detects silence.
- **Word Error Rate (WER):** Must be < 15% on standard clean audio, and < 25% on the Torgo/UASpeech dysarthric benchmark subsets.
- **Hallucination Rate:** RAG responses must exactly match the retrieved context 99% of the time (measured via LLM-as-a-judge).
- **VRAM Utilization:** Must remain stable (no memory leaks) across 1,000 consecutive inference requests.

## 3. Technology Stack
- **Testing Framework:** `pytest` (backend), `vitest` (frontend).
- **Benchmarking Tools:** Python `time` and `memory_profiler`.
- **Evaluation Metric:** `jiwer` (Python package for calculating Word Error Rate).
- **Test Data:** A local folder (`tests/audio_samples/`) containing pre-recorded Opus audio chunks representing different speaker profiles (children, deep voices, dysarthric speech, loud background noise).

## 4. Architecture of the Benchmark Suite
1. **The Simulated Client:** A Python script that acts like the React frontend, establishing a WebSocket connection to the FastAPI server and streaming audio files at real-time speeds.
2. **Telemetry Interceptors:** Timers placed at the boundaries of VAD cutoff, Whisper transcription completion, LLM first-token generation, and Kokoro TTS first-chunk generation.
3. **The Reporting Engine:** After running a batch of 50 audio samples, the suite outputs a detailed markdown report (`benchmark_results.md`) detailing the average TTFA, WER, and memory consumption.

## 5. Implementation Steps
1. Create a `tests/benchmark/` directory.
2. Add the `jiwer` and `memory_profiler` dependencies to the development environment.
3. Write `test_latency.py`: Streams audio to the WebSocket and records the exact millisecond the first TTS binary chunk is returned.
4. Write `test_dysarthria.py`: Streams 10 specific dysarthric audio samples, captures the transcribed text, compares it against known transcripts using `jiwer`, and asserts that the WER is below 25%.
5. Write `test_memory_leak.py`: Triggers 100 fast LLM generations and verifies that VRAM returns to baseline after each generation without creeping upward.