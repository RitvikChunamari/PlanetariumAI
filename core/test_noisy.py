import asyncio
import websockets
import json
import numpy as np
from inference.tts import KokoroTTS

async def test_noisy():
    print("Generating noisy test audio...")
    tts = KokoroTTS("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    
    def get_speech_pcm(text):
        raw_24k = tts.synthesize(text, voice="af_sarah")
        arr_24k = np.frombuffer(raw_24k, dtype=np.int16).astype(np.float32)
        
        # Add significant white noise
        noise = np.random.normal(0, 100, len(arr_24k))
        arr_24k_noisy = arr_24k + noise
        arr_24k_noisy = np.clip(arr_24k_noisy, -32768, 32767)
        
        arr_16k = np.interp(
            np.arange(0, len(arr_24k_noisy), 1.5),
            np.arange(0, len(arr_24k_noisy)),
            arr_24k_noisy
        ).astype(np.int16)
        
        # Pad with 0.5s of silence at the end to ensure it captures the last word
        silence_pad = np.zeros(8000, dtype=np.int16)
        arr_16k = np.concatenate([arr_16k, silence_pad])
        return arr_16k.tobytes()

    pcm_q1 = get_speech_pcm("Tell me a fact about Saturn.")
    
    print("Connecting to websocket...")
    async with websockets.connect("ws://localhost:8000/ws/audio", ping_interval=None, ping_timeout=None) as ws:
        state_msg = json.loads(await ws.recv())
        assert state_msg["state"] == "Listening..."
        print("State: Listening...")
        
        print("Sending Noisy Query...")
        chunk_size = 2048
        for i in range(0, len(pcm_q1), chunk_size):
            await ws.send(pcm_q1[i:i+chunk_size])
            await asyncio.sleep(0.01)
            
        print("Sending silence...")
        silence = np.zeros(2048, dtype=np.int16).tobytes()
        for _ in range(20):
            await ws.send(silence)
            await asyncio.sleep(0.05)
            
        msg = json.loads(await ws.recv())
        assert msg["state"] == "Thinking..."
        
        print("Waiting for transcription...")
        msg = json.loads(await ws.recv())
        if msg.get("state") == "Searching Archives...":
            msg = json.loads(await ws.recv())
            
        print(f"Received msg: {msg}")
        assert msg["state"] == "Speaking..."
        print(f"Transcription received: {msg.get('transcription')}")
        print("Successfully isolated voice from noise!")
        
        # Close connection
        await ws.close()

if __name__ == "__main__":
    asyncio.run(test_noisy())
