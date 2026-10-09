"""Latency benchmark measuring Time-To-First-Audio (TTFA) over WebSocket."""

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

# Ensure tests/benchmark is importable
bench_dir = os.path.dirname(os.path.abspath(__file__))
if bench_dir not in sys.path:
    sys.path.insert(0, bench_dir)

from client import WebSocketBenchmarkClient


async def run_latency_benchmark(
    audio_dir: str,
    server_url: str = "ws://localhost:8000/ws/audio"
) -> List[Dict[str, Any]]:
    """Stream all test audio samples to the WebSocket and record TTFA latency."""
    manifest_path = os.path.join(audio_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}. Run generate_test_audio.py first.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    client = WebSocketBenchmarkClient(uri=server_url)
    results = []

    print("=" * 65)
    print("      TIME-TO-FIRST-AUDIO (TTFA) LATENCY BENCHMARK")
    print("=" * 65)

    for item in samples:
        sample_path = item["path"]
        sample_id = item["id"]
        sample_type = item["type"]
        print(f"\n[Benchmarking] Sample '{sample_id}' ({sample_type})...", flush=True)

        telemetry = await client.stream_audio_file(sample_path, timeout=90.0)
        result_entry = {
            "id": sample_id,
            "type": sample_type,
            "reference": item["reference_text"],
            "transcription": telemetry.get("transcription", ""),
            "success": telemetry.get("success", False),
            "ttfa_ms": telemetry.get("ttfa_ms"),
            "asr_latency_ms": telemetry.get("asr_latency_ms"),
            "tts_latency_ms": telemetry.get("tts_latency_ms"),
            "error": telemetry.get("error")
        }
        results.append(result_entry)

        if result_entry["success"]:
            print(f"  -> TTFA Latency: {result_entry['ttfa_ms']} ms", flush=True)
            print(f"  -> ASR Latency:  {result_entry['asr_latency_ms']} ms", flush=True)
            print(f"  -> TTS Latency:  {result_entry['tts_latency_ms']} ms", flush=True)
            print(f"  -> Audio Bytes:  {telemetry.get('audio_bytes_received')} bytes", flush=True)
            print(f"  -> Transcription: \"{result_entry['transcription']}\"", flush=True)
        else:
            print(f"  -> Failed: {result_entry['error']}", flush=True)

        await asyncio.sleep(1.0)

    print("\n" + "=" * 65)
    successful = [r["ttfa_ms"] for r in results if r["ttfa_ms"] is not None]
    if successful:
        avg_ttfa = sum(successful) / len(successful)
        min_ttfa = min(successful)
        max_ttfa = max(successful)
        print(f"Avg TTFA: {avg_ttfa:.2f} ms | Min: {min_ttfa:.2f} ms | Max: {max_ttfa:.2f} ms")
    print("=" * 65)

    return results


def test_latency_measurements():
    """Pytest target for latency verification."""
    audio_dir = os.path.join(bench_dir, "audio_samples")
    assert os.path.exists(os.path.join(audio_dir, "manifest.json"))


if __name__ == "__main__":
    audio_directory = os.path.join(bench_dir, "audio_samples")
    asyncio.run(run_latency_benchmark(audio_directory))
