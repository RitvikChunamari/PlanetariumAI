"""Utility script to generate 3 test audio files (clean, dysarthric, noisy) for benchmarking."""

import json
import os
import sys
import wave
import numpy as np

# Ensure core is on path
core_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "core"))
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from inference.tts import KokoroTTS


def resample_24k_to_16k(audio_24k: np.ndarray) -> np.ndarray:
    """Downsample 24kHz audio to 16kHz."""
    target_len = int(len(audio_24k) * (16000.0 / 24000.0))
    indices = np.linspace(0, len(audio_24k) - 1, target_len)
    return np.interp(indices, np.arange(len(audio_24k)), audio_24k).astype(np.int16)


def save_wav(filename: str, pcm_data: bytes, sample_rate: int = 16000):
    """Save raw 16-bit PCM data to WAV file."""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    print(f"Saved: {filename} ({len(pcm_data)} bytes)")


def generate_samples(output_dir: str):
    """Generate 3 test audio samples representing diverse acoustic conditions."""
    os.makedirs(output_dir, exist_ok=True)
    models_dir = os.path.join(core_dir, "models")
    tts_model = os.path.join(models_dir, "kokoro-v1.0.onnx")
    tts_voices = os.path.join(models_dir, "voices-v1.0.bin")

    print("[AudioGen] Initializing Kokoro TTS...")
    tts = KokoroTTS(model_path=tts_model, voices_path=tts_voices)

    samples_manifest = []

    # 1. Clean Sample
    text_clean = "What is the largest planet in our solar system?"
    print(f"[AudioGen] Synthesizing Clean Sample: '{text_clean}'")
    raw_24k = tts.synthesize(text_clean, voice="af_sarah")
    arr_24k = np.frombuffer(raw_24k, dtype=np.int16).astype(np.float32)
    arr_16k_clean = resample_24k_to_16k(arr_24k)
    path_clean = os.path.join(output_dir, "sample_1_clean.wav")
    save_wav(path_clean, arr_16k_clean.tobytes())
    samples_manifest.append({
        "id": "sample_1_clean",
        "file": "sample_1_clean.wav",
        "path": path_clean,
        "type": "clean",
        "reference_text": text_clean
    })

    # 2. Dysarthric-Simulated Sample (elongated vowels, irregular tempo)
    text_dysarthric = "Tell me about black holes and the event horizon."
    print(f"[AudioGen] Synthesizing Dysarthric Sample: '{text_dysarthric}'")
    raw_24k = tts.synthesize(text_dysarthric, voice="af_sarah")
    arr_24k = np.frombuffer(raw_24k, dtype=np.int16).astype(np.float32)
    arr_16k = resample_24k_to_16k(arr_24k)
    # Simulate atypical/dysarthric speech: time stretch (slower speech rate 0.7x) + vowel pitch modulation
    stretched_len = int(len(arr_16k) * 1.35)
    stretched = np.interp(np.linspace(0, len(arr_16k) - 1, stretched_len), np.arange(len(arr_16k)), arr_16k)
    # Slight micro-tremor amplitude modulation
    t = np.linspace(0, 1, stretched_len)
    tremor = 1.0 + 0.1 * np.sin(2 * np.pi * 5 * t)
    arr_dysarthric = np.clip(stretched * tremor, -32768, 32767).astype(np.int16)
    path_dysarthric = os.path.join(output_dir, "sample_2_dysarthric.wav")
    save_wav(path_dysarthric, arr_dysarthric.tobytes())
    samples_manifest.append({
        "id": "sample_2_dysarthric",
        "file": "sample_2_dysarthric.wav",
        "path": path_dysarthric,
        "type": "dysarthric",
        "reference_text": text_dysarthric
    })

    # 3. Noisy Sample (speech mixed with background noise)
    text_noisy = "How old is the universe according to cosmic measurements?"
    print(f"[AudioGen] Synthesizing Noisy Sample: '{text_noisy}'")
    raw_24k = tts.synthesize(text_noisy, voice="af_sarah")
    arr_24k = np.frombuffer(raw_24k, dtype=np.int16).astype(np.float32)
    arr_16k = resample_24k_to_16k(arr_24k)
    # Add ambient Gaussian noise (tested with DeepFilterNet3)
    noise = np.random.normal(0, 120, len(arr_16k))
    arr_noisy = np.clip(arr_16k + noise, -32768, 32767).astype(np.int16)
    path_noisy = os.path.join(output_dir, "sample_3_noisy.wav")
    save_wav(path_noisy, arr_noisy.tobytes())
    samples_manifest.append({
        "id": "sample_3_noisy",
        "file": "sample_3_noisy.wav",
        "path": path_noisy,
        "type": "noisy",
        "reference_text": text_noisy
    })

    manifest_path = os.path.join(output_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(samples_manifest, f, indent=2)
    print(f"[AudioGen] Manifest written to: {manifest_path}")

    return samples_manifest


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "audio_samples")
    generate_samples(out_dir)
