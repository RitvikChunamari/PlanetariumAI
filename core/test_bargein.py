import asyncio
import websockets
import json
import numpy as np
from inference.tts import KokoroTTS

async def test_bargein():
    print("Generating test audio...")
    tts = KokoroTTS("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    
    def get_speech_pcm(text):
        raw_24k = tts.synthesize(text, voice="af_sarah")
        arr_24k = np.frombuffer(raw_24k, dtype=np.int16)
        arr_16k = np.interp(
            np.arange(0, len(arr_24k), 1.5),
            np.arange(0, len(arr_24k)),
            arr_24k
        ).astype(np.int16)
        return arr_16k.tobytes()

    pcm_q1 = get_speech_pcm("Tell me a very long story about Jupiter.")
    pcm_q2 = get_speech_pcm("Stop!")
    
    print("Connecting to websocket...")
    async with websockets.connect("ws://localhost:8000/ws/audio", ping_interval=None, ping_timeout=None) as ws:
        state_msg = json.loads(await ws.recv())
        assert state_msg["state"] == "Listening..."
        print("State: Listening...")
        
        print("Sending Query 1...")
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
        
        while True:
            msg_str = await ws.recv()
            if isinstance(msg_str, str):
                msg = json.loads(msg_str)
                if msg.get("state") == "Speaking...":
                    print("AI is now speaking...")
                    break

        print("AI started speaking! Quickly sending barge-in audio...")
        for i in range(0, len(pcm_q2), chunk_size):
            await ws.send(pcm_q2[i:i+chunk_size])
            await asyncio.sleep(0.01)
            
        print("Sent barge-in audio. Waiting for interruption signal...")
        interrupted = False
        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                print(f"Received audio chunk while barging in ({len(msg)} bytes)")
            elif isinstance(msg, str):
                m = json.loads(msg)
                print(f"Received JSON: {m}")
                if m.get("state") == "Interrupted":
                    print("SUCCESS: Barge-in detected and pipeline interrupted!")
                    interrupted = True
                    break
                if m.get("state") == "Listening...":
                    print("FAILURE: Pipeline finished normally instead of interrupting!")
                    break

        assert interrupted, "Pipeline was not interrupted!"

if __name__ == "__main__":
    asyncio.run(test_bargein())
