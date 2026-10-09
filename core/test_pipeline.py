import asyncio
import websockets
import json
import numpy as np
from inference.tts import KokoroTTS

async def test_pipeline():
    print("Generating test audio...")
    tts = KokoroTTS("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    raw_24k = tts.synthesize("Show me Jupiter.", voice="af_sarah")
    
    arr_24k = np.frombuffer(raw_24k, dtype=np.int16)
    arr_16k = np.interp(
        np.arange(0, len(arr_24k), 1.5),
        np.arange(0, len(arr_24k)),
        arr_24k
    ).astype(np.int16)
    pcm_16k = arr_16k.tobytes()
    
    print("Connecting to websocket...")
    async with websockets.connect("ws://localhost:8000/ws/audio", ping_interval=None, ping_timeout=None) as ws:
        # Wait for Listening
        state_msg = json.loads(await ws.recv())
        assert state_msg["state"] == "Listening..."
        print("State: Listening...")
        
        # Send chunks of audio
        print("Sending audio...")
        chunk_size = 2048
        for i in range(0, len(pcm_16k), chunk_size):
            await ws.send(pcm_16k[i:i+chunk_size])
            await asyncio.sleep(0.01)
            
        # Send silence to trigger VAD
        print("Sending silence...")
        silence = np.zeros(2048, dtype=np.int16).tobytes()
        for _ in range(20):
            await ws.send(silence)
            await asyncio.sleep(0.05)
            
        # Receive Thinking
        msg = json.loads(await ws.recv())
        assert msg["state"] == "Thinking..."
        print("State: Thinking...")
        
        # Receive Searching Archives
        msg = json.loads(await ws.recv())
        if msg.get("state") == "Searching Archives...":
            print("State: Searching Archives...")
            msg = json.loads(await ws.recv())
            
        # Receive Speaking and transcription
        assert msg["state"] == "Speaking..."
        print(f"Transcription: {msg['transcription']}")
        
        # Receive audio chunks or image
        received_audio = bytearray()
        received_image = False
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                received_audio.extend(msg)
                print(f"Received audio chunk of {len(msg)} bytes")
            elif isinstance(msg, str):
                m = json.loads(msg)
                if m.get("image"):
                    print("Received image metadata:", m["image"]["title"])
                    received_image = True
                if m.get("state") == "Listening...":
                    print("Pipeline completed successfully.")
                    break
        
        print(f"Total audio received: {len(received_audio)} bytes")
        print(f"Image received: {received_image}")
        
        print(f"Total audio received: {len(received_audio)} bytes")
        
if __name__ == "__main__":
    asyncio.run(test_pipeline())
