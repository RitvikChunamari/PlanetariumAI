import sys
import torchaudio
import torch
import numpy as np

# Monkeypatch torchaudio backend for older dependencies
if 'torchaudio.backend' not in sys.modules:
    sys.modules['torchaudio.backend'] = type('module', (), {})
    sys.modules['torchaudio.backend.common'] = type('module', (), {'AudioMetaData': object})

from df.enhance import init_df, enhance

class NoiseFilter:
    def __init__(self):
        print("Loading DeepFilterNet3...")
        self.model, self.df_state, _ = init_df()
        
    def process_chunk(self, audio_chunk_16k_bytes: bytes) -> bytes:
        if not audio_chunk_16k_bytes:
            return audio_chunk_16k_bytes
            
        # 16kHz int16 PCM -> float32 [-1.0, 1.0]
        audio_np = np.frombuffer(audio_chunk_16k_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_np).unsqueeze(0) # [1, T]
        
        # DeepFilterNet3 expects 48kHz audio. 
        # df_state internal state handles streaming if we pass chunks, but enhance expects continuous frames?
        # If we pass short chunks, it will enhance them.
        audio_48k = torchaudio.functional.resample(audio_tensor, 16000, 48000)
        
        # Enhance
        enhanced_48k = enhance(self.model, self.df_state, audio_48k, pad=False)
        
        # Back to 16kHz
        enhanced_16k = torchaudio.functional.resample(enhanced_48k, 48000, 16000)
        
        enhanced_np = np.clip(enhanced_16k.squeeze(0).numpy() * 32768.0, -32768, 32767).astype(np.int16)
        return enhanced_np.tobytes()
