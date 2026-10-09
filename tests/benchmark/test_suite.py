"""Pytest integration tests for the benchmark suite."""

import json
import os
import sys
import wave
import pytest

bench_dir = os.path.dirname(os.path.abspath(__file__))
if bench_dir not in sys.path:
    sys.path.insert(0, bench_dir)

from test_dysarthria import evaluate_wer, normalize_text
from test_memory_leak import run_memory_leak_benchmark
from run_benchmarks import generate_markdown_report


def test_audio_samples_integrity():
    """Verify that the 3 test audio files exist and have 16kHz mono 16-bit format."""
    manifest_path = os.path.join(bench_dir, "audio_samples", "manifest.json")
    assert os.path.exists(manifest_path), "Audio manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    assert len(samples) == 3, "Must have exactly 3 test audio samples"

    expected_types = {"clean", "dysarthric", "noisy"}
    found_types = {s["type"] for s in samples}
    assert expected_types == found_types

    for s in samples:
        wav_path = s["path"]
        assert os.path.exists(wav_path), f"Audio file {wav_path} must exist"
        with wave.open(wav_path, "rb") as wf:
            assert wf.getframerate() == 16000
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getnframes() > 8000  # At least 0.5s of audio


def test_text_normalization():
    """Test text normalization for fair ASR WER evaluation."""
    assert normalize_text("Hello, World! 123.") == "hello world 123"
    assert normalize_text("What is Jupiter's mass?") == "what is jupiters mass"


def test_jiwer_wer_evaluation():
    """Verify WER calculations using jiwer."""
    res = evaluate_wer("the quick brown fox", "the quick brown fox")
    assert res["wer"] == 0.0
    assert res["wer_percent"] == 0.0

    res2 = evaluate_wer("the quick brown fox jumps", "the fast brown fox jumps")
    assert 0.19 < res2["wer"] < 0.21  # 1 substitution out of 5 words (20%)


def test_memory_leak_profiler_synthetic():
    """Verify that the memory profiler captures drift and snapshots."""
    results = run_memory_leak_benchmark(iterations=10, mock_llm=True)
    assert results["iterations"] == 10
    assert "rss_drift_mb" in results
    assert "vram_drift_mb" in results
    assert results["leak_detected"] is False
    assert len(results["snapshots"]) >= 2


def test_markdown_report_formatting(tmp_path):
    """Verify that the reporting engine outputs valid markdown report."""
    report_file = tmp_path / "test_report.md"
    latency_mock = [{
        "id": "sample_1_clean",
        "type": "clean",
        "reference": "Hello world",
        "transcription": "Hello world",
        "success": True,
        "ttfa_ms": 750.0,
        "asr_latency_ms": 320.0,
        "tts_latency_ms": 430.0
    }]
    asr_mock = [{
        "id": "sample_1_clean",
        "type": "clean",
        "reference": "Hello world",
        "hypothesis": "Hello world",
        "wer": 0.0,
        "wer_percent": 0.0,
        "cer": 0.0,
        "cer_percent": 0.0
    }]
    mem_mock = {
        "iterations": 10,
        "initial_rss_mb": 150.0,
        "final_rss_mb": 152.0,
        "peak_rss_mb": 155.0,
        "rss_drift_mb": 2.0,
        "rss_drift_per_iter_mb": 0.2,
        "initial_vram_mb": 0.0,
        "final_vram_mb": 0.0,
        "vram_drift_mb": 0.0,
        "leak_detected": False,
        "snapshots": [{"iteration": 1, "rss_mb": 150.0, "vram_allocated_mb": 0.0}]
    }

    generate_markdown_report(str(report_file), latency_mock, asr_mock, mem_mock)
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "PlanetariumAI - Phase 10 Benchmark & QA Performance Report" in content
    assert "Time-To-First-Audio (TTFA)" in content
    assert "Word Error Rate" in content
