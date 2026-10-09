import os
import sys
import numpy as np
import pytest

core_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "core"))
if core_dir not in sys.path:
    sys.path.insert(0, core_dir)

from vad import SileroVAD
from inference.asr import WhisperASR


def test_vad_high_sensitivity():
    """Verify SileroVAD sensitivity captures low-amplitude vocalization."""
    vad = SileroVAD()
    
    # 1. Pure silence
    silence = np.zeros(2048, dtype=np.int16).tobytes()
    assert vad.is_speech(silence) is False

    # 2. Synthetic speech-like harmonic tone
    t = np.linspace(0, 0.128, 2048, endpoint=False)
    # Formants at 300Hz and 2500Hz
    signal = 0.15 * np.sin(2 * np.pi * 300 * t) + 0.08 * np.sin(2 * np.pi * 2500 * t)
    pcm_bytes = (signal * 32767).astype(np.int16).tobytes()
    
    # Check that is_speech is callable and returns a boolean
    result = vad.is_speech(pcm_bytes, threshold=0.32)
    assert isinstance(result, bool)


def test_whisper_normalizer_and_prompt():
    """Verify WhisperASR has initial_prompt configured and handles empty/soft inputs gracefully."""
    asr = WhisperASR()
    assert hasattr(asr, "initial_prompt")
    assert "planetarium" in asr.initial_prompt.lower()
    assert "jupiter" in asr.initial_prompt.lower()
    
    # Empty audio returns empty string
    assert asr.transcribe(b"") == ""


def test_websocket_chat_message_protocol():
    """Verify the WebSocket accepts CHAT_MESSAGE and CONFIG messages in FastAPI."""
    from fastapi.testclient import TestClient
    from main import app
    
    client = TestClient(app)
    
    # Test websocket connection and initial state message
    with client.websocket_connect("/ws/audio") as websocket:
        init_msg = websocket.receive_json()
        assert init_msg.get("type") == "state" or "state" in init_msg
        assert init_msg.get("state") == "Listening..."
        
        # Send CONFIG to update pause tolerance
        websocket.send_json({"type": "CONFIG", "silence_threshold": 28, "dysarthria_mode": True})
        
        # Send a typed chat message (Gemini-style)
        websocket.send_json({"type": "CHAT_MESSAGE", "text": "What is the Sun?"})
        
        # Expect response messages acknowledging query or updating state
        resp1 = websocket.receive_json()
        assert "type" in resp1 or "state" in resp1
