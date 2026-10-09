"""ASR benchmark measuring Word Error Rate (WER) and Character Error Rate (CER) using jiwer."""

import json
import os
import re
import sys
import wave
from typing import Any, Dict, List
import jiwer

# Ensure core and tests are on path
bench_dir = os.path.dirname(os.path.abspath(__file__))
core_dir = os.path.abspath(os.path.join(bench_dir, "..", "..", "core"))
for p in [bench_dir, core_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)


def normalize_text(text: str) -> str:
    """Normalize text for ASR WER evaluation: lowercase, remove punctuation, strip whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def evaluate_wer(reference: str, hypothesis: str) -> Dict[str, Any]:
    """Calculate Word Error Rate (WER) and Character Error Rate (CER) using jiwer."""
    ref_norm = normalize_text(reference)
    hyp_norm = normalize_text(hypothesis)

    if not ref_norm:
        wer = 1.0 if hyp_norm else 0.0
        cer = 1.0 if hyp_norm else 0.0
    elif not hyp_norm:
        wer = 1.0
        cer = 1.0
    else:
        wer = float(jiwer.wer(ref_norm, hyp_norm))
        cer = float(jiwer.cer(ref_norm, hyp_norm))

    return {
        "reference_normalized": ref_norm,
        "hypothesis_normalized": hyp_norm,
        "wer": round(wer, 4),
        "wer_percent": round(wer * 100.0, 2),
        "cer": round(cer, 4),
        "cer_percent": round(cer * 100.0, 2)
    }


def run_asr_benchmark(audio_dir: str, use_direct_asr: bool = True) -> List[Dict[str, Any]]:
    """Evaluate ASR accuracy across the benchmark audio samples using Whisper ASR and jiwer."""
    manifest_path = os.path.join(audio_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    asr_model = None
    if use_direct_asr:
        print("[ASR Benchmark] Initializing local Faster-Whisper ASR...")
        from inference.asr import WhisperASR
        asr_model = WhisperASR()

    results = []
    print("=" * 65)
    print("      WORD ERROR RATE (WER) DYSARTHRIA & ACCURACY BENCHMARK")
    print("=" * 65)

    for item in samples:
        sample_path = item["path"]
        sample_id = item["id"]
        sample_type = item["type"]
        ref_text = item["reference_text"]

        print(f"\n[Evaluating] Sample '{sample_id}' ({sample_type})")
        print(f"  Reference: \"{ref_text}\"")

        # Load WAV
        with wave.open(sample_path, "rb") as wf:
            pcm_bytes = wf.readframes(wf.getnframes())

        # Transcribe directly
        if asr_model:
            hypothesis = asr_model.transcribe(pcm_bytes)
        else:
            hypothesis = ref_text  # Fallback for mock testing

        print(f"  Predicted: \"{hypothesis}\"")

        metrics = evaluate_wer(ref_text, hypothesis)
        print(f"  -> WER: {metrics['wer_percent']}% | CER: {metrics['cer_percent']}%")

        entry = {
            "id": sample_id,
            "type": sample_type,
            "reference": ref_text,
            "hypothesis": hypothesis,
            "wer": metrics["wer"],
            "wer_percent": metrics["wer_percent"],
            "cer": metrics["cer"],
            "cer_percent": metrics["cer_percent"]
        }
        results.append(entry)

    # Summary
    print("\n" + "=" * 65)
    all_wers = [r["wer_percent"] for r in results]
    avg_wer = sum(all_wers) / len(all_wers) if all_wers else 0.0
    print(f"Overall Average WER: {avg_wer:.2f}%")
    print("=" * 65)

    return results


def test_wer_calculation():
    """Unit test for jiwer evaluation logic."""
    ref = "What is the largest planet in our solar system"
    hyp = "What is the largest planet in our solar system"
    res = evaluate_wer(ref, hyp)
    assert res["wer"] == 0.0
    assert res["wer_percent"] == 0.0

    # 1 word substitution out of 5 words
    ref2 = "hello world from outer space"
    hyp2 = "hello earth from outer space"
    res2 = evaluate_wer(ref2, hyp2)
    assert 0.15 < res2["wer"] < 0.25


if __name__ == "__main__":
    audio_directory = os.path.join(bench_dir, "audio_samples")
    run_asr_benchmark(audio_directory)
