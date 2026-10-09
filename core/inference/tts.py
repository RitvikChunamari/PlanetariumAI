import os
import sys
from kokoro_onnx import Kokoro
import numpy as np

def resolve_model_path(path: str) -> str:
    if os.path.exists(path):
        return path
    core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    c1 = os.path.join(core_dir, path)
    if os.path.exists(c1):
        return c1
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        for cand in [
            os.path.join(exe_dir, path),
            os.path.join(exe_dir, "resources", path),
            os.path.join(exe_dir, "..", "Resources", path)
        ]:
            if os.path.exists(cand):
                return cand
    return path

class KokoroTTS:
    def __init__(self, model_path="models/kokoro-v1.0.onnx", voices_path="models/voices-v1.0.bin"):
        model_path = resolve_model_path(model_path)
        voices_path = resolve_model_path(voices_path)
        self.kokoro = Kokoro(model_path, voices_path)
        
    def synthesize(self, text: str, voice="af_sarah") -> bytes:
        """
        Synthesizes text into raw 16-bit PCM bytes (24kHz).
        """
        if not text.strip():
            return b""
            
        try:
            samples, _ = self.kokoro.create(
                text,
                voice=voice,
                speed=1.0,
                lang="en-us"
            )
            # samples is a float32 array
            samples_int16 = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
            return samples_int16.tobytes()
        except Exception as e:
            print(f"TTS Error: {e}")
            return b""
