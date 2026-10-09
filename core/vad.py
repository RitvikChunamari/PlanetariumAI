import torch
import numpy as np

class SileroVAD:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            trust_repo=True
        )
         
    def is_speech(self, audio_data: bytes, threshold: float = 0.28) -> bool:
        if not audio_data:
            return False
            
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Silero requires EXACTLY 512 samples for 16kHz
        chunk_size = 512
        
        if len(audio_np) < chunk_size:
            audio_np = np.pad(audio_np, (0, chunk_size - len(audio_np)), 'constant')
            
        # Process in chunks of 512 and return True if ANY chunk is speech
        has_speech = False
        for i in range(0, len(audio_np), chunk_size):
            chunk = audio_np[i:i+chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
            
            # RMS energy of chunk
            rms = np.sqrt(np.mean(chunk**2)) if len(chunk) > 0 else 0.0
            
            audio_tensor = torch.from_numpy(chunk)
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
            
            # Sensitivity check: speech probability or audible vocal energy with moderate probability
            if speech_prob > threshold or (speech_prob > 0.18 and rms > 0.012):
                has_speech = True
                break
                
        return has_speech
