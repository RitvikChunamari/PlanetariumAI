"""Simulated WebSocket client for latency and ASR benchmarking."""

import asyncio
import json
import time
import wave
from typing import Any, Dict, Optional
import numpy as np
import websockets


class WebSocketBenchmarkClient:
    """Client that streams audio to the PlanetariumAI WebSocket endpoint and records timing telemetry."""

    def __init__(self, uri: str = "ws://localhost:8000/ws/audio", chunk_size: int = 2048, chunk_interval: float = 0.01):
        self.uri = uri
        self.chunk_size = chunk_size
        self.chunk_interval = chunk_interval

    async def stream_audio_file(self, wav_path: str, silence_pad_seconds: float = 0.8, timeout: float = 90.0) -> Dict[str, Any]:
        """Load a 16kHz WAV file, stream it to the WebSocket server, and capture timing metrics."""
        with wave.open(wav_path, "rb") as wf:
            assert wf.getframerate() == 16000, f"Expected 16kHz sample rate, got {wf.getframerate()}"
            pcm_bytes = wf.readframes(wf.getnframes())

        return await self.stream_pcm(pcm_bytes, silence_pad_seconds=silence_pad_seconds, timeout=timeout)

    async def stream_pcm(self, pcm_data: bytes, silence_pad_seconds: float = 0.8, timeout: float = 90.0) -> Dict[str, Any]:
        """Stream raw 16kHz 16-bit mono PCM bytes and record exact latencies."""
        telemetry: Dict[str, Any] = {
            "success": False,
            "transcription": "",
            "ttfa_ms": None,
            "asr_latency_ms": None,
            "tts_latency_ms": None,
            "audio_bytes_received": 0,
            "error": None
        }

        t_silence_start = None
        t_thinking = None
        t_transcription = None
        t_first_audio = None
        received_chunks = []

        # Ensure pcm_data is a multiple of chunk_size
        rem = len(pcm_data) % self.chunk_size
        if rem != 0:
            pcm_data = pcm_data + b"\x00" * (self.chunk_size - rem)

        try:
            async with websockets.connect(self.uri, ping_interval=None, ping_timeout=None) as ws:
                # 1. Handshake
                init_msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=10.0))
                if init_msg.get("state") != "Listening...":
                    raise ValueError(f"Unexpected initial state: {init_msg}")

                # 2. Stream Audio in chunks
                for i in range(0, len(pcm_data), self.chunk_size):
                    chunk = pcm_data[i:i + self.chunk_size]
                    await ws.send(chunk)
                    await asyncio.sleep(self.chunk_interval)

                # 3. Stream silence to trigger VAD end-of-speech
                t_silence_start = time.perf_counter()
                silence_chunk = np.zeros(self.chunk_size // 2, dtype=np.int16).tobytes()
                num_silence_chunks = int((silence_pad_seconds * 16000 * 2) / len(silence_chunk))
                for _ in range(max(num_silence_chunks, 15)):
                    await ws.send(silence_chunk)
                    await asyncio.sleep(0.04)

                # 4. Receive server responses and track timestamps
                start_waiting = time.perf_counter()
                while time.perf_counter() - start_waiting < timeout:
                    try:
                        remaining = max(1.0, timeout - (time.perf_counter() - start_waiting))
                        msg = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except asyncio.TimeoutError:
                        break

                    if isinstance(msg, str):
                        data = json.loads(msg)
                        state = data.get("state")

                        if state == "Thinking..." and t_thinking is None:
                            t_thinking = time.perf_counter()

                        elif state == "Searching Archives..." or state == "Speaking...":
                            if "transcription" in data and not telemetry["transcription"]:
                                telemetry["transcription"] = data["transcription"]
                                t_transcription = time.perf_counter()

                        if state == "Listening..." and t_first_audio is not None:
                            # Finished cycle
                            break

                    elif isinstance(msg, (bytes, bytearray)):
                        # Binary audio chunk from TTS
                        if t_first_audio is None:
                            t_first_audio = time.perf_counter()
                        telemetry["audio_bytes_received"] += len(msg)
                        received_chunks.append(msg)
                        # Once we receive the first audio chunk, we have our primary TTFA metric
                        if len(received_chunks) >= 1:
                            break

                # 5. Calculate Metrics
                if t_first_audio is not None:
                    telemetry["success"] = True
                    # TTFA from the moment VAD detects silence / user stops speaking
                    ref_time = t_thinking or t_silence_start
                    telemetry["ttfa_ms"] = round((t_first_audio - ref_time) * 1000.0, 2)

                    if t_thinking and t_transcription:
                        telemetry["asr_latency_ms"] = round((t_transcription - t_thinking) * 1000.0, 2)
                    if t_transcription:
                        telemetry["tts_latency_ms"] = round((t_first_audio - t_transcription) * 1000.0, 2)
                else:
                    telemetry["error"] = "Did not receive binary TTS audio before timeout."

        except Exception as e:
            telemetry["error"] = str(e)

        return telemetry
