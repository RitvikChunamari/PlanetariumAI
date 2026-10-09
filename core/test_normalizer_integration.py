import asyncio
import websockets
import json
import numpy as np
from inference.tts import KokoroTTS

async def test_normalizer():
    print("Generating test audio for normalizer...")
    tts = KokoroTTS("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
    
    def get_speech_pcm(text):
        raw_24k = tts.synthesize(text, voice="af_sarah")
        arr_24k = np.frombuffer(raw_24k, dtype=np.int16).astype(np.float32)
        
        arr_16k = np.interp(
            np.arange(0, len(arr_24k), 1.5),
            np.arange(0, len(arr_24k)),
            arr_24k
        ).astype(np.int16)
        
        silence_pad = np.zeros(8000, dtype=np.int16)
        arr_16k = np.concatenate([arr_16k, silence_pad])
        return arr_16k.tobytes()

    # We ask a question that triggers a LLM response with abbreviation
    # Let's ask: "What is Sagittarius A star?" or "Tell me about JWST."
    # Wait! If the LLM generates the text, we have no control over what it outputs unless we force it or test a specific fact.
    # Fact 1 in the RAG DB: "A year on Venus is shorter than a day on Venus."
    # We can just check the logs to see if normalizer runs!
    
    pcm_q1 = get_speech_pcm("Tell me a fact about Venus.")
    
    print("Connecting to websocket...")
    async with websockets.connect("ws://localhost:8000/ws/audio", ping_interval=None, ping_timeout=None) as ws:
        state_msg = json.loads(await ws.recv())
        assert state_msg["state"] == "Listening..."
        
        print("Sending Query...")
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
        
        print("Waiting for synthesized output...")
        
        # we can just receive until the connection drops or it returns Listening
        while True:
            resp = await ws.recv()
            if isinstance(resp, str):
                msg = json.loads(resp)
                print("WS TEXT:", msg)
                if msg.get("state") == "Listening...":
                    print("Finished response!")
                    break
            else:
                print(f"WS BINARY: Received audio chunk of {len(resp)} bytes")
        
        await ws.close()

if __name__ == "__main__":
    asyncio.run(test_normalizer())
